#!/usr/bin/env bash
# Prueba el servidor sin Unity: simula 2 jugadores contra 127.0.0.1:7777.
# Uso: probar_servidor.sh [ip] [puerto]
source "$(dirname "$0")/_comun.sh"
# El test solo usa la biblioteca estándar, así que cualquier Python 3 sirve
python3 servidor/probar_cliente.py "${1:-127.0.0.1}" "${2:-7777}"
