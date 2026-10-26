## Reporte Fase 1 — Repo + servidor

Hecho:
- 1.1 Entorno verificado: `docker info` sin sudo ✔, Docker Compose 5.6.1, Python 3.14.8, git 2.56.0, `gh` autenticado como skypromtby2006-source, Unity en `~/Unity/Hub/Editor/6000.3.27f1`.
- La carpeta no era un clon: se hizo `git init -b main` y se agregó `origin` (el remoto estaba vacío).
- 1.2 `.gitignore` (Unity sobre `QuimicaVR/`, Python, `Build/`, `dist/`, `logs/`, `*.log`). Extra: `.gitattributes` que fuerza CRLF en `.bat` y LF en `.sh`, para que git no rompa los finales de línea (base para la Fase 4).
- 1.3 Código copiado de `_base/` a `servidor/`, `docker-compose.yml` y `entrega/windows/`. `_base/` se conserva (y se versionó como referencia hasta la Fase 4).
- 1.4 `scripts/`: `servidor_iniciar.sh`, `servidor_detener.sh`, `servidor_logs.sh`, `servidor_eventos.sh [N]`, `probar_servidor.sh [ip] [puerto]`. Comparten `_comun.sh`, que se ubica en la raíz del repo para funcionar desde cualquier carpeta.
- 1.6 `docs/protocolo.md` (resumen, campos, validaciones, objeto sala, ejemplo, tabla `eventos`) y `docs/backlog.md`.

Probado (cómo y resultado):
- `servidor_iniciar.sh` ejecutado desde `/tmp`: imagen construida, `quimica_db` healthy, `quimica_servidor` en `0.0.0.0:7777`; muestra la IP LAN 192.168.0.4.
- `probar_servidor.sh` ejecutado desde `/tmp`: 7 pasos (crear, unirse, listo, iniciar, pos, sala inexistente, cambio de anfitrión) → `TODO OK ✔`, exit 0.
- Log del servidor: `Conectado a PostgreSQL`.
- `servidor_eventos.sh 8`: 8 filas (conexion, sala_creada, union, partida_iniciada, desconexion, sala_cerrada).
- `git ls-files --eol`: los `.bat` quedan `w/crlf`.

Pendiente / riesgos:
- La ruta real del repo es `~/Projects/My_Proyect`, no `~/Proyectos/My-project` como dice el brief. No afecta al código (los scripts usan rutas relativas), pero en la 2.1 el proyecto Unity debe crearse **dentro de esta carpeta**.
- Docker nombra la imagen según la carpeta (`my_proyect-servidor`); en Windows será otro nombre. Es cosmético: los contenedores tienen `container_name` fijo.
- El servidor queda corriendo (lo necesitará la 2.6). Se detiene con `scripts/servidor_detener.sh`.

Necesito de Jona:
- 2.1: Unity Hub → *New project* → **Universal 3D** → nombre **`QuimicaVR`**, ubicación **`/home/jad/Projects/My_Proyect/`**. Esperar a que abra, **cerrar el editor** y avisarme.

Commit: b1187f1 (último commit de contenido de la fase; el reporte va en el commit siguiente)
