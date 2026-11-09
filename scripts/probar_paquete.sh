#!/usr/bin/env bash
# Prueba de humo de un paquete de entrega: descomprime el zip en una carpeta temporal y
# arranca el servidor DESDE AHÍ (no desde el repo). Si al zip le falta un archivo, falla.
#
# Uso: probar_paquete.sh <zip> [docker|exe|todo]      (por defecto: todo)
#   docker  ServidorDedicado/: docker compose up --build con lo que trae el zip
#   exe     QuimicaServidor(.exe): el servidor local de PyInstaller
#   todo    los que el zip traiga (falla si no trae ninguno)
# Para cada uno: corre probar_cliente.py contra el juego, entra al panel con usuario y
# contraseña y pide /api/estado. Del .exe verifica además admin.txt y quimica.db.
#
# Corre en Arch y en el runner Windows de GitHub Actions (Git Bash).
set -euo pipefail
source "$(dirname "$0")/_comun.sh"

ZIP="${1:?Uso: probar_paquete.sh <zip> [docker|exe|todo]}"
QUE="${2:-todo}"
[ -f "$ZIP" ] || { echo "No existe $ZIP"; exit 1; }
ZIP="$(cd "$(dirname "$ZIP")" && pwd)/$(basename "$ZIP")"

# "python" primero: en Windows es el de setup-python; "python3" puede ser el alias de la tienda
PY="$(command -v python || command -v python3)"
export PYTHONIOENCODING=utf-8   # probar_cliente imprime ✔: en Windows la consola no es UTF-8
WINDOWS=false; case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WINDOWS=true ;; esac

TMP="$(mktemp -d)"
LIMPIEZA=()
limpiar() {
  for cmd in "${LIMPIEZA[@]}"; do eval "$cmd" >/dev/null 2>&1 || true; done
  rm -rf "$TMP"
}
trap limpiar EXIT

echo "Descomprimiendo $(basename "$ZIP") en $TMP"
"$PY" -m zipfile -e "$ZIP" "$TMP"

esperar_log() {  # esperar_log <archivo|comando> <texto> <segundos>
  local fuente="$1" texto="$2" seg="$3"
  for _ in $(seq 1 "$seg"); do
    if eval "$fuente" 2>/dev/null | grep -q "$texto"; then return 0; fi
    sleep 1
  done
  echo "ERROR: no apareció \"$texto\" en $seg s. Últimas líneas:"; eval "$fuente" 2>&1 | tail -20
  return 1
}

