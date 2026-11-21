# PRESENTACION.md — Build de Windows, pruebas y kit de presentación

> Brief del PM para Claude Code. Siguen vigentes **todas** las reglas de `CLAUDE.md`.
> Objetivo: dejar **una versión para Windows probada y empaquetada** y **un kit de presentación** (tutorial de preparación + guion de lo que se dice) para que Jona presente sin improvisar.
> Fecha de presentación: **[FECHA Y HORA — completar]**. Corte: **2 horas antes**.

## 0. Antes de empezar
1. Identifica la versión estable más reciente (`git tag --sort=-creatordate | head`). La nueva se llama **la siguiente**: si la última es `v0.6-demo`, esta es `v0.7-demo`. Abajo aparece como `<VER>`.
2. Rama `presentacion` desde `main` (o desde la rama donde esté lo último aprobado, si todavía no se mergeó: dilo en el reporte).
3. **No agregues funciones nuevas.** Este brief solo empaqueta, prueba y documenta lo que ya existe. Si al probar aparece un bug, se corrige (`fix:`); si aparece una idea, va a `docs/backlog.md`.
4. **El guion tiene que ser fiel a lo que existe.** Si una parte del guion de §4 describe algo que el juego no hace, ajusta el texto a la realidad y márcalo en el reporte. Nunca se presenta algo que no funciona.

## 1. Build y paquete de Windows

### 1.1 Datos de demo (nuevo)
`scripts/sembrar_demo.py` (y su `.bat` para Windows) carga en la BD del servidor (SQLite o PostgreSQL, vía `repositorio.py`) un estado listo para presentar:
- Cuenta docente `docente_demo` con una contraseña generada, que se muestra y se guarda en `demo_credenciales.txt`, junto a la de admin.
- Clase "Química 5to A" con su código de 8 caracteres.
- Un reto "Laberinto — Sala 1 a 5" con **semilla fija**.
- 4 estudiantes (`ana_demo`, `beto_demo`, `carla_demo`, `dani_demo`) inscritos, con **algunos intentos ya jugados** y errores variados por concepto, para que el panel docente y las estadísticas **no se vean vacíos** al abrirlos.
- Idempotente: si se corre dos veces, no duplica nada.

`scripts/limpiar_demo.py`: borra solo los datos `*_demo` (y la clase y el reto demo). **Por qué los dos:** en la presentación se muestra un panel con datos reales de ejemplo, y después se puede dejar la BD limpia.

### 1.2 Build
- Unity cerrado → `Construir.Windows` y `Construir.Linux`.
- Tag `<VER>` → GitHub Actions construye y prueba `QuimicaServidor.exe` en Windows → `scripts/publicar_release.sh <VER>`.

### 1.3 Contenido del zip `dist/QuimicaDemo_Windows_<VER>.zip`
```
QuimicaDemo/
├─ LEEME.txt                    ← pasos cortos (§3 resumido)
├─ Juego/QuimicaDemo.exe        ← el juego
├─ Servidor/                    ← servidor local: QuimicaServidor.exe (SQLite)
│  ├─ sembrar_demo.bat
│  └─ limpiar_demo.bat
└─ ServidorDedicado/            ← Docker + PostgreSQL
   ├─ docker-compose.yml, .env.example, servidor/, panel/
   ├─ instalar_servidor.bat · detener_servidor.bat · ver_logs.bat · abrir_pgadmin.bat
   └─ iniciar_servidor_sin_docker.bat   ← plan C (si un antivirus bloquea el .exe)
```

## 2. Pruebas

### 2.1 Automáticas (todas en verde antes del tag)
- `pytest` contra **SQLite y PostgreSQL**, 0 salteados.
- `probar_build.sh`: **todos** los escenarios (laberinto, laberinto_player, sesion, reinicio, panel, espectador, docente/clases si existe).
- `probar_paquete.sh`: el paquete Docker en Arch + el `.exe` en Actions (Windows), **jugando una partida del laberinto**.
- **Nuevo:** prueba de `sembrar_demo.py` (lo corre dos veces y verifica que no haya duplicados) y de `limpiar_demo.py`.
- Capturas automáticas de las 5 salas en `docs/presentacion/capturas/`, además de capturas de cada pantalla del menú y del panel (admin y docente). Se usan como material de respaldo si falla algo en vivo.

