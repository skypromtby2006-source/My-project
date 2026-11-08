"""
Fixtures de los tests del panel. Todo corre SIN base de datos (modo Plan B2) para que
los tests no dependan de Docker; el camino con PostgreSQL se prueba con curl contra
el servidor real (ver docs/reportes/fase-s3-1.md).
"""
import asyncio
import json
import logging
import pathlib
import sys

import httpx
import pytest
import pytest_asyncio

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import admin_api  # noqa: E402
import auth  # noqa: E402
import registro_logs  # noqa: E402
import server  # noqa: E402

ADMIN, CLAVE = "admin", "clave-de-prueba-123"


@pytest.fixture(autouse=True)
def estado_limpio():
    """Cada test empieza con el servidor vacío (los datos viven en variables del módulo)."""
    server.db = None
    for coleccion in (server.salas, server.jugadores, server.sesiones, server.usuarios_mem,
                      server.errores_mem):
        coleccion.clear()
    server.misiones_mem.clear()
    server.eventos_mem.clear()
    registro_logs.registro.buffer.clear()
    registro_logs.instalar()
    # El cliente httpx de los tests loguea cada pedido; en el servidor real no existe
    logging.getLogger("httpx").setLevel(logging.WARNING)
    yield


@pytest_asyncio.fixture
async def servidor_juego():
    """Servidor TCP del juego en un puerto libre, dentro del mismo loop que la API."""
    srv = await asyncio.start_server(server.cliente, "127.0.0.1", 0)
    puerto = srv.sockets[0].getsockname()[1]
    yield puerto
    srv.close()
    await srv.wait_closed()


@pytest.fixture
def autenticador():
    return auth.Autenticador(ADMIN, CLAVE, "secreto-de-pruebas-" + "x" * 32)


@pytest.fixture
def app(autenticador):
    return admin_api.crear_app(server, autenticador, registro_logs.registro)


@pytest_asyncio.fixture
async def api(app):
    transporte = httpx.ASGITransport(app=app, client=("10.0.0.1", 5555))
    async with httpx.AsyncClient(transport=transporte, base_url="http://panel") as c:
        yield c


@pytest_asyncio.fixture
async def token(api):
    r = await api.post("/api/login", json={"usuario": ADMIN, "contrasena": CLAVE})
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture
def h(token):
    return {"Authorization": f"Bearer {token}"}


class Bot:
    """Un jugador falso que habla el protocolo del juego por TCP."""

    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.id = None

    @classmethod
    async def nuevo(cls, puerto, usuario, nombre="Bot", color="#3FA9F5"):
        r, w = await asyncio.open_connection("127.0.0.1", puerto)
        b = cls(r, w)
        await b.env(t="registro", usuario=usuario, nombre=nombre, color=color)
        b.id = (await b.rec("perfil"))["id"]
        return b

    async def env(self, **m):
        self.writer.write((json.dumps(m) + "\n").encode())
        await self.writer.drain()

    async def rec(self, tipo, timeout=3):
        """Lee mensajes hasta uno del tipo pedido (descarta los demás)."""
        while True:
            linea = await asyncio.wait_for(self.reader.readline(), timeout)
            if not linea:
                raise ConnectionError(f"el servidor cerró la conexión esperando {tipo}")
            m = json.loads(linea)
            if m["t"] == tipo:
                return m

    async def cerrado(self, timeout=3) -> bool:
        """True si el servidor cerró la conexión (readline vacío)."""
        while True:
            linea = await asyncio.wait_for(self.reader.readline(), timeout)
            if not linea:
                return True

    def cerrar(self):
        self.writer.close()


@pytest.fixture
def bot():
    creados = []

    async def crear(puerto, usuario, **kw):
        b = await Bot.nuevo(puerto, usuario, **kw)
        creados.append(b)
        return b
    yield crear
    for b in creados:
        b.cerrar()
