@echo off
cd /d "%~dp0"
docker compose down
echo Servidor detenido (los datos de la BD se conservan).
pause
