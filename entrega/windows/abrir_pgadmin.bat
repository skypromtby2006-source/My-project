@echo off
cd /d "%~dp0"
echo Iniciando pgAdmin (panel web de la base de datos)...
docker compose --profile admin up -d pgadmin
if errorlevel 1 (
  echo [X] Fallo docker compose. Esta Docker Desktop corriendo?
  pause & exit /b 1
)
echo.
echo pgAdmin en: http://127.0.0.1:5050  (tarda unos segundos en arrancar)
echo   Usuario:    admin@example.com
echo   Contrasena: admin123
echo.
echo Para registrar la BD: Add New Server - pestana Connection:
echo   Host: db   Puerto: 5432   BD: quimica   Usuario: quimica   Contrasena: quimica123
timeout /t 5 >nul
start http://127.0.0.1:5050
pause
