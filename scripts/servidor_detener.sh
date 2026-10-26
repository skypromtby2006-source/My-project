#!/usr/bin/env bash
# Detiene los contenedores. Sin "-v": el volumen de la BD (y sus eventos) se conserva.
set -e
source "$(dirname "$0")/_comun.sh"
docker compose down
echo "Servidor detenido (los datos de la BD se conservan)."
