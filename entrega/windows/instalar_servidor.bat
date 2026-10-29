@echo off
title Servidor Quimica - Instalacion
cd /d "%~dp0"
echo ==================================================
echo   Servidor multijugador - Juego de Quimica (demo)
echo ==================================================
echo.

docker --version >nul 2>&1
if errorlevel 1 (
  echo [X] Docker no esta instalado.
  echo     Descarga Docker Desktop: https://www.docker.com/products/docker-desktop/
  echo     Instalalo, reinicia la PC y vuelve a ejecutar este archivo.
  start https://www.docker.com/products/docker-desktop/
  pause & exit /b 1
)

docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
echo [!] Docker esta instalado pero no esta corriendo.
echo     Abriendo Docker Desktop... espera a que diga "Engine running".
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
:esperar
timeout /t 5 >nul
docker info >nul 2>&1
if errorlevel 1 goto esperar
:docker_ok

echo [1/2] Construyendo e iniciando contenedores (la primera vez tarda unos minutos)...
docker compose up -d --build
if errorlevel 1 (
  echo [X] Fallo docker compose. Revisa el mensaje de arriba.
  pause & exit /b 1
)

REM Se espera a que el servidor escuche: Docker acepta conexiones en el 7777 antes,
REM y un juego que conecta en ese momento queda cortado.
echo Esperando al servidor...
set /a intentos=0
:esperar_servidor
docker compose logs servidor 2>nul | findstr /c:"Servidor escuchando" >nul
if not errorlevel 1 goto servidor_ok
set /a intentos+=1
if %intentos% geq 60 (
  echo [X] El servidor no arranco en 60 segundos. Revisa ver_logs.bat
  pause & exit /b 1
)
timeout /t 1 >nul
goto esperar_servidor
:servidor_ok

echo.
echo [2/2] Estado:
docker compose ps
echo.
echo ==================================================
echo  SERVIDOR LISTO en el puerto 7777
echo  - En esta PC conecta a:   127.0.0.1
echo  - Desde otra PC de la red usa alguna de estas IP:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo        %%a
echo.
echo  Si otra PC no conecta, ejecuta abrir_firewall.bat como administrador.
echo ==================================================
pause
