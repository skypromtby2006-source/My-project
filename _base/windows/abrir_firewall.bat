@echo off
net session >nul 2>&1
if errorlevel 1 (
  echo Ejecuta este archivo con clic derecho - "Ejecutar como administrador".
  pause & exit /b 1
)
netsh advfirewall firewall add rule name="Quimica Servidor 7777" dir=in action=allow protocol=TCP localport=7777
echo Puerto 7777 abierto en el firewall de Windows.
pause
