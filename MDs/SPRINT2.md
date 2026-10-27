# SPRINT2.md — Perfiles + progreso por misiones

> Brief del PM para Claude Code. Siguen vigentes **todas** las reglas de `CLAUDE.md`
> (sin sudo, nada de YAML de Unity a mano, batch con el editor cerrado, InvariantCulture, commits en español, reporte por fase).
> Plazo: **hoy 26/10/2026, corte a las 19:00**. Si a esa hora no está aprobado en Windows, se entrega `v0.2-demo`.

## 0. Requisito previo (bloqueante) · 🧑 JONA + 🤖
- [ ] 🧑 Validar la v0.2 en Windows 11 (prueba de la S1-4).
- [ ] 🤖 Merge de `sprint-1` a `main`, tag `v0.2-demo` y push con tags.
- [ ] 🤖 `git checkout -b sprint-2` **desde main ya con la v0.2**.

**Por qué:** si se empieza el Sprint 2 antes de cerrar la v0.2, se mezclan dos versiones a medio probar y se pierde el respaldo.

## 1. Qué se construye (decisiones del cliente)

### Flujo de pantallas
```
Conexión (IP/puerto) → [VENTANA 1] Perfil: Iniciar sesión | Crear perfil
                                  ↓
                     Lobby de salas ──botón "Mi perfil"──→ [VENTANA 2] Editar perfil + Progreso
                                  ↓                                      (volver al lobby)
                     Sala → Partida (Sprint 1, sin cambios de jugabilidad)
```

### Ventana 1 — Crear perfil / Iniciar sesión
- **Login solo con nombre de usuario, sin contraseña** (decisión del cliente, para la demo).
- Pestaña **Iniciar sesión:** campo *usuario* → botón *Entrar*.
- Pestaña **Crear perfil:** *usuario* (identificador único, **no editable** después), *nombre visible* y *color de avatar* (paleta de 8 colores) → botón *Crear*.
- Se recuerda el último usuario usado en `PlayerPrefs` para no reescribirlo cada vez.
- Errores visibles arriba: "Ese usuario ya existe", "Usuario no encontrado", "Ese usuario ya tiene una sesión abierta".

### Ventana 2 — Editar perfil + Progreso
- Editables: **nombre visible** y **color de avatar**. El *usuario* se muestra pero no se puede editar.
- Botones *Guardar* y *Volver*.
- Sección **Progreso** (solo lectura):
  - Misiones completadas (total)
  - Mejor tiempo en "Sintetizar agua"
  - Errores totales cometidos como Player
  - Historial: las últimas 5 misiones, con fecha, duración y errores

### Reglas de progreso
- **Solo los Players suman progreso.** El Wizard guía, pero no suma.
- Cuando se completa una misión, se guarda un registro **por cada Player** que estaba en la sala en ese momento.
- Errores: cada `reaccion_fallida` se atribuye **al Player que soltó el elemento** (queda en su perfil y en la tabla `eventos`).
  **Por qué:** eso permite el análisis de "errores frecuentes por estudiante" con pandas, que es lo que justifica Python en el perfil de investigación.

### Integración con lo que ya existe
- El **nombre visible** y el **color** del perfil reemplazan al "Jugador81" y a los colores asignados por índice. Se ven en la sala y sobre la cápsula, y llegan a los demás dentro de `sala.info()`.
- Si alguien edita su perfil mientras está en una sala, los demás lo ven actualizado (se reenvía `sala`).

### Fuera de alcance (a `docs/backlog.md`)
Contraseña y hash con bcrypt · roles estudiante/docente/admin (pendiente de consulta con el docente) · guardado local estilo Steam Cloud · borrar cuenta · avatares 3D.

## 2. Diseño técnico

### 2.1 Base de datos (PostgreSQL)
Crear las tablas con `CREATE TABLE IF NOT EXISTS` en `iniciar_bd()`.
**Por qué en Python y no en un `.sql` montado en `docker-entrypoint-initdb.d`:** Postgres solo ejecuta esos scripts cuando el volumen está **vacío**, y el volumen `datos_db` ya existe con datos. Así, las tablas se crean igual en una instalación nueva y en una existente.

```sql
usuarios (
  id            SERIAL PRIMARY KEY,
  usuario       TEXT UNIQUE NOT NULL,      -- minúsculas, ^[a-z0-9_]{3,16}$
  nombre        TEXT NOT NULL,             -- 1..20 caracteres
  color         TEXT NOT NULL,             -- uno de los 8 hex de la paleta
  creado        TIMESTAMPTZ DEFAULT now(),
  ultimo_login  TIMESTAMPTZ
)

misiones_completadas (
  id          SERIAL PRIMARY KEY,
  usuario_id  INT REFERENCES usuarios(id),
  mision      TEXT NOT NULL,               -- 'agua'
  sala        TEXT NOT NULL,
  duracion_s  REAL NOT NULL,
  errores     INT NOT NULL,                -- errores de ESE player en esa misión
  fecha       TIMESTAMPTZ DEFAULT now()
)
```
- `eventos.detalle` de `reaccion_fallida` agrega `usuario`.
- **Sin base de datos** (Plan B2 con `iniciar_servidor_sin_docker.bat`): los perfiles y el progreso viven en diccionarios en memoria y se pierden al cerrar. Se avisa con `log.warning` al arrancar. **Por qué:** el Plan B tiene que seguir funcionando.

