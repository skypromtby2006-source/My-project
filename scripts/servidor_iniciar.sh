#!/usr/bin/env bash
# Construye e inicia el servidor + PostgreSQL y muestra las IP para conectar.
set -e
source "$(dirname "$0")/_comun.sh"

docker compose up -d --build
echo
docker compose ps
echo
echo "Servidor en el puerto 7777."
echo " - En esta PC conecta a: 127.0.0.1"
echo " - Desde otra PC de la red usa alguna de estas IP:"
# Se omite loopback y las redes virtuales de Docker, que no sirven desde otra PC
ip -4 -o addr show | awk '$2 != "lo" && $2 !~ /^(docker|br-|veth)/ {split($4, a, "/"); print "     " a[1] "  (" $2 ")"}'
