"""
Capa de datos del servidor: TODO el SQL vive aquí. `server.py`, `admin_api.py`,
`registro_logs.py` y `estadisticas.py` no tienen SQL propio; llaman a un `Repositorio`.

Hay dos motores con **las mismas consultas**:
  - PostgreSQL (asyncpg) para el servidor dedicado con Docker.
  - SQLite (sqlite3 de la stdlib) para el servidor local de un solo ejecutable.
El SQL se escribe portable (RETURNING, FILTER, ->>, NULLS LAST andan en los dos; SQLite
>= 3.38) y las pocas diferencias inevitables (timestamp actual, SERIAL/AUTOINCREMENT,
JSONB/TEXT, TIMESTAMPTZ, ILIKE, el estilo de placeholder $1 vs ?1 y cómo se pasa una
fecha como parámetro) se declaran en un diccionario por motor (`_CONFIG`), no con
reemplazos de texto. Ver docs/decisiones.md.

El repositorio devuelve los datos ya normalizados (fechas como datetime UTC, booleanos
como bool, `detalle` como dict) para que el resto del servidor no sepa qué motor hay.

Si no hay ninguna BD, `server.py` cae a memoria (sus propias listas); acá solo vive el SQL.
"""
import asyncio
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

# Diferencias inevitables entre motores, explícitas (no hay traducción de SQL).
_CONFIG = {
    "postgres": {"serial": "SERIAL PRIMARY KEY", "json": "JSONB", "tstz": "TIMESTAMPTZ",
                 "ahora": "now()", "ilike": "ILIKE", "pg": True},
    # `ahora` lleva paréntesis: SQLite los exige en un DEFAULT con función. Se guarda con
    # milisegundos (%f) y no con datetime('now'), que solo tiene segundos: con segundos,
    # dos filas del mismo instante empatan al ordenar por fecha.
    "sqlite":   {"serial": "INTEGER PRIMARY KEY AUTOINCREMENT", "json": "TEXT", "tstz": "TEXT",
                 "ahora": "(strftime('%Y-%m-%d %H:%M:%f', 'now'))", "ilike": "LIKE", "pg": False},
}

# Columnas de fecha y booleanas que se normalizan al leer (SQLite las da como texto y 0/1)
_FECHAS = ("fecha", "creado", "ultimo_login")
_BOOLEANOS = ("bloqueado",)
TABLAS = ("misiones_completadas", "eventos", "usuarios", "logs", "auditoria_admin")


class Dialecto:
    def __init__(self, motor):
        if motor not in _CONFIG:
            raise ValueError(f"motor desconocido: {motor}")
        self.motor = motor
        c = _CONFIG[motor]
        self.serial, self.json, self.tstz = c["serial"], c["json"], c["tstz"]
        self.ahora, self.ilike, self._pg = c["ahora"], c["ilike"], c["pg"]

    def p(self, n):
        """Placeholder del parámetro n (1-based). Se usa el estilo NUMERADO en los dos
        motores ($n en PostgreSQL, ?n en SQLite) para que ligar por número —y no por
        orden en el texto— y reusar el mismo parámetro varias veces funcione igual."""
        return f"${n}" if self._pg else f"?{n}"

    def ps(self, desde, cantidad):
        """Lista de `cantidad` placeholders desde `desde`: '$1, $2, $3' o '?1, ?2, ?3'."""
        return ", ".join(self.p(desde + i) for i in range(cantidad))

    def fecha(self, dt: datetime):
        """Una fecha como parámetro: asyncpg recibe el datetime; en SQLite se guarda como
        texto UTC con el MISMO formato que `ahora`, para que compare y ordene bien."""
        if self._pg:
            return dt
        dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


# --------------------------------------------------------------------- backends
# Interfaz común: execute / executemany / fetchrow (dict|None) / fetch (list[dict]) /
# fetch_grande (list[dict], para resultados enormes) / fetchval.
LOTE = 5000


