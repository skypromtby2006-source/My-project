#!/usr/bin/env bash
# Genera el zip de entrega para Windows: dist/QuimicaDemo_Windows_<versión>.zip
#
# Uso: empaquetar.sh [versión] [--servidor-exe CARPETA | --sin-exe]
#   versión          por defecto v0.5
#   --servidor-exe   carpeta QuimicaServidor/ con el .exe (la que genera GitHub Actions).
#                    Por defecto: dist/QuimicaServidor/
#   --sin-exe        arma el zip sin el servidor local (solo para probar el paquete Docker)
#
# Contenido:
#   QuimicaDemo/
#   ├─ Juego/              build de Windows de Unity
#   ├─ Servidor/           servidor local: QuimicaServidor.exe (PyInstaller) + SQLite
#   ├─ ServidorDedicado/   Docker + PostgreSQL, con TODO lo que necesita "docker compose build"
#   └─ LEEME.txt
# Después de generarlo: scripts/probar_paquete.sh dist/QuimicaDemo_Windows_<versión>.zip
set -e
source "$(dirname "$0")/_comun.sh"

VERSION="v0.5"; EXE_DIR="dist/QuimicaServidor"; CON_EXE=true
while [ $# -gt 0 ]; do
  case "$1" in
    --servidor-exe) EXE_DIR="$2"; shift 2 ;;
    --sin-exe) CON_EXE=false; shift ;;
    -*) echo "Opción desconocida: $1"; exit 1 ;;
    *) VERSION="$1"; shift ;;
  esac
done
ZIP="dist/QuimicaDemo_Windows_$VERSION.zip"

[ -f Build/Windows/QuimicaDemo.exe ] || { echo "Falta Build/Windows/QuimicaDemo.exe: genera el build de Windows primero."; exit 1; }
if $CON_EXE && [ ! -f "$EXE_DIR/QuimicaServidor.exe" ]; then
  echo "Falta $EXE_DIR/QuimicaServidor.exe (el servidor local)."
  echo "  Descárgalo de GitHub Actions y descomprímelo en dist/:"
  echo "    gh run download --repo skypromtby2006-source/My-project -n QuimicaServidor_Windows -D dist/"
  echo "  o usa --sin-exe para armar solo el paquete Docker."
  exit 1
fi

# Se arma en una carpeta temporal dentro de dist/ para que el zip tenga una raíz limpia "QuimicaDemo/"
TMP="dist/_armado"
rm -rf "$TMP" && mkdir -p "$TMP/QuimicaDemo"
RAIZ_ZIP="$TMP/QuimicaDemo"

# Juego: el build completo, menos la carpeta de símbolos de Burst ("DoNotShip": solo sirve para depurar)
cp -r Build/Windows "$RAIZ_ZIP/Juego"
rm -rf "$RAIZ_ZIP"/Juego/*_DoNotShip

# Servidor local: la carpeta de PyInstaller tal cual, SIN datos de otra PC
if $CON_EXE; then
  cp -r "$EXE_DIR" "$RAIZ_ZIP/Servidor"
  rm -f "$RAIZ_ZIP"/Servidor/{admin.txt,quimica.db,quimica.db-wal,quimica.db-shm,.env}
  cp entrega/windows/abrir_firewall.bat "$RAIZ_ZIP/Servidor/"
fi

# Servidor dedicado: el MISMO contexto de build que usa el repo (compose con context ".").
# Antes solo se copiaba server.py y la imagen no arrancaba: faltaban los demás módulos,
# niveles/ y el código del panel que compila el Dockerfile. probar_paquete.sh lo vigila.
DED="$RAIZ_ZIP/ServidorDedicado"
mkdir -p "$DED/servidor"
cp docker-compose.yml .dockerignore .env.example "$DED/"
cp servidor/*.py servidor/requirements.txt servidor/Dockerfile "$DED/servidor/"
cp -r servidor/niveles "$DED/servidor/"
rm -f "$DED"/servidor/{servidor_local.py,probar_build.py}   # no los usa la imagen
tar -C . --exclude=node_modules --exclude=dist -cf - panel | tar -C "$DED" -xf -
cp entrega/windows/*.bat "$DED/"
cp entrega/LEEME.txt "$RAIZ_ZIP/"

# Finales CRLF en .bat y LEEME: con LF, cmd.exe ejecuta mal etiquetas y goto.
# La expresión es idempotente: no duplica el \r si ya estaba.
TEXTOS=("$DED"/*.bat "$RAIZ_ZIP/LEEME.txt")
$CON_EXE && TEXTOS+=("$RAIZ_ZIP/Servidor/abrir_firewall.bat")
for f in "${TEXTOS[@]}"; do sed -i 's/\r*$/\r/' "$f"; done
# Comprobación: ninguna línea de esos archivos puede terminar sin \r
for f in "${TEXTOS[@]}"; do
  if grep -qv $'\r$' "$f"; then echo "ERROR: $f tiene líneas sin CRLF"; exit 1; fi
done

rm -f "$ZIP"
(cd "$TMP" && zip -qr -X "../$(basename "$ZIP")" QuimicaDemo)
rm -rf "$TMP"

echo "Generado: $ZIP ($(du -h "$ZIP" | cut -f1))$($CON_EXE || echo '  [SIN servidor local: --sin-exe]')"
unzip -l "$ZIP" | awk 'NR>3 {print $4}' | grep -E '^QuimicaDemo/[^/]+/?$|^QuimicaDemo/(Servidor|ServidorDedicado|Juego)/[^/]+/?$' | sort
echo "Prueba de humo: scripts/probar_paquete.sh $ZIP"
