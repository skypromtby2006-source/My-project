"""
Fixtures de los tests del servidor y del panel.

Los tests que tocan datos (perfiles, progreso, panel, laberinto) se corren contra
**cada motor**: `memoria` (sin BD), `sqlite` (servidor local) y `postgres` (servidor
dedicado). Así "mismas consultas en los dos motores" es algo probado, no una promesa.
Un test entra en la batería con solo pedir la fixture `motor` (directa o a través de
`servidor_juego` / `app`).

PostgreSQL se toma de TEST_DATABASE_URL —una BD descartable, porque cada test la
VACÍA— y no de DATABASE_URL, para no borrar nunca los datos reales por error.
`scripts/probar_tests.sh` la levanta con Docker y corre todo. Si falta, los tests de
postgres FALLAN (no se saltean): elegir motores es explícito, con --motores.
"""
import asyncio
import collections
import json
import logging
import os
import pathlib
import sys

import httpx
import pytest
import pytest_asyncio

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import admin_api  # noqa: E402
import auth  # noqa: E402
import registro_logs  # noqa: E402
import repositorio  # noqa: E402
import server  # noqa: E402

ADMIN, CLAVE = "admin", "clave-de-prueba-123"
MOTORES = ("memoria", "sqlite", "postgres")


# ----------------------------------------------------------------- motores
def pytest_addoption(parser):
    parser.addoption("--motores", default=",".join(MOTORES),
                     help="motores de BD a probar, separados por coma (por defecto: todos)")


def pytest_generate_tests(metafunc):
    """Parametriza con `motor` a todo test que lo use. Un módulo puede limitar los
    motores que tienen sentido para él con su propia lista MOTORES (p. ej. los tests
    del SQL no aplican a memoria): así no hace falta saltear nada."""
    if "motor" not in metafunc.fixturenames:
        return
    elegidos = [m.strip() for m in metafunc.config.getoption("--motores").split(",") if m.strip()]
    desconocidos = set(elegidos) - set(MOTORES)
    if desconocidos:
        raise pytest.UsageError(f"--motores: desconocido(s) {sorted(desconocidos)}; válidos: {MOTORES}")
    validos = getattr(metafunc.module, "MOTORES", MOTORES)
    metafunc.parametrize("motor", [m for m in elegidos if m in validos], indirect=True)


async def abrir_repo(motor: str, tmp_path) -> repositorio.Repositorio:
    if motor == "sqlite":
        # Un archivo y no ":memory:": así se prueba también WAL y busy_timeout
        repo = repositorio.abrir_sqlite(tmp_path / "quimica.db")
    else:
        url = os.getenv("TEST_DATABASE_URL")
        if not url:
            pytest.fail("Falta TEST_DATABASE_URL para los tests de postgres. Corre "
                        "scripts/probar_tests.sh (levanta PostgreSQL con Docker) o elige "
                        "otros motores con --motores=memoria,sqlite", pytrace=False)
        repo = await repositorio.abrir_postgres(url)
    await repo.crear_esquema()
    await repo.vaciar_todo()
    return repo


@pytest_asyncio.fixture
async def motor(request, tmp_path):
    """Pone `server.db` con el motor del test (None = memoria) y lo cierra al final."""
    if request.param == "memoria":
        yield "memoria"
        return
    repo = await abrir_repo(request.param, tmp_path)
    server.db = repo
    await registro_logs.registro.conectar_bd(repo)
    yield request.param
    server.db = None
    registro_logs.registro.db = None
    registro_logs.registro.pendientes.clear()
    await repo.cerrar()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    reporte = yield
    params = getattr(getattr(item, "callspec", None), "params", {})
    reporte.user_properties.append(("motor", params.get("motor", "sin motor")))
    return reporte


def pytest_terminal_summary(terminalreporter):
    """Resumen por motor: "N passed, 0 skipped" de cada uno, para ver de un vistazo que
    ningún motor quedó sin probar."""
    cuentas: dict[str, collections.Counter] = {}
    for estado in ("passed", "failed", "skipped", "error", "xfailed", "xpassed"):
        for rep in terminalreporter.stats.get(estado, []):
            props = dict(getattr(rep, "user_properties", []))
            if "motor" not in props:
                continue
            # Un test cuenta una vez: su fase "call", o la de setup si falló/se salteó ahí
            if rep.when == "call" or (rep.when == "setup" and estado in ("skipped", "error")) \
                    or (rep.when == "teardown" and estado == "error"):
                cuentas.setdefault(props["motor"], collections.Counter())[estado] += 1
    if not cuentas:
        return
    terminalreporter.section("resultado por motor")
    for m in [*MOTORES, "sin motor"]:
        if m in cuentas:
            c = cuentas[m]
            extra = "".join(f", {c[k]} {k}" for k in ("failed", "error", "xfailed", "xpassed") if c[k])
            terminalreporter.write_line(f"{m:>10}: {c['passed']} passed, {c['skipped']} skipped{extra}")


# ----------------------------------------------------------------- lectura de datos
# Para que los tests revisen lo guardado igual en los tres motores.
async def eventos(tipo: str | None = None) -> list[dict]:
    if server.db is None:
        return [e for e in server.eventos_mem if tipo is None or e["tipo"] == tipo]
    return await server.db.eventos(tipo)


async def misiones() -> list[dict]:
    if server.db is None:
        return list(server.misiones_mem)
    return await server.db.misiones()


async def esperar(condicion, timeout: float = 3.0):
    """Espera a que `condicion()` (async) sea verdadera. Hace falta con BD: el servidor
    responde al cliente ANTES de terminar de guardar (registrar va después de difundir),
    así que el test puede consultar un instante antes de que llegue la fila."""
    limite = asyncio.get_running_loop().time() + timeout
    while not await condicion():
        if asyncio.get_running_loop().time() > limite:
            raise AssertionError("la condición no se cumplió a tiempo")
        await asyncio.sleep(0.01)


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
async def servidor_juego(motor):
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
def app(autenticador, motor):
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

    async def rec(self, tipo, timeout=3, cuando=None):
        """Lee mensajes hasta uno del tipo pedido (y que cumpla `cuando`, si se da);
        descarta los demás."""
        while True:
            linea = await asyncio.wait_for(self.reader.readline(), timeout)
            if not linea:
                raise ConnectionError(f"el servidor cerró la conexión esperando {tipo}")
            m = json.loads(linea)
            if m["t"] == tipo and (cuando is None or cuando(m)):
                return m

    async def listo(self, anfitrion: "Bot"):
        """Marca Listo y espera a que el anfitrión lo vea. Sin esa espera, el "iniciar"
        del anfitrión (otra conexión) puede procesarse antes que este "listo" cuando el
        servidor cede el loop para escribir en la BD; un jugador real espera la UI."""
        await self.env(t="listo", valor=True)
        await anfitrion.rec("sala", cuando=lambda m: all(
            x["listo"] for x in m["sala"]["jugadores"] if x["id"] != m["sala"]["host"]))

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