### 2.2 Protocolo (actualizar `docs/protocolo.md`)
| Cliente → Servidor | Respuesta |
|---|---|
| `{"t":"registro","usuario":"jona","nombre":"Jona","color":"#3FA9F5"}` | `perfil` o `error` |
| `{"t":"login","usuario":"jona"}` | `perfil` o `error` |
| `{"t":"perfil_editar","nombre":"...","color":"#..."}` | `perfil` (+ `sala` a la sala si está en una) |
| `{"t":"perfil_ver"}` | `perfil` |
| — | `{"t":"perfil","usuario":..,"nombre":..,"color":..,"progreso":{"completadas":3,"mejor_tiempo_s":41.2,"errores_totales":5,"historial":[{fecha,duracion_s,errores}]}}` |

- `hola` deja de usarse: la identidad viene del `login` o del `registro`.
- **Antes del login**, el servidor rechaza `listar`, `crear_sala` y `unirse` con el error "Inicia sesión primero". **Por qué:** sin identidad no hay a quién asignarle el progreso.
- **Una sesión por usuario:** si `jona` ya está conectado, un segundo `login` como `jona` se rechaza. **Por qué:** si no, dos ventanas sumarían progreso al mismo perfil y el dato quedaría inflado.
- Las validaciones (formato del usuario, largo del nombre, color en la paleta) se hacen **en el servidor**. El cliente también valida, pero solo por comodidad: la regla la impone el servidor.
- `sala.info()` agrega `color` a cada jugador.
- Paleta (la misma en los dos lados; el servidor la envía en `perfil`, o queda constante en ambos y documentada en el protocolo): `#3FA9F5 #F5D33F #E04FD8 #4FE07A #F5913F #E04F4F #FFFFFF #6A5AE0`.

### 2.3 Cliente Unity
- **`MenuLobby.cs`:** agregar las pantallas `Perfil` (ventana 1, con dos pestañas) y `EditarPerfil` (ventana 2). Agregar el botón *Mi perfil* en el lobby. Seguir con IMGUI, igual que el resto.
  El selector de color son 8 botones cuadrados del color correspondiente, con borde en el seleccionado.
- **`ClienteRed.cs`:** métodos `Registrar`, `Login`, `EditarPerfil` y `VerPerfil`. Modelos `[Serializable]`: `InfoPerfil`, `InfoProgreso`, `EntradaHistorial`. Propiedad `MiPerfil`.
- **`GestorPartida.cs`:** el color de la cápsula sale de `jugador.color` (con `ColorUtility.TryParseHtmlString`) y no del índice.

### 2.4 Nota para el perfil de investigación (sección legal 2.4)
Los usuarios finales son estudiantes de secundaria, en su mayoría **menores de edad**. Por eso el perfil guarda **solo** usuario, nombre visible y color: nada de correo, edad, colegio ni datos personales.
**Por qué:** es el principio de **minimización de datos** (pedir solo lo necesario), y Jona puede citarlo en la justificación legal.

## 3. Plan de trabajo

### Fase S2-1 — Servidor · 🤖
- [ ] Implementar 2.1 y 2.2.
- [ ] Ampliar `probar_cliente.py` (crear un `probar_perfiles.py` aparte si queda muy largo). Debe comprobar:
  1. `crear_sala` sin login → error.
  2. Registro OK; registro con un usuario duplicado → error; usuario con formato inválido → error.
  3. Login de un usuario inexistente → error; doble sesión → error.
  4. `perfil_editar` cambia el nombre y el color, y la sala lo refleja.
  5. Misión completada → el Player suma +1 y el Wizard sigue en 0.
  6. Errores atribuidos al Player correcto.
  7. Al reconectar, el progreso persiste (prueba con Docker).
- [ ] **Criterio de terminado:** todos los tests en `TODO OK ✔`. En pgAdmin se ven `usuarios` y `misiones_completadas` con datos.
- [ ] Commit, push y reporte S2-1.

### Fase S2-2 — Cliente Unity · 🤖
- [ ] Implementar 2.3. Batch sin `error CS`. Build de Linux, commit y reporte S2-2.

### Fase S2-3 — Prueba · 🧑 JONA
- [ ] Crear 2 perfiles de colores distintos. Editar el nombre de uno **estando en la sala** y verificar que el otro lo ve.
- [ ] Completar la misión: el Player ve +1 en *Mi perfil* y el Wizard no.
- [ ] Cerrar todo, `servidor_detener.sh` y `servidor_iniciar.sh`, volver a entrar: el progreso sigue ahí.
- [ ] Intentar entrar dos veces con el mismo usuario: debe rechazarse.
- [ ] 🤖 Corregir lo reportado, re-build y reporte S2-3.

### Fase S2-4 — Entrega v0.3 · 🤖 + 🧑
- [ ] 🤖 Build de Windows, `QuimicaDemo_Windows_v0.3.zip`, LEEME actualizado (perfiles y progreso) y `abrir_pgadmin.bat` incluido.
- [ ] 🧑 Prueba en Windows 11. **Ojo:** reconstruir el servidor desde la carpeta nueva (`detener` en la vieja, `instalar` en la nueva).
- [ ] 🤖 Si es OK: merge a `main`, tag `v0.3-demo`, push y reporte final.
- [ ] **19:00 sin aprobación → se entrega `v0.2-demo`.**