class _BDPostgres:
    def __init__(self, pool):
        self.pool = pool

    async def execute(self, sql, *a):
        async with self.pool.acquire() as c:
            await c.execute(sql, *a)

    async def executemany(self, sql, filas):
        async with self.pool.acquire() as c:
            await c.executemany(sql, filas)

    async def fetchrow(self, sql, *a):
        async with self.pool.acquire() as c:
            f = await c.fetchrow(sql, *a)
        return dict(f) if f else None

    async def fetch(self, sql, *a):
        async with self.pool.acquire() as c:
            return [dict(x) for x in await c.fetch(sql, *a)]

    async def fetchval(self, sql, *a):
        async with self.pool.acquire() as c:
            return await c.fetchval(sql, *a)

    async def fetch_grande(self, sql, *a):
        """Como fetch, pero por lotes con un cursor. asyncpg decodifica las filas DENTRO
        del event loop: 500 000 filas de una vez lo frenan ~0,4 s (lo midió
        test_concurrencia.py). De a LOTE filas, cada tramo es corto y entre tramo y
        tramo el loop atiende a los jugadores."""
        filas = []
        async with self.pool.acquire() as c:
            async with c.transaction():   # los cursores de PostgreSQL viven en una transacción
                cursor = await c.cursor(sql, *a)
                while bloque := await cursor.fetch(LOTE):
                    filas.extend(dict(x) for x in bloque)
                    await asyncio.sleep(0)
        return filas

    async def cerrar(self):
        await self.pool.close()


class _BDSQLite:
    """sqlite3 es sincrónico: si se llamara directo desde una corrutina, una consulta
    pesada (las estadísticas del panel) congelaría el event loop y con él a TODOS los
    jugadores. Por eso cada consulta corre en un hilo (`asyncio.to_thread`) sobre una
    única conexión, y un `threading.Lock` —tomado DENTRO del hilo— la serializa: el
    loop nunca espera el lock, solo espera el resultado del hilo.

    Una sola conexión y no un pool: SQLite permite un solo escritor a la vez, así que
    varias conexiones solo cambiarían el lock nuestro por esperas de `busy_timeout`."""

    def __init__(self, con):
        self.con = con
        self._lock = threading.Lock()

    async def _en_hilo(self, fn):
        def con_lock():
            with self._lock:
                return fn()
        return await asyncio.to_thread(con_lock)

    async def execute(self, sql, *a):
        await self._en_hilo(lambda: self.con.execute(sql, a))

    async def executemany(self, sql, filas):
        filas = list(filas)

        def go():
            # Una transacción para todo el lote: en autocommit, cada fila sería un fsync
            with self.con:
                self.con.executemany(sql, filas)
        await self._en_hilo(go)

    async def fetchrow(self, sql, *a):
        def go():
            fila = self.con.execute(sql, a).fetchone()
            return dict(fila) if fila is not None else None
        return await self._en_hilo(go)

    async def fetch(self, sql, *a):
        def go():
            return [dict(x) for x in self.con.execute(sql, a).fetchall()]
        return await self._en_hilo(go)

    async def fetchval(self, sql, *a):
        def go():
            fila = self.con.execute(sql, a).fetchone()
            return fila[0] if fila is not None else None
        return await self._en_hilo(go)

    async def fetch_grande(self, sql, *a):
        # Ya corre entero en un hilo: no hace falta partirlo
        return await self.fetch(sql, *a)

    async def cerrar(self):
        await self._en_hilo(self.con.close)


async def abrir_postgres(database_url):
    import asyncpg
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    return Repositorio(_BDPostgres(pool), "postgres")