verificar_panel() {  # verificar_panel <puerto> <usuario> <contraseña> <modo_bd esperado> <línea del arranque>
  "$PY" - "$@" <<'EOF'
import json, sys, urllib.parse, urllib.request
puerto, usuario, clave, modo_bd, arranque = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "true", sys.argv[5]
base = f"http://127.0.0.1:{puerto}"
def pedir(ruta, datos=None, token=None):
    cab = {"Content-Type": "application/json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(base + ruta, json.dumps(datos).encode() if datos else None, cab)
    with urllib.request.urlopen(r, timeout=10) as resp:
        return resp.read().decode()
html = pedir("/")
assert "<div id=" in html, "la raíz no devolvió la página del panel (¿falta panel/dist en el paquete?)"
token = json.loads(pedir("/api/login", {"usuario": usuario, "contrasena": clave}))["token"]
estado = json.loads(pedir("/api/estado", token=token))
assert "conectados" in estado, estado
assert estado["modo_bd"] is modo_bd, f"modo_bd={estado['modo_bd']}, se esperaba {modo_bd}"
# Las líneas del arranque se generan antes de conectar el registro a la BD: tienen
# que aparecer igual en la página Logs (registro_logs las guarda y las envía al conectar)
logs = json.loads(pedir("/api/logs?buscar=" + urllib.parse.quote(arranque), token=token))
assert logs["total"] >= 1, f"el log del arranque \"{arranque}\" no está en la página Logs"
print(f"  panel OK: página servida, login, /api/estado (modo_bd={estado['modo_bd']}) "
      f"y el log del arranque \"{arranque}\" en Logs")
EOF
}

# ------------------------------------------------------------------ Docker
probar_docker() {
  local dir="$1"
  echo; echo "=== Paquete Docker: $dir"
  # El compose del paquete fija nombres de contenedor y puertos: no puede convivir
  # con el servidor del repo levantado.
  if docker ps -a --format '{{.Names}}' | grep -qE '^quimica_(db|servidor)$'; then
    echo "ERROR: existen los contenedores del servidor del repo. Detenlo con scripts/servidor_detener.sh"
    return 1
  fi
  local clave; clave="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(12))')"
  printf 'ADMIN_USER=prueba\nADMIN_PASSWORD=%s\nJWT_SECRET=%s\n' "$clave" "$("$PY" -c 'import secrets; print(secrets.token_hex(32))')" > "$dir/.env"
  # Proyecto propio: su volumen de PostgreSQL no es el del repo, y "down -v" lo borra
  local compose="docker compose -p quimica_paquete --project-directory \"$dir\" -f \"$dir/docker-compose.yml\""
  LIMPIEZA+=("$compose down -v")
  echo "  docker compose up --build (la primera vez tarda)..."
  eval "$compose up -d --build" >"$TMP/docker_build.log" 2>&1 || { tail -30 "$TMP/docker_build.log"; return 1; }
  esperar_log "$compose logs servidor" "Servidor escuchando" 90
  eval "$compose logs servidor" | grep -q "Conectado a PostgreSQL" || { echo "ERROR: el servidor no usó PostgreSQL"; return 1; }
  echo "  servidor arriba con PostgreSQL"
  "$PY" "$dir/servidor/probar_cliente.py" 127.0.0.1 7777 > "$TMP/cliente_docker.log" 2>&1 \
    || { tail -20 "$TMP/cliente_docker.log"; return 1; }
  grep -q "TODO OK" "$TMP/cliente_docker.log" && echo "  probar_cliente: TODO OK ✔"
  verificar_panel 8000 prueba "$clave" true "Conectado a PostgreSQL"
  eval "$compose down -v" >/dev/null 2>&1
  echo "  Paquete Docker OK ✔"
}

# ------------------------------------------------------------------ .exe
# Carpeta sin permiso de escritura (como "Archivos de programa"): el .exe tiene que
# explicar qué hacer y salir con código 2, no caerse con una traza de Python.
probar_sin_escritura() {
  local exe="$1" dir; dir="$(dirname "$exe")"
  local quitar
  if $WINDOWS; then
    # Se niega crear archivos/carpetas en ESA carpeta (sin herencia: _internal se sigue leyendo)
    icacls "$(cygpath -w "$dir")" //deny "${USERNAME}:(WD,AD)" >/dev/null
    quitar="icacls \"$(cygpath -w "$dir")\" //remove:d \"${USERNAME}\""
  else
    chmod a-w "$dir"
    quitar="chmod u+w \"$dir\""
  fi
  LIMPIEZA+=("$quitar")   # por si algo falla: si no, la carpeta temporal no se podría borrar
  local codigo=0
  (cd "$TMP" && QUIMICA_SIN_NAVEGADOR=1 PUERTO=17777 PUERTO_PANEL=18000 timeout 60 "$exe" </dev/null >"$TMP/exe_ro.log" 2>&1) || codigo=$?
  eval "$quitar"
  if [ "$codigo" -ne 2 ] || ! grep -q "descomprime el zip en Documentos o en el Escritorio" "$TMP/exe_ro.log"; then
    echo "ERROR: en una carpeta de solo lectura el .exe no mostró el aviso (código $codigo):"; cat "$TMP/exe_ro.log"
    return 1
  fi
  [ ! -e "$dir/admin.txt" ] || { echo "ERROR: dejó un admin.txt en la carpeta de solo lectura"; return 1; }
  echo "  carpeta de solo lectura: muestra \"descomprime el zip en Documentos o en el Escritorio\" y sale (código 2)"
}

detener_exe() {  # SIGTERM a todo proceso de ese ejecutable; si en 10 s no salió, SIGKILL
  pkill -TERM -f "$1" || return 0
  for _ in $(seq 1 20); do pgrep -f "$1" >/dev/null || return 0; sleep 0.5; done
  pkill -KILL -f "$1" || true
}

probar_exe() {
  local exe="$1" dir; dir="$(dirname "$exe")"
  if [[ "$exe" == *.exe ]] && ! $WINDOWS; then
    echo "ERROR: $(basename "$exe") es de Windows y no corre aquí. Prueba solo el paquete Docker"
    echo "  (probar_paquete.sh <zip> docker); el .exe lo prueba GitHub Actions en windows-latest."
    return 1
  fi
  echo; echo "=== Servidor local (PyInstaller): $exe"
  [ ! -e "$dir/admin.txt" ] && [ ! -e "$dir/quimica.db" ] || { echo "ERROR: el paquete trae admin.txt o quimica.db (datos de otra PC)"; return 1; }
  local juego=17777 panel=18000
  chmod +x "$exe"   # zipfile no conserva el permiso de ejecución (en Windows no hace falta)
  probar_sin_escritura "$exe"
  # Se arranca desde OTRA carpeta: los datos tienen que ir junto al ejecutable igual
  # exec: así $! es el PID del servidor y no el de un subshell que lo dejaría huérfano
  (cd "$TMP" && exec env -u DATABASE_URL -u ADMIN_USER -u ADMIN_PASSWORD -u JWT_SECRET -u SQLITE_RUTA \
      PUERTO=$juego PUERTO_PANEL=$panel QUIMICA_SIN_NAVEGADOR=1 "$exe" > "$TMP/exe.log" 2>&1) &
  # Se mata por nombre/ruta y no por $!: el bootloader de PyInstaller corre el servidor
  # en un proceso HIJO y no le reenvía el SIGTERM, así que matar al padre lo dejaría vivo.
  if $WINDOWS; then
    LIMPIEZA+=("taskkill //F //T //IM $(basename "$exe")")
  else
    LIMPIEZA+=("detener_exe \"$exe\"")
  fi
  esperar_log "cat \"$TMP/exe.log\"" "Servidor escuchando" 90
  grep -q "datos en SQLite" "$TMP/exe.log" || { echo "ERROR: el servidor no usó SQLite"; cat "$TMP/exe.log"; return 1; }
  [ -f "$dir/admin.txt" ] || { echo "ERROR: no se generó admin.txt junto al ejecutable"; return 1; }
  local usuario clave
  usuario="$(grep '^ADMIN_USER=' "$dir/admin.txt" | cut -d= -f2- | tr -d '\r')"
  clave="$(grep '^ADMIN_PASSWORD=' "$dir/admin.txt" | cut -d= -f2- | tr -d '\r')"
  grep -qF -- "$clave" "$TMP/exe.log" || { echo "ERROR: la contraseña de admin.txt no se mostró al arrancar"; return 1; }
  echo "  servidor arriba con SQLite; admin.txt generado y contraseña mostrada"
  "$PY" "$(dirname "$0")/../servidor/probar_cliente.py" 127.0.0.1 $juego > "$TMP/cliente_exe.log" 2>&1 \
    || { tail -20 "$TMP/cliente_exe.log"; echo "--- log del servidor:"; tail -20 "$TMP/exe.log"; return 1; }
  grep -q "TODO OK" "$TMP/cliente_exe.log" && echo "  probar_cliente: TODO OK ✔"
  verificar_panel $panel "$usuario" "$clave" true "datos en SQLite"
  # Lo que jugó probar_cliente quedó en quimica.db, junto al ejecutable
  "$PY" - "$dir/quimica.db" <<'EOF'
import sqlite3, sys
n = sqlite3.connect(sys.argv[1]).execute("SELECT count(*) FROM usuarios").fetchone()[0]
assert n >= 3, f"quimica.db tiene {n} usuarios; probar_cliente registra 3"
print(f"  quimica.db junto al ejecutable: {n} usuarios guardados")
EOF
  echo "  Servidor local OK ✔"
}

# ------------------------------------------------------------------ qué probar
DOCKER_DIR="$(find "$TMP" -maxdepth 3 -type d -name ServidorDedicado | head -1)"
EXE="$(find "$TMP" -maxdepth 4 -type f \( -name QuimicaServidor.exe -o -name QuimicaServidor \) | head -1)"
probados=0
if [ "$QUE" = docker ] || { [ "$QUE" = todo ] && [ -n "$DOCKER_DIR" ]; }; then
  [ -n "$DOCKER_DIR" ] || { echo "ERROR: el zip no trae ServidorDedicado/"; exit 1; }
  probar_docker "$DOCKER_DIR"; probados=$((probados + 1))
fi
if [ "$QUE" = todo ] && [[ "$EXE" == *.exe ]] && ! $WINDOWS; then
  echo; echo "NOTA: el zip trae $(basename "$EXE"), que solo corre en Windows: aquí NO se prueba"
  echo "      (lo prueba GitHub Actions en windows-latest antes de subirlo)."
  EXE=""
fi
if [ "$QUE" = exe ] || { [ "$QUE" = todo ] && [ -n "$EXE" ]; }; then
  [ -n "$EXE" ] || { echo "ERROR: el zip no trae QuimicaServidor(.exe)"; exit 1; }
  probar_exe "$EXE"; probados=$((probados + 1))
fi
[ $probados -gt 0 ] || { echo "ERROR: el zip no trae ningún servidor (ni ServidorDedicado/ ni QuimicaServidor)"; exit 1; }
echo; echo "PAQUETE OK ✔ ($probados servidor(es) probados desde el zip)"
