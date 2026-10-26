#!/usr/bin/env bash
# Detiene los contenedores. Sin "-v": el volumen de la BD (y sus eventos) se conserva.
set -e
source "$(dirname "$0")/_comun.sh"
# --profile admin: sin él, "down" deja vivo a pgAdmin y la red queda en uso
docker compose --profile admin down
echo "Servidor detenido (los datos de la BD se conservan)."
