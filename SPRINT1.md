# SPRINT1.md — Roles Wizard/Player + sincronización

> Brief del PM para Claude Code. Complementa a `CLAUDE.md`: **todas sus reglas siguen vigentes**
> (sin sudo, no editar YAML de Unity a mano, batch con el editor cerrado, commits en español, reporte por fase).
> Entrega: **hoy 26/10/2026 en la noche**. La versión `v0.1-demo` es el plan de respaldo y no se toca.

## 0. Regla de oro de este sprint: rama aparte
```bash
git checkout -b sprint-1
```
Todo el trabajo va en `sprint-1`. **Solo se hace merge a `main`** cuando Jona apruebe la prueba en Windows (Fase S1-4).
**Por qué:** si a la noche esto no está listo, `main` y `v0.1-demo` siguen intactos y se entrega esa versión.

## 1. Qué se construye (decisiones del cliente)

**Concepto:** cooperativo asimétrico, estilo *We Were Here Together*. Nadie puede ganar solo.

| | 🧙 Wizard | 🧑‍🔬 Player |
|---|---|---|
| Quién | El **anfitrión** (quien crea la sala) | Todos los que se unen |
| Ve | El **símbolo** de cada elemento y la **receta** de la misión | Solo esferas de colores con un "?" |
| Puede | Moverse y **señalar** objetos (clic) | Moverse, **agarrar y soltar** objetos (tecla E) |
| No puede | Agarrar objetos | Ver qué elemento es cada esfera |

Los jugadores hablan en persona o por voz: el Wizard guía ("¡la esfera que acabo de señalar es hidrógeno!") y el Player ejecuta.

**Misión demo:** *Sintetizar agua*. Sobre la mesa hay 6 esferas: H, H, O, Na, Cl y C. Hay que llevar **exactamente 2 H + 1 O** a la zona del **reactor**.
- Si entra un elemento que no corresponde: "Reacción inestable", el elemento vuelve a la mesa y se registra un **error**.
- Si el reactor llega a 2 H + 1 O: "¡Reacción completada! 2H + O → H₂O" para todos, y la misión se marca como cumplida.
- El Wizard puede **reiniciar** la misión.

### Sincronización requerida
1. **Objetos compartidos:** agarrar, soltar y posición, controlado por el servidor.
2. **Acciones del Wizard:** el señalamiento se ve en todos los clientes (el objeto brilla o pulsa unos 2 segundos).
3. **Estado de la partida:** contenido del reactor, errores, mensajes y misión completada.

### Fuera de alcance (va a `docs/backlog.md`)
Voz integrada · más misiones · ocultar la información del Wizard en el servidor (anti-trampas) · VR · física real.

## 2. Diseño técnico

### 2.1 Servidor autoritativo (`servidor/server.py`)
El servidor es **la única fuente de verdad** sobre los objetos. **Por qué:** si dos jugadores intentan agarrar la misma esfera al mismo tiempo, el servidor decide quién la agarró. Si decidiera cada cliente, se desincronizarían.

- `Jugador.rol`: `"wizard"` | `"player"`. Al crear la sala el rol es `wizard`; al unirse, `player`.
- Si el anfitrión se va, el nuevo anfitrión pasa a ser `wizard`. **Por qué:** sin Wizard la partida no se puede ganar.
- `iniciar` exige **al menos 2 jugadores** (ahora sí hace falta un Player) y que todos estén listos.
- Al iniciar, el servidor crea `sala.mision` con los objetos `{id, elemento, x, y, z, portador}` en posiciones fijas sobre la mesa, el reactor (centro + radio) y el estado `{reactor: [], errores: 0, completada: false}`.
- **Validaciones:** solo un `player` puede agarrar o soltar; solo el `wizard` puede señalar o reiniciar; no se puede agarrar un objeto que ya tiene portador; el portador de un objeto solo lleva uno a la vez.
- **Desconexión:** si se va un jugador que llevaba un objeto, ese objeto queda en el suelo, en su última posición.
- **Persistencia** (tabla `eventos`, ya existe): registrar `agarrar`, `soltar`, `senal`, `reaccion_fallida` (con `{esperado, recibido}`), `mision_completada` (con duración en segundos y errores) y `mision_reiniciada`.
  **Por qué:** `reaccion_fallida` es exactamente el dato de "errores frecuentes" que Jona analizará después con pandas para el perfil de investigación.

### 2.2 Protocolo nuevo (actualizar `docs/protocolo.md`)
| Cliente → Servidor | Quién | Servidor → Cliente |
|---|---|---|
| `{"t":"agarrar","obj":"o3"}` | player | `{"t":"obj","obj":{id,elemento,x,y,z,portador}}` a todos |
| `{"t":"soltar","obj":"o3","x":..,"y":..,"z":..}` | player | `obj` + `estado` a todos |
| `{"t":"senalar","obj":"o3"}` | wizard | `{"t":"senal","obj":"o3","por":"<id>"}` a todos |
| `{"t":"reiniciar"}` | wizard | `inicio` de nuevo, con la misión fresca |
| — | — | `{"t":"estado","reactor":["H","O"],"errores":1,"completada":false,"mensaje":"..."}` |

