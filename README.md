# Juego de Química VR — Demo multijugador (v0.1)

Demo del sprint 0: un servidor **Python + PostgreSQL** en Docker y un cliente **Unity 6.3 (URP)** para Windows y Linux.
Los jugadores se conectan por IP, crean una sala o se unen a una (desde la lista o con un código de 4 letras), marcan "Listo", el anfitrión inicia la partida y todos se ven moverse en tiempo real.

> Todavía no tiene VR, login ni contenido de química: eso queda para los siguientes sprints (ver [`docs/backlog.md`](docs/backlog.md)).

## Arquitectura

1. **Servidor** (`servidor/server.py`): Python asyncio sobre TCP, puerto **7777**. Un solo hilo atiende a todos los jugadores y es autoritativo: valida cada acción.
2. **Protocolo**: un mensaje JSON por línea. Detalle en [`docs/protocolo.md`](docs/protocolo.md).
   El porqué de cada decisión está en [`docs/decisiones.md`](docs/decisiones.md).
3. **Base de datos**: PostgreSQL 16 guarda un registro de eventos (conexiones, salas, partidas). Es opcional: si cae, el servidor sigue funcionando en memoria.
4. **Cliente Unity** (`QuimicaVR/Assets/Scripts/Red/`): `ClienteRed` maneja el socket en un hilo aparte, `MenuLobby` dibuja el menú con IMGUI y `GestorPartida` crea el escenario y sincroniza las posiciones 15 veces por segundo, con interpolación.
5. **Docker Compose** levanta el servidor y la BD juntos, así la demo corre igual en cualquier PC sin instalar Python ni PostgreSQL.

## Linux (desarrollo)

Requisitos: Docker con Compose (sin `sudo`), Python 3 y Unity `6000.3.27f1` con *Windows Build Support (Mono)*.

| Script | Qué hace |
|---|---|
| `scripts/servidor_iniciar.sh` | Construye e inicia el servidor y la BD, y muestra las IP de la PC |
| `scripts/servidor_detener.sh` | Detiene los contenedores (los datos de la BD se conservan) |
| `scripts/servidor_logs.sh` | Log del servidor en vivo |
| `scripts/servidor_eventos.sh [N]` | Últimos N eventos guardados en PostgreSQL |
| `scripts/probar_servidor.sh` | Prueba de 2 jugadores simulados, sin Unity → `TODO OK ✔` |
| `scripts/jugar_linux.sh [N]` | Abre N instancias del build de Linux (logs en `logs/`) |
| `scripts/empaquetar.sh [versión]` | Genera `dist/QuimicaDemo_Windows_<versión>.zip` |

Los scripts funcionan desde cualquier carpeta del repo.

**Builds de Unity** (con el editor cerrado):

```bash
UNITY=~/Unity/Hub/Editor/6000.3.27f1/Editor/Unity
"$UNITY" -batchmode -nographics -quit -projectPath QuimicaVR -logFile logs/build.log \
  -executeMethod Quimica.EditorTools.Construir.Linux     # o .Windows
```

Salen en `Build/Linux/` y `Build/Windows/`. Desde el editor: menú **Quimica → 2/3. Build**.
La escena `Demo.unity` y los ajustes del proyecto se generan con **Quimica → 1. Configurar escena demo** (`Assets/Editor/ConfigurarDemo.cs`); no se editan a mano.

**Prueba rápida:**

```bash
scripts/servidor_iniciar.sh
scripts/jugar_linux.sh 2      # A crea la sala, B se une y marca Listo, A inicia → WASD
scripts/servidor_eventos.sh
```

## Windows (entrega)

Descomprime `QuimicaDemo_Windows_v0.1.zip` y sigue su `LEEME.txt`:

1. Instala **Docker Desktop** y espera a que diga *Engine running*.
2. `Servidor\instalar_servidor.bat`: levanta el servidor y muestra las IP.
3. Abre `Juego\QuimicaDemo.exe` dos veces y conecta a `127.0.0.1`.

Si otra PC de la red no puede conectar, ejecuta `Servidor\abrir_firewall.bat` como administrador.

## Estructura

```
servidor/          servidor Python (server.py, Dockerfile, probar_cliente.py)
docker-compose.yml servidor + PostgreSQL
QuimicaVR/         proyecto Unity (Assets/Scripts/Red, Assets/Editor)
scripts/           scripts .sh de Linux
entrega/           .bat de Windows y LEEME.txt del zip
docs/              protocolo, backlog y reportes de cada fase
```
