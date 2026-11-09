#!/usr/bin/env bash
# Corre la batería de pytest del servidor contra los TRES motores (memoria, SQLite y
# PostgreSQL). Levanta un PostgreSQL descartable con Docker (docker-compose.test.yml),
# corre los tests y lo apaga al terminar, pase lo que pase.
# Uso: probar_tests.sh [argumentos extra para pytest]   (ej.: -k laberinto)
set -e
source "$(dirname "$0")/_comun.sh"

PY="$RAIZ/.venv/bin/python"
[ -x "$PY" ] || { echo "Falta el venv: python -m venv .venv && .venv/bin/pip install -r servidor/requirements-dev.txt"; exit 1; }

# Ruta absoluta: el trap corre después del "cd servidor" de abajo
COMPOSE=(docker compose -p quimica_test -f "$RAIZ/docker-compose.test.yml")
trap '"${COMPOSE[@]}" down -v >/dev/null 2>&1 || true' EXIT
echo "Levantando PostgreSQL de prueba..."
"${COMPOSE[@]}" up -d --wait >/dev/null

export TEST_DATABASE_URL="postgresql://quimica_test:quimica_test@127.0.0.1:55432/quimica_test"
cd servidor
"$PY" -m pytest "$@"