### 2.2 Manual en Windows (la hace Jona) → `docs/pruebas/windows-<VER>.md`
Escribe la lista como tabla con una columna ✅/❌ para que Jona la complete:
1. Descomprimir en **Escritorio** (no en Archivos de programa).
2. `QuimicaServidor.exe`: SmartScreen → *Ejecutar de todas formas*; Defender no lo bloquea; el firewall acepta las redes privadas; la ventana muestra las IP y la contraseña, y se abre el panel.
3. `sembrar_demo.bat` → el panel muestra la clase, el reto y los resultados de ejemplo.
4. Panel **admin**: logs en vivo, crear un docente nuevo.
5. Panel **docente**: ver la clase, el código, los inscritos, los resultados por concepto.
6. Dos ventanas del juego: login de estudiantes, unirse a la clase con el código, crear sala, elegir el reto, jugar la Sala 1 completa.
7. El panel docente muestra el intento nuevo.
8. Tercera ventana: docente como **espectador** en esa sala.
9. Cerrar el servidor, volver a abrirlo: perfiles y resultados siguen ahí (SQLite).
10. **Desde otra PC o el celular** en la misma red: el panel con `http://<IP>:8000`.
11. (Si hay Docker en esa PC) `ServidorDedicado/instalar_servidor.bat` → misma prueba 3–7 contra PostgreSQL, y pgAdmin muestra las tablas.

## 3. Tutorial de preparación → `docs/presentacion/tutorial.md`
Paso a paso para Jona, **con los comandos exactos y sin términos que no haya visto**. Estructura:
- **El día anterior:** probar el zip en Windows (§2.2), copiar el zip a la USB, cargar el celular, anotar las credenciales en papel.
- **T-60 min:** encender la PC, descomprimir en el Escritorio, abrir el servidor, `sembrar_demo.bat`, abrir el panel e iniciar sesión como admin y como docente (en dos pestañas), abrir 2 ventanas del juego con los estudiantes ya logueados. **Abrir todo antes**, para que en vivo no aparezcan los avisos de SmartScreen o del firewall.
- **T-15 min:** verificar con el checklist de 5 puntos (servidor arriba, panel ok, 2 juegos en el lobby, celular en la misma red, capturas de respaldo abiertas en una pestaña).
- **Si algo falla en vivo:** tabla síntoma → qué hacer (por ejemplo: "el juego no conecta" → revisar la IP y el firewall; "el `.exe` bloqueado" → plan C; "nada anda" → mostrar las capturas de `docs/presentacion/capturas/` y explicar sobre ellas).
- **Después:** `limpiar_demo.bat` (opcional) y cerrar el servidor.

## 4. Guion de presentación → `docs/presentacion/guion.md`
Copia este guion y **ajústalo a lo que realmente funciona** (§0.4). Duración objetivo: **12–15 min + preguntas**. Cada bloque dice **qué se muestra** y **qué se dice**.

### Bloque 1 — El problema (1 min) · *Se muestra:* pantalla de login del juego
> "En La Paz, muchos estudiantes de secundaria no tienen acceso a un laboratorio ni a reactivos. Aprenden reacciones químicas solo en la pizarra, y les cuesta imaginarse lo que pasa. Nuestro proyecto es un laboratorio de química en forma de juego cooperativo, preparado para realidad virtual, donde se puede practicar sin reactivos."

### Bloque 2 — El giro del negocio (2 min) · *Se muestra:* una diapositiva o el panel docente con datos
> "No vendemos solo un juego: es una **plataforma de aprendizaje y evaluación**. Los estudiantes practican jugando, y el docente crea clases, asigna retos y ve con datos en qué concepto se equivoca cada estudiante: balanceo, mol a mol, masa a masa, reactivo limitante o rendimiento.
> El modelo es **freemium institucional**: el estudiante juega gratis, y el colegio paga una licencia anual que le da su propio servidor, el panel docente y los reportes. Para los colegios fiscales, la licencia la puede cubrir un municipio o un patrocinador.
> Como referencia, Labster, el laboratorio virtual más conocido, cobra desde 5.000 dólares por año por institución. Nosotros apuntamos a una alternativa local, en español y mucho más accesible. El precio exacto lo vamos a validar con entrevistas a colegios."

### Bloque 3 — Los tres roles (1 min) · *Se muestra:* login del juego (estudiante / docente) y login del panel
> "Hay tres roles. El **estudiante** entra solo con su usuario, sin contraseña, porque son menores de edad y pedimos el mínimo de datos. El **docente** entra con usuario y contraseña, y su cuenta la crea el **administrador**, que es quien gestiona el servidor y ve todos los logs."

### Bloque 4 — Demo: el docente prepara la clase (2 min) · *Se muestra:* panel docente
1. Mostrar la clase "Química 5to A" y su **código de 8 caracteres**.
2. Crear un reto en vivo (o mostrar el ya creado).
> "Cada reto tiene una **semilla fija**: todos los grupos de la clase juegan exactamente el mismo laberinto con los mismos números. Así la evaluación es justa."

