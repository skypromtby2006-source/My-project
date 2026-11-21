@echo off
REM Servidor dedicado (Docker): carga los datos de la presentacion en PostgreSQL.
REM Requiere el servidor levantado (instalar_servidor.bat).
cd /d "%~dp0"
docker compose exec servidor python demo.py sembrar
pause
