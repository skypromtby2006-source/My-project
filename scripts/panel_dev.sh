#!/usr/bin/env bash
# Panel en modo desarrollo: Vite en http://localhost:5173 con recarga al guardar.
# Las llamadas a /api (y el WebSocket) se reenvían al servidor real en :8000, así
# que antes hay que levantarlo (servidor_iniciar.sh).
set -e
source "$(dirname "$0")/_comun.sh"
cd panel
[ -d node_modules ] || npm install --no-audit --no-fund
npm run dev
