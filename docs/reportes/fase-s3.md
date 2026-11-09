## Reporte Sprint 3 (domingo 08/11) — Panel web de administración

> Un solo reporte para S3-1 a S3-4 + 🟡, porque se hizo todo en el día, siguiendo la replanificación del PM del 08/11.

Hecho:
- **Git:** `sprint-2` mergeado a `main`, tag `v0.3-demo`, push con tags, rama `sprint-3` creada desde `main` y subida a GitHub.
- **S3-1 · Backend** (`0edc6f1`). FastAPI en el **mismo proceso y event loop** que el servidor del juego, en el puerto 8000:
  - `auth.py`: login con usuario y contraseña del `.env` (`compare_digest`), JWT de 8 h, máximo 5 intentos por minuto por IP (el 6.º da 429). Sin `ADMIN_PASSWORD`, el panel queda deshabilitado; nunca se usa una contraseña por defecto.
  - `registro_logs.py`: captura todos los logs (INFO, WARNING y ERROR) en un buffer de 2000 líneas, los empuja por WebSocket y los guarda en la tabla `logs` en lotes cada 2 s, para no frenar el juego. Al arrancar borra los de más de 30 días.
  - `admin_api.py`: `/api/login`, `/api/estado` (incluye los usuarios activos), `/api/salas`, cerrar sala, expulsar, `/api/usuarios` (búsqueda y paginado), `/api/usuarios/{u}` (historial, errores por elemento y confusiones "llevó X cuando faltaba Y"), `/api/logs` (filtros por nivel y texto), `/api/auditoria` y el WebSocket `/api/ws` (logs al instante y estado cada 2 s).
  - En el juego (`server.py`): mensajes nuevos `expulsado` y `sala_cerrada` (documentados en `docs/protocolo.md`), tablas `logs` y `auditoria_admin`, y columnas de bloqueo en `usuarios` (todo con `IF NOT EXISTS`). Sin BD (Plan B2), la auditoría y los eventos quedan en memoria y el panel muestra el aviso amarillo "Modo sin base de datos".
  - **El panel no puede tumbar el juego:** si faltan dependencias, la contraseña o el puerto 8000, el juego arranca igual y lo avisa en el log.
  - Docker: build multi-etapa (Node compila el panel; la imagen final no lleva Node), contexto en la raíz con `.dockerignore`, puerto 8000 y `env_file: .env` opcional. Creé `.env.example` y agregué `.env` al `.gitignore`.
- **S3-2/S3-3 · Panel React** (`2732da6`). Vite + React 18 + React Router (HashRouter), en JavaScript:
  - Login, Estado (datos en vivo + usuarios activos con *Expulsar*), Salas (tarjetas en vivo con roles, "Listo" y misión en curso; *Expulsar* y *Cerrar sala*), Usuarios (búsqueda), detalle de usuario, Logs en vivo (filtros por nivel y texto, pausa) y Auditoría.
  - Toda acción pide confirmación y **motivo obligatorio**.
  - Tema oscuro, legible a 1280×720, adaptado al celular (menú ☰). Indicador "● En vivo" con reconexión automática.
  - `scripts/panel_dev.sh` para desarrollo con Vite.
- **S3-4 mínima · Unity** (`56ddc5e`): con `expulsado`, el juego vuelve a la pantalla de conexión y muestra "Fuiste expulsado por un administrador. Motivo: …", **no** "Se perdió la conexión". Con `sala_cerrada` vuelve al lobby con el motivo.
- **🟡**, con lo 🔴 ya terminado y testeado, en el orden pedido:
  1. **Estadísticas en tabla** (`0c90664`): `estadisticas.py` con **pandas** calcula los errores por elemento (veces, % y usuarios), las confusiones, el tiempo por misión, las misiones por día y los usuarios con más errores. Sin gráficos.
  2. **Aviso global** (`467da45`): `POST /api/aviso` (máx. 200 caracteres) y un formulario en Estado. En el juego aparece una franja amarilla arriba, 6 s, en cualquier pantalla, también en la partida.
  3. **Bloquear / desbloquear** (`467da45`): desde el detalle del usuario. Un usuario bloqueado no puede iniciar sesión ("Cuenta bloqueada: <motivo>"), y si está conectado se lo expulsa.
- **Docs:** `docs/pruebas/s3-integral.md` (guion para Jona), `docs/protocolo.md`, `docs/decisiones.md` (sección Sprint 3), `docs/backlog.md`, `README.md` y casillas de `MDs/SPRINT3.md`.

