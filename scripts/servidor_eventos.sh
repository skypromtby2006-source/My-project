#!/usr/bin/env bash
# Muestra los últimos eventos guardados en PostgreSQL: evidencia de la integración Python + BD.
# Uso: servidor_eventos.sh [cantidad]   (por defecto 20)
set -e
source "$(dirname "$0")/_comun.sh"
N="${1:-20}"
# Se valida que sea un número porque se interpola dentro del SQL
[[ "$N" =~ ^[0-9]+$ ]] || { echo "La cantidad debe ser un número"; exit 1; }
# -T: sin TTY, para que funcione también desde otros scripts o redirigido a un archivo
docker compose exec -T db psql -U quimica -d quimica \
  -c "SELECT id, tipo, detalle, fecha FROM eventos ORDER BY id DESC LIMIT $N;"
