#!/usr/bin/env bash
# Genera el zip de entrega para Windows: dist/QuimicaDemo_Windows_<versión>.zip
# Uso: empaquetar.sh [versión]   (por defecto v0.1)
set -e
source "$(dirname "$0")/_comun.sh"
VERSION="${1:-v0.1}"
ZIP="dist/QuimicaDemo_Windows_$VERSION.zip"

[ -f Build/Windows/QuimicaDemo.exe ] || { echo "Falta Build/Windows/QuimicaDemo.exe: genera el build de Windows primero."; exit 1; }

# Se arma en una carpeta temporal dentro de dist/ para que el zip tenga una raíz limpia "QuimicaDemo/"
TMP="dist/_armado"
rm -rf "$TMP" && mkdir -p "$TMP/QuimicaDemo"
RAIZ_ZIP="$TMP/QuimicaDemo"

# Juego: el build completo, menos la carpeta de símbolos de Burst ("DoNotShip": solo sirve para depurar)
cp -r Build/Windows "$RAIZ_ZIP/Juego"
rm -rf "$RAIZ_ZIP"/Juego/*_DoNotShip

# Servidor: compose + código Python + .bat, todo junto porque los .bat hacen "cd" a su propia carpeta
mkdir -p "$RAIZ_ZIP/Servidor/servidor"
cp docker-compose.yml "$RAIZ_ZIP/Servidor/"
cp servidor/{server.py,Dockerfile,requirements.txt,probar_cliente.py} "$RAIZ_ZIP/Servidor/servidor/"
cp entrega/windows/*.bat "$RAIZ_ZIP/Servidor/"
cp entrega/LEEME.txt "$RAIZ_ZIP/"

# Finales CRLF en .bat y LEEME: con LF, cmd.exe ejecuta mal etiquetas y goto.
# La expresión es idempotente: no duplica el \r si ya estaba.
for f in "$RAIZ_ZIP"/Servidor/*.bat "$RAIZ_ZIP/LEEME.txt"; do
  sed -i 's/\r*$/\r/' "$f"
done
# Comprobación: ninguna línea de esos archivos puede terminar sin \r
for f in "$RAIZ_ZIP"/Servidor/*.bat "$RAIZ_ZIP/LEEME.txt"; do
  if grep -qv $'\r$' "$f"; then echo "ERROR: $f tiene líneas sin CRLF"; exit 1; fi
done

rm -f "$ZIP"
(cd "$TMP" && zip -qr -X "../$(basename "$ZIP")" QuimicaDemo)
rm -rf "$TMP"

echo "Generado: $ZIP ($(du -h "$ZIP" | cut -f1))"
unzip -l "$ZIP" | awk 'NR>3 {print $4}' | grep -E '^QuimicaDemo/[^/]+/?$|^QuimicaDemo/(Servidor|Juego)/[^/]+/?$' | sort
