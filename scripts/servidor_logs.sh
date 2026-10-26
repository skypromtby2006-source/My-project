#!/usr/bin/env bash
# Muestra en vivo los registros del servidor (Ctrl+C para salir).
source "$(dirname "$0")/_comun.sh"
docker compose logs -f servidor
