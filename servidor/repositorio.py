"""
Capa de datos del servidor: TODO el SQL vive aquí. `server.py` y `admin_api.py` no
tienen SQL propio; llaman a un `Repositorio`.

Hay dos motores con **las mismas consultas**:
  - PostgreSQL (asyncpg) para el servidor dedicado con Docker.
  - SQLite (sqlite3 de la stdlib) para el servidor local de un solo ejecutable.
El SQL se escribe portable (RETURNING, FILTER, ->> andan en los dos; SQLite >= 3.38) y
las pocas diferencias inevitables (now(), SERIAL/AUTOINCREMENT, JSONB/TEXT, TIMESTAMPTZ,
ILIKE, y el estilo de placeholder $1 vs ?) se declaran en un diccionario por motor
(`_CONFIG`), no con reemplazos de texto. Ver docs/decisiones.md.

Si no hay ninguna BD, `server.py` cae a memoria (otro módulo); acá solo vive el SQL.
"""
import asyncio
import json
import sqlite3
from datetime import datetime, timezone

# Diferencias inevitables entre motores, explícitas (no hay traducción de SQL).
_CONFIG = {
    "postgres": {"serial": "SERIAL PRIMARY KEY", "json": "JSONB", "tstz": "TIMESTAMPTZ",
                 "ahora": "now()", "ilike": "ILIKE", "pg": True},
    # `ahora` lleva paréntesis: SQLite los exige en un DEFAULT con función, y en un
    # VALUES/SET tampoco molestan. En PostgreSQL now() no los necesita.
    "sqlite":   {"serial": "INTEGER PRIMARY KEY AUTOINCREMENT", "json": "TEXT", "tstz": "TEXT",
                 "ahora": "(datetime('now'))", "ilike": "LIKE", "pg": False},
}


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
        """Lista de `cantidad` placeholders desde `desde`: '$1, $2, $3' o '?, ?, ?'."""
        return ", ".join(self.p(desde + i) for i in range(cantidad))


# --------------------------------------------------------------------- backends
# Interfaz común: execute / fetchrow (dict|None) / fetch (list[dict]) / fetchval.
class _BDPostgres:
    def __init__(self, pool):
        self.pool = pool

    async def execute(self, sql, *a):
        async with self.pool.acquire() as c:
            await c.execute(sql, *a)

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


class _BDSQLite:
    """sqlite3 es sincrónico: cada consulta corre en un hilo (to_thread) y un lock la
    serializa. SQLite serializa la escritura igual, así que no se pierde paralelismo
    real, y con un solo jugador local el costo es nulo."""

    def __init__(self, con):
        self.con = con
        self._lock = asyncio.Lock()

    async def _en_hilo(self, fn):
        async with self._lock:
            return await asyncio.to_thread(fn)

    async def execute(self, sql, *a):
        await self._en_hilo(lambda: self.con.execute(sql, a))

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


async def abrir_postgres(database_url):
    import asyncpg
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    return Repositorio(_BDPostgres(pool), "postgres"), pool


def abrir_sqlite(ruta):
    # autocommit: cada statement se confirma solo (como asyncpg). check_same_thread=False
    # porque to_thread usa un pool de hilos; el lock del backend evita las carreras.
    con = sqlite3.connect(ruta, autocommit=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return Repositorio(_BDSQLite(con), "sqlite"), con


def _a_fecha(v):
    """Normaliza una fecha a datetime UTC, venga de PostgreSQL (datetime) o de SQLite
    (texto 'YYYY-MM-DD HH:MM:SS' que da datetime('now'), siempre en UTC)."""
    if v is None or isinstance(v, datetime):
        return v
    return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


class Repositorio:
    def __init__(self, bd, motor):
        self.bd = bd
        self.d = Dialecto(motor)
        self.motor = motor

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

    # ------------------------------------------------------------- eventos
    async def registrar(self, tipo: str, detalle: dict):
        d = self.d
        await self.bd.execute(
            f"INSERT INTO eventos (tipo, detalle) VALUES ({d.p(1)}, {d.p(2)})",
            tipo, json.dumps(detalle, ensure_ascii=False))

    # ------------------------------------------------------------- usuarios
    async def buscar_usuario(self, usuario: str):
        d = self.d
        return await self.bd.fetchrow(
            f"SELECT id, usuario, nombre, color, bloqueado, motivo_bloqueo "
            f"FROM usuarios WHERE usuario = {d.p(1)}", usuario)

    async def crear_usuario(self, usuario: str, nombre: str, color: str):
        """None si el usuario ya existe (la restricción UNIQUE decide sin carrera)."""
        d = self.d
        return await self.bd.fetchrow(
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

    async def fijar_bloqueo(self, usuario: str, bloqueado: bool, motivo: str):
        d = self.d
        await self.bd.execute(
            f"UPDATE usuarios SET bloqueado = {d.p(2)}, motivo_bloqueo = {d.p(3)} "
            f"WHERE usuario = {d.p(1)}", usuario, bloqueado, motivo)

    # ------------------------------------------------------------- misiones / progreso
    async def guardar_mision(self, usuario_id, mision: str, sala: str, duracion_s: float, errores: int):
        d = self.d
        await self.bd.execute(
            f"INSERT INTO misiones_completadas (usuario_id, mision, sala, duracion_s, errores) "
            f"VALUES ({d.ps(1, 5)})", usuario_id, mision, sala, duracion_s, errores)

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
        historial = await self.bd.fetch(
            f"SELECT fecha, duracion_s, errores FROM misiones_completadas "
            f"WHERE usuario_id = {d.p(1)} ORDER BY fecha DESC LIMIT 5", usuario_id)
        for h in historial:
            h["fecha"] = _a_fecha(h["fecha"])
        return fila["n"], fila["mejor"], errores, historial

    async def cerrar(self):
        bd = self.bd
        if isinstance(bd, _BDPostgres):
            await bd.pool.close()
        elif isinstance(bd, _BDSQLite):
            await asyncio.to_thread(bd.con.close)
