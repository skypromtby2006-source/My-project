#!/usr/bin/env bash
# Prueba el build REAL de Linux (sin ventana).
# Uso: probar_build.sh [escenario ...]   (sin argumentos: todos)
# Escenarios:
#   laberinto, laberinto_player  -> el juego nuevo (S4). Levantan su PROPIO servidor
#       con semilla fija (puerto 7788, en memoria): no necesitan Docker y conocen las
#       respuestas de los puzzles. "laberinto" incluye el door-cross físico (una puerta
#       cerrada bloquea; al abrirse, deja pasar).
#   sesion, reinicio, panel      -> usan el servidor de Docker (servidor_iniciar.sh).
#       "reinicio" reinicia el servidor con servidor_detener.sh + servidor_iniciar.sh;
#       "panel" necesita ADMIN_PASSWORD en el .env.
# Requiere Build/Linux al día (Quimica/3. Build Linux). Se corre con el Python del venv
# para que el servidor del laberinto tenga sus dependencias (fastapi, etc.).
set -e
source "$(dirname "$0")/_comun.sh"
PY="$RAIZ/.venv/bin/python"; [ -x "$PY" ] || PY=python3
"$PY" servidor/probar_build.py "$@"
