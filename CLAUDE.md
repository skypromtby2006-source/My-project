# CLAUDE.md — Juego de Química VR · Sprint 0: Demo multijugador

> Brief para Claude Code. Léelo completo antes de tocar nada.
> Idioma de trabajo: **español** (código, commits, comentarios y reportes).

## 1. Equipo y roles

| Rol | Quién | Responsabilidad |
|---|---|---|
| Cliente | **Jona** | Define qué se quiere, aprueba entregables y hace lo manual en el editor de Unity y en Unity Hub |
| Project Manager | **Claude (chat)** | Escribió este brief y revisa los reportes de fase |
| Equipo de desarrollo | **Claude Code (tú)** + Jona en el editor | Implementar, probar y documentar |

Cuando una tarea diga **🧑 JONA**, **detente**: dile exactamente qué tiene que hacer y espera su confirmación.
Las tareas marcadas **🤖 CLAUDE CODE** son tuyas.

## 2. Objetivo del sprint (entrega: HOY 26/10/2026, en la noche)

Demo jugable con:
1. **Ejecutable para Windows** (`.exe`) generado desde Unity en Linux
2. **Servidor Python instalable con Docker** (más PostgreSQL)
3. **Conexión local** del juego al servidor (IP + puerto 7777)
4. **Multijugador**: crear sala, unirse a sala (por lista o por código), "Listo", el anfitrión inicia y los jugadores se ven moverse

### ⛔ Alcance congelado
No se agregan funciones nuevas en este sprint: ni login, ni VR, ni UI bonita, ni química. Si surge una idea, anótala en `docs/backlog.md` y sigue.
**Por qué:** el plazo es de horas. Una demo pequeña que funciona vale más que una grande que se cae en la presentación.

## 3. Contexto técnico

- **SO de desarrollo:** Arch Linux (Hyprland), terminal kitty. Jona también tiene Windows 11 en dual boot, que sirve para la prueba final del `.exe`.
- **Unity:** 6.3 LTS (`6000.3.27f1`) instalado con Unity Hub y el módulo **Windows Build Support (Mono)**.
  - Ruta típica del editor: `~/Unity/Hub/Editor/6000.3.27f1/Editor/Unity`. Verifícala con `ls ~/Unity/Hub/Editor/`.
- **Repositorio:** `https://github.com/skypromtby2006-source/My-project.git` (vacío al empezar), rama `main`.
- **Código base ya probado** en la carpeta `_base/` (lo escribió el PM; el servidor pasó la prueba de 2 jugadores simulados):
  - `_base/servidor/`: `server.py` (asyncio + TCP, un JSON por línea), `Dockerfile`, `requirements.txt` y `probar_cliente.py` (test sin Unity)
  - `_base/docker-compose.yml`: servicio `servidor` + servicio `db` (Postgres 16)
  - `_base/unity/Scripts/`: `ClienteRed.cs`, `MenuLobby.cs` (IMGUI) y `GestorPartida.cs`
  - `_base/unity/Editor/`: `ConfigurarDemo.cs` (arma la escena por código) y `Construir.cs` (builds por menú o batch)
  - `_base/windows/*.bat`: scripts para la PC Windows que recibirá la demo
  - `_base/LEEME_demo_anterior.md`: explicación del protocolo y de las decisiones de diseño. **Léelo.**

## 4. Estructura objetivo del repo

```
My-project/
├─ CLAUDE.md
├─ README.md                  ← cómo correr todo (Linux y Windows)
├─ .gitignore                 ← Unity + Python + Build/ + dist/
├─ docker-compose.yml
├─ servidor/                  ← Python (server.py, Dockerfile, requirements.txt, probar_cliente.py)
├─ QuimicaVR/                 ← proyecto Unity (lo crea JONA con Unity Hub)
│  └─ Assets/
│     ├─ Scripts/Red/         ← ClienteRed, MenuLobby, GestorPartida
│     ├─ Editor/              ← ConfigurarDemo, Construir
│     └─ Scenes/Demo.unity    ← generada por ConfigurarDemo
├─ scripts/                   ← .sh para Linux (desarrollo)
├─ entrega/windows/           ← .bat que van dentro del zip de entrega
├─ docs/
│  ├─ protocolo.md
│  ├─ backlog.md
│  └─ reportes/               ← reporte de cada fase para el PM
├─ Build/                     ← (ignorado por git) salida de Unity
└─ dist/                      ← (ignorado por git) zip final de entrega
```

## 5. Reglas del equipo de desarrollo

1. **Nunca uses `sudo`.** Si hace falta, dale a Jona el comando exacto y espera su respuesta.
2. **No edites a mano** los `.unity`, `.prefab`, `.asset` ni `ProjectSettings/*`. Todo cambio de escena o de configuración se hace con scripts de Editor (`Assets/Editor/`).
   **Por qué:** son YAML con referencias internas (fileID/guid); editarlos a mano los corrompe fácilmente.
