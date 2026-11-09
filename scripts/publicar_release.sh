#!/usr/bin/env bash
# Publica la entrega completa en el GitHub Release de un tag: un solo comando.
#
# Uso: publicar_release.sh <tag>          (ej.: publicar_release.sh v0.5-demo)
#
# Antes: crear y subir el tag (git tag <tag> && git push origin <tag>) y esperar a que
# GitHub Actions termine: el workflow construye QuimicaServidor.exe, lo prueba en
# Windows desde el zip y recién entonces crea el Release con ese zip.
# Este script, desde Arch (donde está el build de Unity):
#   1. baja del Release el zip del servidor, para que el .exe del paquete sea EXACTAMENTE
#      el del tag (y el que ya pasó la prueba en Windows),
#   2. empaquetar.sh <tag>  ->  dist/QuimicaDemo_Windows_<tag>.zip
#   3. probar_paquete.sh <zip> docker  (el .exe ya se probó en Windows; aquí no corre)
#   4. gh release upload del zip completo al Release.
set -euo pipefail
source "$(dirname "$0")/_comun.sh"

TAG="${1:?Uso: publicar_release.sh <tag>}"
REPO="skypromtby2006-source/My-project"
ZIP_SERVIDOR="QuimicaServidor_Windows_${TAG}.zip"
ZIP="dist/QuimicaDemo_Windows_${TAG}.zip"

echo "[1/4] Servidor del Release $TAG"
if ! gh release view "$TAG" -R "$REPO" >/dev/null 2>&1; then
  echo "No existe el Release $TAG. ¿Subiste el tag y terminó GitHub Actions?"
  echo "  git push origin $TAG   y mira:  gh run list -R $REPO --workflow servidor-exe.yml -L 3"
  exit 1
fi
DESCARGA="$(mktemp -d)"; trap 'rm -rf "$DESCARGA"' EXIT
gh release download "$TAG" -R "$REPO" -p "$ZIP_SERVIDOR" -D "$DESCARGA" \
  || { echo "El Release $TAG no tiene $ZIP_SERVIDOR (¿falló la prueba del .exe en Actions?)"; exit 1; }
rm -rf dist/QuimicaServidor
python3 -m zipfile -e "$DESCARGA/$ZIP_SERVIDOR" dist/
[ -f dist/QuimicaServidor/QuimicaServidor.exe ] || { echo "El zip del Release no trae QuimicaServidor/QuimicaServidor.exe"; exit 1; }

echo "[2/4] empaquetar.sh $TAG"
scripts/empaquetar.sh "$TAG"

echo "[3/4] probar_paquete.sh (paquete Docker, desde el zip)"
scripts/probar_paquete.sh "$ZIP" docker

echo "[4/4] Subiendo $(basename "$ZIP") al Release $TAG"
gh release upload "$TAG" "$ZIP" -R "$REPO" --clobber
echo
gh release view "$TAG" -R "$REPO" --json url,assets -q '"Release: " + .url, (.assets[] | "  - " + .name)'