def abrir_sqlite(ruta):
    # autocommit: cada statement se confirma solo (como asyncpg). check_same_thread=False
    # porque to_thread usa un pool de hilos; el threading.Lock del backend evita carreras.
    con = sqlite3.connect(str(ruta), autocommit=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    # WAL: los lectores no bloquean al escritor (y viceversa) si otra herramienta abre
    # el archivo a la vez, p. ej. un visor de SQLite mientras corre el servidor.
    con.execute("PRAGMA journal_mode=WAL")
    # Si el archivo está tomado por otro proceso, esperar hasta 5 s en vez de fallar
    # al instante con "database is locked".
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA foreign_keys=ON")
    return Repositorio(_BDSQLite(con), "sqlite")


def _a_fecha(v):
    """Normaliza una fecha a datetime UTC, venga de PostgreSQL (datetime) o de SQLite
    (texto 'YYYY-MM-DD HH:MM:SS[.mmm]', siempre en UTC)."""
    if v is None or isinstance(v, datetime):
        return v
    dt = datetime.fromisoformat(str(v))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _normalizar(fila: dict | None) -> dict | None:
    if fila is None:
        return None
    for k in _FECHAS:
        if k in fila:
            fila[k] = _a_fecha(fila[k])
    for k in _BOOLEANOS:
        if k in fila and fila[k] is not None:
            fila[k] = bool(fila[k])
    if isinstance(fila.get("detalle"), str):
        fila["detalle"] = json.loads(fila["detalle"])
    return fila


class Repositorio:
    def __init__(self, bd, motor):
        self.bd = bd
        self.d = Dialecto(motor)
        self.motor = motor

    async def _filas(self, sql, *a):
        return [_normalizar(f) for f in await self.bd.fetch(sql, *a)]

    async def _fila(self, sql, *a):
        return _normalizar(await self.bd.fetchrow(sql, *a))

    # ------------------------------------------------------------- esquema
    async def crear_esquema(self):
        d = self.d
        sentencias = [
            f"""CREATE TABLE IF NOT EXISTS eventos (
                    id {d.serial},
                    tipo TEXT NOT NULL,
                    detalle {d.json},
                    fecha {d.tstz} DEFAULT {d.ahora})""",
            f"""CREATE TABLE IF NOT EXISTS usuarios (
                    id {d.serial},
                    usuario TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    color TEXT NOT NULL,
                    creado {d.tstz} DEFAULT {d.ahora},
                    ultimo_login {d.tstz},
                    bloqueado BOOLEAN DEFAULT false,
                    motivo_bloqueo TEXT)""",
            f"""CREATE TABLE IF NOT EXISTS misiones_completadas (
                    id {d.serial},
                    usuario_id INT REFERENCES usuarios(id),
                    mision TEXT NOT NULL,
                    sala TEXT NOT NULL,
                    duracion_s REAL NOT NULL,
                    errores INT NOT NULL,
                    fecha {d.tstz} DEFAULT {d.ahora})""",
            "CREATE INDEX IF NOT EXISTS misiones_por_usuario ON misiones_completadas (usuario_id)",
            f"""CREATE TABLE IF NOT EXISTS logs (
                    id {d.serial},
                    nivel TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    fecha {d.tstz} DEFAULT {d.ahora})""",
            "CREATE INDEX IF NOT EXISTS logs_por_fecha ON logs (fecha)",
            f"""CREATE TABLE IF NOT EXISTS auditoria_admin (
                    id {d.serial},
                    admin TEXT NOT NULL,
                    accion TEXT NOT NULL,
                    objetivo TEXT,
                    detalle {d.json},
                    ip TEXT,
                    fecha {d.tstz} DEFAULT {d.ahora})""",
            "CREATE INDEX IF NOT EXISTS eventos_por_tipo ON eventos (tipo)",
        ]
        for s in sentencias:
            await self.bd.execute(s)
        # Migración solo para PostgreSQL ya instalado antes del Sprint 3: agrega las
        # columnas del panel si la tabla usuarios es vieja. SQLite ya las crea arriba.
        if self.d._pg:
            await self.bd.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN DEFAULT false")
            await self.bd.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS motivo_bloqueo TEXT")

    async def vaciar_todo(self):
        """Borra todas las filas (solo para tests: cada test empieza con la BD vacía)."""
        if self.d._pg:
            await self.bd.execute(f"TRUNCATE {', '.join(TABLAS)} RESTART IDENTITY CASCADE")
        else:
            for t in TABLAS:
                await self.bd.execute(f"DELETE FROM {t}")

    # ------------------------------------------------------------- eventos
    async def registrar(self, tipo: str, detalle: dict):
        d = self.d
        await self.bd.execute(
            f"INSERT INTO eventos (tipo, detalle) VALUES ({d.p(1)}, {d.p(2)})",
            tipo, json.dumps(detalle, ensure_ascii=False))

    async def eventos(self, tipo: str | None = None) -> list[dict]:
        """Eventos en orden de llegada, opcionalmente de un solo tipo."""
        d = self.d
        if tipo is None:
            return await self._filas("SELECT tipo, detalle, fecha FROM eventos ORDER BY id")
        return await self._filas(
            f"SELECT tipo, detalle, fecha FROM eventos WHERE tipo = {d.p(1)} ORDER BY id", tipo)

    # ------------------------------------------------------------- usuarios
    async def buscar_usuario(self, usuario: str):
        d = self.d
        return await self._fila(
            f"SELECT id, usuario, nombre, color, bloqueado, motivo_bloqueo "
            f"FROM usuarios WHERE usuario = {d.p(1)}", usuario)

    async def crear_usuario(self, usuario: str, nombre: str, color: str):
        """None si el usuario ya existe. ON CONFLICT en vez de consultar antes: si dos
        clientes registran el mismo usuario a la vez, la restricción UNIQUE decide."""
        d = self.d
        return await self._fila(
            f"INSERT INTO usuarios (usuario, nombre, color, ultimo_login) "
            f"VALUES ({d.ps(1, 3)}, {d.ahora}) "
            f"ON CONFLICT (usuario) DO NOTHING RETURNING id, usuario, nombre, color",
            usuario, nombre, color)

    async def marcar_login(self, usuario: str):
        d = self.d
        await self.bd.execute(
            f"UPDATE usuarios SET ultimo_login = {d.ahora} WHERE usuario = {d.p(1)}", usuario)

    async def actualizar_usuario(self, usuario: str, nombre: str, color: str):
        d = self.d
        await self.bd.execute(
            f"UPDATE usuarios SET nombre = {d.p(2)}, color = {d.p(3)} WHERE usuario = {d.p(1)}",
            usuario, nombre, color)

    async def fijar_bloqueo(self, usuario: str, bloqueado: bool, motivo: str | None) -> bool:
        """False si el usuario no existe. RETURNING en vez de leer "UPDATE 0": el texto
        de estado es propio de asyncpg y SQLite no lo tiene."""
        d = self.d
        fila = await self.bd.fetchrow(
            f"UPDATE usuarios SET bloqueado = {d.p(2)}, motivo_bloqueo = {d.p(3)} "
            f"WHERE usuario = {d.p(1)} RETURNING id", usuario, bloqueado, motivo)
        return fila is not None

    async def listar_usuarios(self, buscar: str, pagina: int, por_pagina: int, mision_base: str):
        """(total, filas) de la tabla de usuarios del panel, con su progreso. Los errores
        salen de eventos (reaccion_fallida), igual que en el perfil del juego: así cuentan
        también los de misiones reiniciadas o abandonadas."""
        d = self.d
        patron = f"%{buscar}%"
        total = await self.bd.fetchval(
            f"SELECT count(*) FROM usuarios WHERE usuario {d.ilike} {d.p(1)} OR nombre {d.ilike} {d.p(1)}",
            patron)
        filas = await self._filas(f"""
            SELECT u.usuario, u.nombre, u.color, u.creado, u.ultimo_login, u.bloqueado,
                   count(m.id) AS completadas,
                   min(m.duracion_s) FILTER (WHERE m.mision = {d.p(2)}) AS mejor_tiempo_s,
                   coalesce(e.n, 0) AS errores
            FROM usuarios u
            LEFT JOIN misiones_completadas m ON m.usuario_id = u.id
            LEFT JOIN (SELECT detalle->>'usuario' AS usuario, count(*) AS n FROM eventos
                       WHERE tipo = 'reaccion_fallida' GROUP BY 1) e ON e.usuario = u.usuario
            WHERE u.usuario {d.ilike} {d.p(1)} OR u.nombre {d.ilike} {d.p(1)}
            GROUP BY u.id, e.n
            ORDER BY u.ultimo_login DESC NULLS LAST, u.id DESC
            LIMIT {int(por_pagina)} OFFSET {(int(pagina) - 1) * int(por_pagina)}""",
            patron, mision_base)
        return total, filas

    async def detalle_usuario(self, usuario: str):
        """(perfil, historial, fallos) del detalle de un usuario en el panel, o None."""
        d = self.d
        perfil = await self._fila(
            f"SELECT id, usuario, nombre, color, creado, ultimo_login, bloqueado, motivo_bloqueo "
            f"FROM usuarios WHERE usuario = {d.p(1)}", usuario)
        if perfil is None:
            return None
        uid = perfil.pop("id")
        historial = await self._filas(
            f"SELECT fecha, mision, sala, duracion_s, errores FROM misiones_completadas "
            f"WHERE usuario_id = {d.p(1)} ORDER BY fecha DESC, id DESC LIMIT 200", uid)
        eventos = await self._filas(
            f"SELECT detalle, fecha FROM eventos WHERE tipo = 'reaccion_fallida' "
            f"AND detalle->>'usuario' = {d.p(1)} ORDER BY fecha DESC, id DESC", usuario)
        fallos = [{**e["detalle"], "fecha": e["fecha"]} for e in eventos]
        return perfil, historial, fallos

    # ------------------------------------------------------------- misiones / progreso
    async def guardar_mision(self, usuario_id, mision: str, sala: str, duracion_s: float, errores: int):
        d = self.d
        await self.bd.execute(
            f"INSERT INTO misiones_completadas (usuario_id, mision, sala, duracion_s, errores) "
            f"VALUES ({d.ps(1, 5)})", usuario_id, mision, sala, duracion_s, errores)

    async def misiones(self, usuario: str | None = None) -> list[dict]:
        """Misiones completadas (con el nombre de usuario), en orden de llegada."""
        d = self.d
        sql = ("SELECT u.usuario, m.mision, m.sala, m.duracion_s, m.errores, m.fecha "
               "FROM misiones_completadas m JOIN usuarios u ON u.id = m.usuario_id")
        if usuario is None:
            return await self._filas(sql + " ORDER BY m.id")
        return await self._filas(sql + f" WHERE u.usuario = {d.p(1)} ORDER BY m.id", usuario)

    async def progreso(self, usuario: str, usuario_id, mision_base: str):
        """Devuelve (completadas, mejor_tiempo_s|None, errores_totales, historial[5]).
        Los errores salen de los eventos reaccion_fallida (también cuentan los de
        misiones abandonadas), igual que el análisis con pandas del panel."""
        d = self.d
        fila = await self.bd.fetchrow(
            f"SELECT count(*) AS n, min(duracion_s) FILTER (WHERE mision = {d.p(2)}) AS mejor "
            f"FROM misiones_completadas WHERE usuario_id = {d.p(1)}", usuario_id, mision_base)
        errores = await self.bd.fetchval(
            f"SELECT count(*) FROM eventos WHERE tipo = 'reaccion_fallida' "
            f"AND detalle->>'usuario' = {d.p(1)}", usuario)
        historial = await self._filas(
            f"SELECT fecha, duracion_s, errores FROM misiones_completadas "
            f"WHERE usuario_id = {d.p(1)} ORDER BY fecha DESC, id DESC LIMIT 5", usuario_id)
        return fila["n"], fila["mejor"], errores, historial

    # ------------------------------------------------------------- estadísticas
    async def datos_estadisticas(self):
        """(errores, misiones) para el análisis con pandas. `detalle` va SIN decodificar
        (texto JSON): con muchos eventos el json.loads es caro, y estadisticas.py lo hace
        en un hilo junto con pandas para no frenar el event loop."""
        errores = await self.bd.fetch_grande(
            # Solo usuarios que existen: hay eventos de pruebas viejas con un usuario que
            # ya no está, y su enlace en el panel llevaría a una página vacía
            "SELECT detalle, fecha FROM eventos WHERE tipo = 'reaccion_fallida' "
            "AND detalle->>'usuario' IN (SELECT usuario FROM usuarios)")
        misiones = await self.bd.fetch_grande(
            "SELECT u.usuario, m.mision, m.duracion_s, m.errores, m.fecha "
            "FROM misiones_completadas m JOIN usuarios u ON u.id = m.usuario_id")
        return errores, misiones

    # ------------------------------------------------------------- auditoría del panel
    async def anotar_auditoria(self, admin: str, accion: str, objetivo: str, detalle: dict, ip: str):
        d = self.d
        await self.bd.execute(
            f"INSERT INTO auditoria_admin (admin, accion, objetivo, detalle, ip) VALUES ({d.ps(1, 5)})",
            admin, accion, objetivo, json.dumps(detalle, ensure_ascii=False), ip)

    async def listar_auditoria(self, pagina: int, por_pagina: int, accion: str = ""):
        d = self.d
        donde, args = (f"WHERE accion = {d.p(1)}", [accion]) if accion else ("", [])
        total = await self.bd.fetchval(f"SELECT count(*) FROM auditoria_admin {donde}", *args)
        filas = await self._filas(
            f"SELECT id, admin, accion, objetivo, detalle, ip, fecha FROM auditoria_admin {donde} "
            f"ORDER BY id DESC LIMIT {int(por_pagina)} OFFSET {(int(pagina) - 1) * int(por_pagina)}", *args)
        for f in filas:
            f["detalle"] = f["detalle"] or {}
        return total, filas

    # ------------------------------------------------------------- logs del servidor
    async def purgar_logs(self, dias: int):
        """Borra los logs de más de `dias` días. El corte se calcula en Python y va como
        parámetro: así no hace falta la aritmética de fechas de cada motor."""
        d = self.d
        corte = datetime.now(timezone.utc) - timedelta(days=dias)
        await self.bd.execute(f"DELETE FROM logs WHERE fecha < {d.p(1)}", d.fecha(corte))

    async def guardar_logs(self, lote: list[tuple[str, str, datetime]]):
        d = self.d
        await self.bd.executemany(
            f"INSERT INTO logs (nivel, mensaje, fecha) VALUES ({d.ps(1, 3)})",
            [(nivel, mensaje, d.fecha(fecha)) for nivel, mensaje, fecha in lote])

    async def consultar_logs(self, nivel: str, buscar: str, pagina: int, por_pagina: int):
        d = self.d
        condiciones, args = [], []
        if nivel:
            args.append(nivel)
            condiciones.append(f"nivel = {d.p(len(args))}")
        if buscar:
            args.append(f"%{buscar}%")
            condiciones.append(f"mensaje {d.ilike} {d.p(len(args))}")
        donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        total = await self.bd.fetchval(f"SELECT count(*) FROM logs {donde}", *args)
        filas = await self._filas(
            f"SELECT id, nivel, mensaje, fecha FROM logs {donde} ORDER BY id DESC "
            f"LIMIT {int(por_pagina)} OFFSET {(int(pagina) - 1) * int(por_pagina)}", *args)
        return total, filas

    async def cerrar(self):
        await self.bd.cerrar()