Probado (cómo y resultado):
- **pytest** (`servidor/tests`, sin BD): **28 passed**. Cubren login OK / 401 / 429; 401 sin token o con token falso en las 12 rutas protegidas; expulsar (el cliente TCP recibe `expulsado`, se cierra su socket y puede volver a entrar); cerrar sala; estado y salas en vivo; usuarios y detalle después de una misión jugada de verdad por bots; una fila de auditoría por acción, sin la contraseña; filtros de logs; WebSocket (token malo → 4401, empuja logs y estado); estadísticas; aviso; bloqueo y desbloqueo.
- **Con PostgreSQL (Docker), con curl:** login, `/api/estado`, `/api/usuarios` (108 perfiles reales), detalle con errores y confusiones, logs filtrados, auditoría y estadísticas.
- **Plan B2:** `python server.py` sin BD: con dependencias, el panel funciona; **sin dependencias** (el Python del sistema), el juego arranca y avisa "Panel web DESHABILITADO". En los dos casos, `probar_cliente.py` da `TODO OK ✔`. Ctrl+C cierra limpio.
- **Navegador headless (Playwright, script fuera del repo)** contra Docker, con bots en el juego: **22/22**. Incluye login malo y bueno, en vivo, expulsar y cerrar sala con clics (con validación del motivo vacío), detalle, logs que llegan en vivo, auditoría, estadísticas, aviso, bloquear y desbloquear desde la UI, celular (390 px) sin scroll horizontal y cero errores de JavaScript. Revisé las capturas a 1280×720 y en el celular.
- **Build de Linux:** batch sin `error CS` (`logs/unity_s3_amarillo.log`, Succeeded). Escenario nuevo **`probar_build.sh panel`** con el juego real: el aviso aparece en la partida, `sala_cerrada` lleva al lobby con el motivo, `expulsado` lleva a la conexión con el motivo y una cuenta bloqueada ve "Cuenta bloqueada: …" → `TODO OK ✔`.
- **El juego no se rompió:** al final del día, `probar_servidor.sh` ✔, `probar_perfiles.sh` ✔ y `probar_build.sh` con los **6 escenarios** (wizard, player, sesion, reinicio, progreso, panel) ✔.

Pendiente / riesgos:
- 🧑 **La prueba integral de Jona** (`docs/pruebas/s3-integral.md`), en especial el celular y lo que los tests no ven: el dibujo de la franja amarilla y los textos en rojo del juego.
- **Fuera de hoy, por decisión del PM** (anotado en `docs/backlog.md`): paquete de Windows v0.4, CSV, gráfico de conexiones e histórico paginado de logs en la UI.
  - **Ojo:** sin el paquete v0.4, el zip de Windows sigue siendo la v0.3, sin panel. Si la presentación es en la PC de Windows, el panel no está disponible ahí.
  - **Build de Windows:** no lo hice (no se pidió). Antes de armar el v0.4 hay que generarlo.
- **Con Docker, la IP de todos se ve como `172.18.0.1`** (la red de Docker). El límite de 5 logins por minuto se comparte entre todos los equipos, y la auditoría no ve la IP real. En la demo no molesta; está en el backlog.
- **La primera vez, `servidor_iniciar.sh` tarda más:** baja `node:20-alpine` y pandas. Conviene correrlo antes de la presentación, con internet.
- El `.env` vive solo en esta PC (no está en git). En otra PC hay que crearlo desde `.env.example`.
- Merge a `main` y tag `v0.4-demo`: después de que apruebes la prueba integral.

Necesito de Jona:
1. Hacer `docs/pruebas/s3-integral.md` (15 pasos) con el panel en el navegador y `scripts/jugar_linux.sh 2`.
2. Credenciales del panel: usuario **`admin`** y la contraseña de `ADMIN_PASSWORD` en el `.env` de esta PC. La contraseña no va en este reporte porque el repo está en GitHub; te la paso aparte.
3. Pasarme lo que falle, con captura y hora.
4. Decidir si la presentación se hace desde Arch (panel disponible) o desde Windows con el zip v0.3 (sin panel).

Commits: `0edc6f1` (S3-1), `2732da6` (S3-2/S3-3), `56ddc5e` (S3-4), `0c90664` (estadísticas), `467da45` (aviso + bloqueo), más el commit de este reporte.
