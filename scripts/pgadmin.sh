#!/usr/bin/env bash
# Levanta pgAdmin (perfil "admin" del compose) para revisar la BD desde el navegador.
set -e
source "$(dirname "$0")/_comun.sh"

docker compose --profile admin up -d pgadmin
echo
echo "pgAdmin en: http://127.0.0.1:5050  (tarda unos segundos en arrancar)"
echo "  Usuario:    admin@example.com"
echo "  Contraseña: admin123"
echo
echo "Para registrar la BD: Add New Server → pestaña Connection:"
echo "  Host: db   Puerto: 5432   BD: quimica   Usuario: quimica   Contraseña: quimica123"
