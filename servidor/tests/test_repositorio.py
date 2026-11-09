"""
Tests de la capa de datos (`repositorio.py`) contra los DOS motores: SQLite siempre, y
PostgreSQL cuando hay una BD de prueba (variable DATABASE_URL, p. ej. la de Docker).
Prueban que las MISMAS consultas dan el mismo resultado en ambos.
"""
import os
import pathlib
import sys

import pytest_asyncio

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import repositorio  # noqa: E402

MOTORES = ["sqlite"] + (["postgres"] if os.getenv("DATABASE_URL") else [])


@pytest_asyncio.fixture(params=MOTORES)
async def repo(request):
    if request.param == "sqlite":
        r, _ = repositorio.abrir_sqlite(":memory:")
    else:
        r, _ = await repositorio.abrir_postgres(os.getenv("DATABASE_URL"))
    await r.crear_esquema()
    if request.param == "postgres":
        for t in ("misiones_completadas", "eventos", "usuarios", "logs", "auditoria_admin"):
            await r.bd.execute(f"TRUNCATE {t} RESTART IDENTITY CASCADE")
    yield r
    await r.cerrar()


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
