#!/usr/bin/env bash
# Construye e inicia el servidor + PostgreSQL y muestra las IP para conectar.
set -e
source "$(dirname "$0")/_comun.sh"

docker compose up -d --build
# Se espera a que el servidor escuche: el proxy de Docker acepta conexiones en el 7777
# antes, y un juego que conecta en ese momento queda cortado (bug B4 de la S2-3).
echo -n "Esperando al servidor"
for _ in $(seq 1 60); do
  docker compose logs servidor 2>/dev/null | grep -q "Servidor escuchando" && break
  echo -n "."; sleep 1
done
echo
docker compose logs servidor 2>/dev/null | grep -q "Servidor escuchando" \
  || { echo "El servidor no arrancó en 60 s: revisa scripts/servidor_logs.sh"; exit 1; }
echo
docker compose ps
echo
echo "Servidor en el puerto 7777."
echo " - En esta PC conecta a: 127.0.0.1"
echo " - Desde otra PC de la red usa alguna de estas IP:"
# Se omite loopback y las redes virtuales de Docker, que no sirven desde otra PC
ip -4 -o addr show | awk '$2 != "lo" && $2 !~ /^(docker|br-|veth)/ {split($4, a, "/"); print "     " a[1] "  (" $2 ")"}'
