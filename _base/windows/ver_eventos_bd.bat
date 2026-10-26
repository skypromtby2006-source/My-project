@echo off
cd /d "%~dp0"
echo Ultimos 20 eventos guardados en PostgreSQL:
docker compose exec db psql -U quimica -d quimica -c "SELECT id, tipo, detalle, fecha FROM eventos ORDER BY id DESC LIMIT 20;"
pause
