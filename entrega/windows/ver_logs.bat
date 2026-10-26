@echo off
cd /d "%~dp0"
echo Mostrando registros del servidor (Ctrl+C para salir)...
docker compose logs -f servidor
