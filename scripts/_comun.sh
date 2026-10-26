# Se carga con "source" desde los demás scripts.
# Ubica la raíz del repo a partir de la ruta del script, así los scripts
# funcionan sin importar desde qué carpeta se ejecuten.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ" || exit 1