3. **Nunca toques** `QuimicaVR/Library`, `Temp`, `Logs`, `obj` ni `UserSettings`.
4. **Modo batch de Unity:** antes de usarlo, el editor **debe estar cerrado**. Revisa que no exista `QuimicaVR/Temp/UnityLockfile` y, si existe, pide a Jona que cierre Unity. Comando base:
   ```bash
   UNITY=~/Unity/Hub/Editor/6000.3.27f1/Editor/Unity
   "$UNITY" -batchmode -nographics -quit -projectPath QuimicaVR -logFile logs/unity_<tarea>.log [-executeMethod ...]
   ```
   Después, revisa el log: `grep -E "error CS|\[Quimica\]|Exception" logs/unity_*.log`. La carpeta `logs/` está ignorada por git.
   Si aparece un error de licencia, pídele a Jona que abra el proyecto una vez desde Unity Hub con su sesión iniciada.
5. **No cambies el protocolo** (los mensajes JSON) sin actualizar `docs/protocolo.md` y ambos lados (Python y C#).
6. **Commits pequeños**, uno por tarea, en español y con prefijo: `feat:`, `fix:`, `chore:`, `docs:`, `build:`. Haz push a `origin main` al cerrar cada fase.
7. **Comentarios que expliquen el porqué**, no el qué. Jona tiene que poder defender el código ante su docente.
8. **Cultura numérica:** cualquier número que viaje en el JSON se formatea con `InvariantCulture`. Si no, en un Windows en español se envía `1,5` y el JSON se rompe.
9. Al cerrar cada fase, escribe `docs/reportes/fase-N.md` y muéstralo en la terminal con esta plantilla:
   ```
   ## Reporte Fase N — <nombre>
   Hecho: ...
   Probado (cómo y resultado): ...
   Pendiente / riesgos: ...
   Necesito de Jona: ...
   Commit: <hash>
   ```
   Jona se lo pasa al PM para su revisión.
10. Marca las casillas de la sección 6 de este archivo a medida que avances.

## 6. Plan de trabajo

### Fase 0 — Preparación · 🧑 JONA (antes de abrir Claude Code)
- [x] Unity Hub → instalar **Unity 6.3 LTS (6000.3.27f1)** con el módulo **Windows Build Support (Mono)**. Linux Build Support ya viene incluido.
- [x] Instalar las dependencias:
  ```bash
  sudo pacman -S --needed git github-cli docker docker-compose docker-buildx python zip
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER    # luego CERRAR SESIÓN y volver a entrar
  gh auth login                    # GitHub.com → HTTPS → login con el navegador
  ```
- [x] Clonar el repo y meter el kickoff:
  ```bash
  mkdir -p ~/Proyectos && cd ~/Proyectos
  git clone https://github.com/skypromtby2006-source/My-project.git
  # copiar CLAUDE.md y la carpeta _base/ dentro de My-project/
  cd My-project && claude
  ```
- [x] Primer mensaje a Claude Code: *"Lee CLAUDE.md y arranca la Fase 1"*.

### Fase 1 — Repo + servidor · 🤖 CLAUDE CODE
- [x] 1.1 Verificar el entorno: `docker info` (sin sudo), `docker compose version`, `python --version`, `git`, `gh auth status` y la ruta del editor Unity. Si algo falla, regla 1.
- [x] 1.2 Crear `.gitignore`: el estándar de Unity aplicado a `QuimicaVR/`, más `__pycache__/`, `.venv/`, `Build/`, `dist/`, `logs/` y `*.log`.
- [x] 1.3 Mover el código desde `_base/` a la estructura de la sección 4 (servidor, compose y `.bat` a `entrega/windows/`).
- [x] 1.4 Crear `scripts/` para Linux (con `chmod +x`), todos usando `docker compose` y ejecutables desde cualquier carpeta del repo:
  - `servidor_iniciar.sh`: `up -d --build`, luego `ps` y muestra las IPs locales (`ip -4 addr`)
  - `servidor_detener.sh`, `servidor_logs.sh`, `servidor_eventos.sh` (consulta a la tabla `eventos` con psql dentro del contenedor)
  - `probar_servidor.sh`: corre `servidor/probar_cliente.py` contra `127.0.0.1:7777`
- [x] 1.5 Levantar con Docker y correr `probar_servidor.sh`. **Criterio de terminado:** termina en `TODO OK ✔`, el log dice `Conectado a PostgreSQL` y `servidor_eventos.sh` muestra filas.
- [x] 1.6 Escribir `docs/protocolo.md` (tabla de mensajes, tomada del LEEME anterior) y `docs/backlog.md` (vacío, con encabezado).
- [x] 1.7 Commit, push y reporte de la Fase 1. **No borres `_base/` todavía.**

### Fase 2 — Proyecto Unity · 🧑 JONA, luego 🤖 CLAUDE CODE
- [x] 2.1 🧑 Unity Hub → *New project* → **Universal 3D** → nombre **`QuimicaVR`**, ubicación `~/Proyectos/My-project/`. Esperar a que abra, cerrar el editor y avisar a Claude Code.
  **Por qué URP:** es el pipeline que se usará luego para VR, así no hay que migrar después.
- [x] 2.2 🤖 Copiar `_base/unity/Scripts/*` → `QuimicaVR/Assets/Scripts/Red/` y `_base/unity/Editor/*` → `QuimicaVR/Assets/Editor/`.
- [x] 2.3 🤖 Compilar en batch (sin `-executeMethod`). **Criterio:** cero `error CS` en el log. Si hay errores, corregirlos respetando la regla 5.
- [x] 2.4 🤖 Ejecutar en batch `-executeMethod Quimica.EditorTools.ConfigurarDemo.Configurar`. **Criterio:** existe `Assets/Scenes/Demo.unity` y el log muestra `[Quimica] Escena demo configurada`.
- [x] 2.5 🤖 Commit (incluyendo los `.meta`, `Packages/` y `ProjectSettings/`) y push.
- [x] 2.6 🧑 Abrir el proyecto en el editor, abrir `Assets/Scenes/Demo.unity` y darle **Play** con el servidor arriba: conectar a `127.0.0.1` y crear una sala. Confirmar a Claude Code que se ve el código de sala, o pasarle el error de la consola.
- [x] 2.7 🤖 Reporte de la Fase 2.

### Fase 3 — Builds y prueba en Linux · 🤖 CLAUDE CODE, luego 🧑 JONA
- [x] 3.1 🤖 Pedir a Jona que cierre el editor. Luego, en batch, ejecutar `Quimica.EditorTools.Construir.Linux` y después `Quimica.EditorTools.Construir.Windows`. **Criterio:** existen `Build/Linux/QuimicaDemo.x86_64` y `Build/Windows/QuimicaDemo.exe`, y el log muestra `Succeeded`.
- [x] 3.2 🤖 Crear `scripts/jugar_linux.sh N`, que abre N instancias del build de Linux.
- [x] 3.3 🧑 Prueba multijugador en Arch: servidor arriba, `jugar_linux.sh 2`, A crea sala, B se une y marca Listo, A inicia y los dos se mueven con WASD. Además: cerrar A y verificar que B pasa a ser anfitrión.
- [x] 3.4 🤖 Corregir lo que Jona reporte, re-build, commit y reporte de la Fase 3.

### Fase 4 — Paquete de entrega Windows · 🤖 CLAUDE CODE
- [x] 4.1 Crear `scripts/empaquetar.sh`, que genere `dist/QuimicaDemo_Windows_v0.1.zip` con:
  ```
  QuimicaDemo/
  ├─ Juego/          ← todo Build/Windows/
  ├─ Servidor/       ← docker-compose.yml + servidor/ + los .bat de entrega/windows/
  └─ LEEME.txt       ← pasos para Windows (Docker Desktop → instalar_servidor.bat → abrir el juego)
  ```
  Comprobar que los `.bat` tengan finales de línea **CRLF**. **Por qué:** con LF, `cmd.exe` puede ejecutar mal las etiquetas y los `goto`.
- [x] 4.2 Escribir el `README.md` del repo: qué es, cómo correrlo en Linux (scripts/) y en Windows (zip), arquitectura en 5 líneas y el enlace a `docs/protocolo.md`.
- [x] 4.3 Borrar `_base/` (ya migrado), hacer commit, `git tag v0.1-demo`, push con tags y reporte de la Fase 4.

### Fase 5 — Prueba real en Windows · 🧑 JONA
- [ ] 5.1 Copiar el zip a un USB o al disco de Windows y reiniciar en **Windows 11**.
- [ ] 5.2 Docker Desktop → `instalar_servidor.bat` → abrir `QuimicaDemo.exe` dos veces → repetir la prueba de la 3.3.
- [ ] 5.3 Si algo falla, volver a Arch y pasarle el error a Claude Code.
  **Por qué esta fase:** el entregable es para Windows. Probarlo en el mismo sistema que usará el docente es la única garantía real.

## 7. Definición de "terminado" del sprint
- [ ] `dist/QuimicaDemo_Windows_v0.1.zip` probado en Windows 11 con 2 instancias
- [ ] Servidor levantado con Docker y eventos visibles en PostgreSQL
- [ ] Repo en GitHub con el tag `v0.1-demo`, el README y los reportes de fase

## 8. Fuera de este sprint (backlog conocido)
Login y perfiles · progreso estilo Steam Cloud · roles estudiante/docente/admin · servidor dedicado · VR (XR Interaction Toolkit) · UI definitiva con Canvas/UI Toolkit · instalador `.exe` con Inno Setup (hay una versión en el zip anterior) · escenarios de química.
