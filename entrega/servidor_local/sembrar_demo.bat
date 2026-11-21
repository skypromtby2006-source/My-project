@echo off
REM Carga los datos de la presentacion (docente_demo, clase, reto y 4 estudiantes con intentos).
REM Se puede correr con el servidor abierto o cerrado, y dos veces: no duplica nada.
cd /d "%~dp0"
QuimicaServidor.exe --sembrar-demo
echo.
echo Las credenciales quedaron en demo_credenciales.txt (en esta carpeta).
pause