- `sala.info()` agrega `rol` a cada jugador. El mensaje `inicio` agrega `mision` (objetos, reactor, receta).
- **Mientras alguien lleva un objeto no se envían mensajes extra:** cada cliente dibuja el objeto pegado a la cápsula de su portador, cuya posición ya llega por `pos`. **Por qué:** se ahorra red y no aparece un segundo flujo de posiciones que pueda desincronizarse.
- Los números del JSON se escriben con `InvariantCulture` (regla 8 de `CLAUDE.md`).

### 2.3 Cliente Unity
- **`ClienteRed.cs`:** métodos `Agarrar(id)`, `Soltar(id, pos)`, `Senalar(id)` y `Reiniciar()`. Los modelos JSON nuevos (`InfoObjeto`, `InfoMision`, `EstadoMision`) usan `[Serializable]` y nombres de campos idénticos a los del servidor.
- **`GestorPartida.cs`:**
  - Crea el reactor (un cilindro plano translúcido) y las 6 esferas usando los materiales de `Resources/Materiales` (fix del magenta).
  - **Player:** tecla **E** cerca de una esfera (≤ 1.5 m) para agarrar y otra vez **E** para soltar delante de sí. El objeto agarrado se dibuja sobre la cabeza del portador.
  - **Wizard:** **clic izquierdo** sobre una esfera (raycast) para señalarla. No puede agarrar.
  - Las etiquetas con el símbolo (H, O, Na…) **solo se muestran si mi rol es `wizard`**. Los players ven "?".
  - Al recibir `senal`: el objeto pulsa (escala y emisión) durante 2 segundos en **todos** los clientes, incluidos los players. Así el player sabe *cuál* le están indicando, pero no *qué* es.
- **`MenuLobby.cs`:**
  - En la sala, cada jugador aparece con su rol: "🧙 Wizard (anfitrión)" o "Player". Recuerda usar color o texto y no emojis si la fuente no los dibuja.
  - El botón Iniciar se desactiva con menos de 2 jugadores y se muestra el motivo.
  - **HUD en partida:** rol, controles del rol, contenido del reactor, contador de errores y mensaje central grande al completar. El Wizard además ve la **receta** (`2 H + 1 O → H₂O`) y un botón *Reiniciar misión*.

## 3. Plan de trabajo

### Fase S1-1 — Servidor · 🤖 CLAUDE CODE
- [x] Crear la rama `sprint-1`.
- [x] Implementar 2.1 y 2.2 en `server.py`.
- [x] Ampliar `probar_cliente.py` con la secuencia Wizard (Ana) + Player (Beto):
  1. Iniciar con 1 solo jugador falla.
  2. Beto agarra; Ana intenta agarrar y falla (rol).
  3. Beto suelta Na en el reactor: error + vuelve a la mesa.
  4. Ana señala y Beto recibe `senal`.
  5. Beto lleva H, H, O al reactor: `completada: true`.
  6. Ana reinicia y el reactor queda vacío.
  7. Ana se desconecta: Beto pasa a ser wizard.
- [x] **Criterio de terminado:** `probar_servidor.sh` → `TODO OK ✔` y en `servidor_eventos.sh` se ven `reaccion_fallida` y `mision_completada`.
- [x] Commit, push de la rama y reporte S1-1.

### Fase S1-2 — Cliente Unity · 🤖 CLAUDE CODE
- [x] Implementar 2.3. Compilar en batch: cero `error CS`.
- [x] Re-ejecutar `ConfigurarDemo.Configurar` si la escena necesita cambios. No editar el `.unity` a mano.
- [x] Build de Linux, commit y reporte S1-2.

### Fase S1-3 — Prueba de juego · 🧑 JONA
- [x] Editor (Play) = Wizard y build de Linux = Player. Recorrer la misión completa: error con Na, señalamiento, completar y reiniciar.
- [x] Pasarle a Claude Code los bugs encontrados. 🤖 Corrige, re-build y reporte S1-3.
  - [x] Ronda 1 corregida (`pos`/`soltar` con JSON roto, "H2O", etiquetas). Ronda 2 aprobada por el cliente.

### Fase S1-4 — Entrega v0.2 · 🤖 + 🧑
- [x] 🤖 Build de Windows, `empaquetar.sh` → `dist/QuimicaDemo_Windows_v0.2.zip`. Actualizar el LEEME (roles, controles y misión).
- [ ] 🧑 Prueba en Windows 11 con 2 ventanas.
- [ ] 🤖 Si es OK: merge de `sprint-1` a `main`, tag `v0.2-demo`, push con tags y reporte final.
- [ ] Si a las **19:00** la S1-4 no está aprobada, **se entrega `v0.1-demo`** y `sprint-1` queda para la próxima presentación.
  **Por qué una hora de corte:** decidir con tiempo evita entregar algo a medio probar por apuro.
