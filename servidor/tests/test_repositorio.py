"""
Tests de la capa de datos (`repositorio.py`) contra los DOS motores con SQL: SQLite y
PostgreSQL (ver conftest.py: TEST_DATABASE_URL). Prueban que las MISMAS consultas dan
el mismo resultado en ambos. El modo memoria no tiene SQL, así que no aplica aquí.
"""
import pytest_asyncio

import server

MOTORES = ("sqlite", "postgres")


@pytest_asyncio.fixture
async def repo(motor):
    return server.db


async def test_crear_y_buscar_usuario(repo):
    u = await repo.crear_usuario("ana", "Ana", "#FFFFFF")
    assert u["usuario"] == "ana" and u["id"] is not None
    # Segundo registro con el mismo usuario: la restricción UNIQUE lo rechaza
    assert await repo.crear_usuario("ana", "Otra", "#000000") is None
    f = await repo.buscar_usuario("ana")
    assert f["nombre"] == "Ana" and not f["bloqueado"]
    assert await repo.buscar_usuario("nadie") is None


async def test_progreso_cuenta_misiones_y_errores(repo):
    u = await repo.crear_usuario("ben", "Ben", "#FFFFFF")
    uid = u["id"]
    await repo.guardar_mision(uid, "agua", "S1", 12.5, 1)
    await repo.guardar_mision(uid, "agua", "S1", 9.0, 0)
    await repo.guardar_mision(uid, "laberinto", "L1", 30.0, 2)
    await repo.registrar("reaccion_fallida", {"usuario": "ben"})
    await repo.registrar("reaccion_fallida", {"usuario": "ben"})
    await repo.registrar("reaccion_fallida", {"usuario": "otro"})  # no cuenta

    comp, mejor, err, hist = await repo.progreso("ben", uid, "agua")
    assert comp == 3                       # todas las misiones del usuario
    assert abs(mejor - 9.0) < 1e-6         # mejor tiempo de la misión base (agua)
    assert err == 2                        # solo los reaccion_fallida de 'ben'
    assert len(hist) == 3 and hist[0]["fecha"] is not None


async def test_bloqueo_login_y_actualizar(repo):
    await repo.crear_usuario("cid", "Cid", "#FFFFFF")
    await repo.marcar_login("cid")
    await repo.actualizar_usuario("cid", "Cid II", "#111111")
    await repo.fijar_bloqueo("cid", True, "prueba")
    f = await repo.buscar_usuario("cid")
    assert f["nombre"] == "Cid II" and f["color"] == "#111111"
    assert f["bloqueado"] and f["motivo_bloqueo"] == "prueba"
