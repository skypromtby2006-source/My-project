#!/usr/bin/env bash
# Prueba perfiles y progreso, recrea el contenedor del servidor y comprueba
# que el progreso sigue ahí: así se verifica que viene de PostgreSQL y no de la memoria.
# Uso: probar_perfiles.sh   (requiere el servidor levantado con Docker)
set -eo pipefail
source "$(dirname "$0")/_comun.sh"

salida=$(python3 servidor/probar_perfiles.py 127.0.0.1 7777 | tee /dev/stderr)
usuario=$(grep -oP '^USUARIO_PERSISTENCIA=\K\S+' <<<"$salida")

echo; echo "Recreando el servidor para probar la persistencia..."
docker compose up -d --build --force-recreate servidor
# No basta con que el puerto responda: el proxy de Docker acepta la conexión
# antes de que el servidor esté escuchando. Se espera la línea del log.
for _ in $(seq 1 30); do
    docker compose logs servidor 2>/dev/null | grep -q "Servidor escuchando" && break
    sleep 1
done
python3 servidor/probar_perfiles.py --persistencia "$usuario" 127.0.0.1 7777
