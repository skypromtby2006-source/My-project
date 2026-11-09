#!/usr/bin/env bash
# Prueba el build REAL de Linux (sin ventana) contra el servidor de Docker.
# Uso: probar_build.sh [escenario ...]   (wizard, player, sesion, reinicio, progreso, panel; sin argumentos: todos)
# Requiere Build/Linux al día y el servidor levantado (servidor_iniciar.sh).
# Ojo: "progreso" reinicia el servidor con servidor_detener.sh + servidor_iniciar.sh.
set -e
source "$(dirname "$0")/_comun.sh"
python3 servidor/probar_build.py "$@"
