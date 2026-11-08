@echo off
title Servidor Quimica - Sin Docker (Plan B2)
cd /d "%~dp0"
echo ==================================================
echo   Servidor multijugador - Juego de Quimica (demo)
echo   Plan B2: Python directo, sin Docker ni base de datos
echo ==================================================
echo.

REM Primero "py -3" (el lanzador de python.org) y despues "python".
REM Por que: en Windows 11, "python" puede ser el alias de Microsoft Store, que
REM no es Python y solo abre la tienda. El lanzador "py" no tiene ese problema.
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto python_ok
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto python_ok
echo [X] Python no esta instalado.
echo     Descarga Python 3: https://www.python.org/downloads/
echo     Al instalarlo, marca "Add python.exe to PATH" y vuelve a ejecutar este archivo.
start https://www.python.org/downloads/
pause & exit /b 1
:python_ok

REM server.py usa asyncio moderno: hace falta Python 3.8 o mas nuevo
%PY% -c "import sys; sys.exit(sys.version_info < (3, 8))"
if errorlevel 1 (
  echo [X] Hace falta Python 3.8 o mas nuevo. Esta PC tiene:
  %PY% --version
  pause & exit /b 1
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo [1/3] %%v encontrado.

REM El venv se crea una sola vez en Servidor\.venv: asi no se instala nada en
REM el Python del sistema, y para desinstalar basta con borrar la carpeta.
if exist ".venv\Scripts\python.exe" goto venv_ok
echo [2/3] Creando el entorno de Python (solo la primera vez)...
%PY% -m venv .venv
if errorlevel 1 (
  echo [X] No se pudo crear el entorno en Servidor\.venv
  pause & exit /b 1
)
:venv_ok

REM La marca evita repetir pip en cada arranque, asi el servidor tambien
REM arranca sin internet despues de la primera vez.
if exist ".venv\instalado.txt" goto pip_ok
echo [2/3] Instalando dependencias (necesita internet)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r servidor\requirements.txt
if errorlevel 1 (
  REM No es fatal: requirements.txt solo trae asyncpg, que se usa con la base
  REM de datos. Sin DATABASE_URL, server.py ni lo importa.
  echo [!] Fallo pip install. Se sigue igual: sin base de datos no hace falta.
  goto pip_ok
)
echo ok> ".venv\instalado.txt"
:pip_ok

REM Se vacia por si la PC tiene la variable definida: el Plan B2 corre sin BD
set "DATABASE_URL="

echo.
echo ==================================================
echo  SERVIDOR en el puerto 7777 (espera "Servidor escuchando")
echo  - En esta PC conecta a:   127.0.0.1
echo  - Desde otra PC de la red usa alguna de estas IP:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo        %%a
echo.
echo  Sin base de datos: los perfiles y el progreso se pierden al cerrar
echo  esta ventana. Si Windows pregunta por el firewall, elige "Permitir".
echo  Para apagar el servidor: cierra esta ventana o pulsa Ctrl+C.
echo ==================================================
echo.
echo [3/3] Iniciando el servidor...
".venv\Scripts\python.exe" servidor\server.py
echo.
echo El servidor se detuvo.
pause
