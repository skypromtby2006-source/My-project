@echo off
REM Borra SOLO los datos de la demo (docente_demo, su clase y su reto, y los *_demo).
cd /d "%~dp0"
QuimicaServidor.exe --limpiar-demo
pause
