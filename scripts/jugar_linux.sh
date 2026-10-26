#!/usr/bin/env bash
# Abre N instancias del build de Linux para probar el multijugador en una sola PC.
# Uso: jugar_linux.sh [N]   (por defecto 2)
set -e
source "$(dirname "$0")/_comun.sh"
N="${1:-2}"
[[ "$N" =~ ^[1-9][0-9]*$ ]] || { echo "N debe ser un número mayor que 0"; exit 1; }

JUEGO="Build/Linux/QuimicaDemo.x86_64"
[ -x "$JUEGO" ] || { echo "No existe $JUEGO. Genera el build primero (Quimica/3. Build Linux)."; exit 1; }

# Sin servidor el juego solo muestra "No se pudo conectar"; se avisa antes para no perder tiempo.
# Se usa ss (¿hay algo escuchando?) en vez de conectarse: una conexión de prueba
# ensuciaría los logs del servidor y dejaría un evento falso en la BD.
if [ -z "$(ss -ltnH 'sport = :7777' 2>/dev/null)" ]; then
  echo "Aviso: no hay servidor en 127.0.0.1:7777 (scripts/servidor_iniciar.sh)."
fi

mkdir -p logs
for i in $(seq 1 "$N"); do
  # Un log por instancia: si no, todas escriben el mismo Player.log y se pisan.
  # Ruta absoluta: el player resuelve las rutas relativas desde la carpeta del ejecutable
  # setsid: las ventanas siguen abiertas aunque se cierre esta terminal
  setsid "$JUEGO" -screen-fullscreen 0 -screen-width 1280 -screen-height 720 \
    -logFile "$RAIZ/logs/jugador_$i.log" >/dev/null 2>&1 &
  echo "Jugador $i abierto (log: logs/jugador_$i.log)"
  sleep 1   # escalonado para que las ventanas no se abran todas encima al mismo tiempo
done