### Bloque 5 — Demo: los estudiantes juegan (4 min) · *Se muestran:* las dos ventanas del juego, lado a lado
1. Los estudiantes se unen a la clase con el código → crean la sala → eligen el reto → Listo → Iniciar.
2. Jugar la **Sala 1** en vivo.
> "El laberinto está separado por un muro: cada jugador ve una parte de la receta y tiene sus propias tareas. Ninguno puede resolverlo solo, así que tienen que comunicarse. Para abrir la puerta, los dos bajan su palanca a la vez."
> "Las cinco salas siguen el orden en que se enseña estequiometría: balanceo, mol a mol, masa a masa, reactivo limitante y rendimiento porcentual. Y el producto de cada sala se usa en la siguiente: el agua de la primera reacciona con sodio en la segunda, y así hasta el final."
3. Equivocarse a propósito una vez (por ejemplo, un coeficiente incorrecto).
> "Ese error queda registrado con su concepto, para el docente."

### Bloque 6 — Demo: el docente observa y evalúa (2 min) · *Se muestran:* tercera ventana (espectador) + panel docente
1. El docente entra como **espectador** a la sala: ve la partida sin ocupar un lugar.
2. En el panel: el intento nuevo, con el **tiempo y los errores por concepto** de cada estudiante.
> "El docente no tiene que adivinar quién entendió: ve en qué concepto se traba cada uno, y puede reforzar justo eso en la clase."

### Bloque 7 — Arquitectura y servidor (2 min) · *Se muestran:* la ventana del `.exe`, el panel admin y (si hay) `docker compose ps`
> "Hay dos formas de tener el servidor. El **servidor local** es un solo `.exe`: el colegio lo abre con doble clic y no necesita instalar nada, y guarda los datos en SQLite, un solo archivo. El **servidor dedicado** usa Docker con PostgreSQL, para el servidor oficial. Es el mismo código en los dos casos: todo el acceso a datos pasa por una capa llamada repositorio, que permite cambiar de base de datos sin tocar la lógica del juego."
> "Cada versión se construye y se prueba automáticamente en una máquina con Windows antes de publicarse, con más de 150 pruebas automáticas contra las dos bases de datos." *(usa la cifra real de pytest al momento del tag)*

### Bloque 8 — Cierre y próximos pasos (1 min)
> "Lo que viene: arte final del laberinto, generación procedural de niveles con semilla para que el docente controle la dificultad, pistas integradas en el escenario para aprender descubriendo, y la versión en realidad virtual, para la que el código ya está preparado: la forma de interactuar está separada de la forma de ingresar, así que agregar los controles del visor no cambia el resto."

### Preguntas probables (tabla para estudiar)
| Pregunta | Respuesta corta |
|---|---|
| ¿Cómo evitan que un estudiante entre como docente? | La cuenta docente la crea solo el admin y tiene contraseña; la del estudiante no da acceso al panel. |
| ¿Dónde están los datos? | En el servidor local, en `quimica.db` junto al `.exe`. En el dedicado, en PostgreSQL dentro de Docker, con un volumen persistente. |
| ¿Y si no hay internet en el colegio? | El servidor local funciona en la red del colegio, sin internet. |
| ¿Cómo es justa la evaluación si juegan en grupo? | Los errores se atribuyen al estudiante que los cometió, y todos los grupos juegan con la misma semilla. |
| ¿Por qué el estudiante no tiene contraseña? | Minimización de datos de menores: solo usuario, nombre visible y color. |
| ¿Qué datos de mercado tienen? | 1.231.872 estudiantes de secundaria en Bolivia (Memoria Institucional 2024 del Ministerio de Educación, vía SITEAL-UNESCO). El precio se valida con entrevistas. |
| ¿Cuándo llega la VR? | En la fase siguiente; la arquitectura ya separa la interacción del dispositivo de entrada. |
| ¿Qué pasa si el antivirus bloquea el `.exe`? | Hay un plan C: el mismo servidor con un `.bat` que usa Python. |

**Fuentes que se pueden citar:** SITEAL-UNESCO, perfil educativo de Bolivia (https://siteal.iiep.unesco.org/pais/educacion-pdf/bolivia) · Labster, página de precios (https://labster.com/pricing).

## 5. Entregables y criterio de terminado
- [ ] `dist/QuimicaDemo_Windows_<VER>.zip` + GitHub Release `<VER>` con los dos zips.
- [ ] Pruebas §2.1 en verde (pegar las cifras en el reporte).
- [ ] `docs/pruebas/windows-<VER>.md` (checklist para Jona).
- [ ] `docs/presentacion/tutorial.md`, `docs/presentacion/guion.md` (ajustado a la realidad) y `docs/presentacion/capturas/`.
- [ ] `docs/reportes/presentacion-<VER>.md`: qué entró, qué partes del guion se ajustaron y por qué, y el **plan B** si algo falla.
- [ ] Merge a `main` y push con tags.
