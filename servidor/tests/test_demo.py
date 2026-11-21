"""Datos de demo de la presentación (servidor/demo.py): sembrar dos veces no duplica,
el panel docente se ve con datos y limpiar borra solo lo de la demo."""
import sys

import pytest

import demo
import server
import servidor_local
from test_docentes_api import entrar

MOTORES = ("sqlite", "postgres")


async def contar(db) -> dict:
    """Filas de cada tabla que toca la demo (por motor, sin SQL fuera del repositorio)."""
    doc = await db.buscar_docente(demo.DOCENTE)
    clases = await db.clases_de_docente(doc["id"]) if doc else []
    retos = await db.retos_de_docente(doc["id"]) if doc else []
    return {
        "docentes": len(await db.listar_docentes()),
        "clases": len(clases),
        "inscritos": sum(c["inscritos"] for c in clases),
        "retos": len(retos),
        "intentos": len(await db.intentos()),
        "misiones": len(await db.misiones()),
        "usuarios": sum([await db.buscar_usuario(u) is not None for u, _, _ in demo.ESTUDIANTES]),
    }


async def test_sembrar_dos_veces_no_duplica_y_reusa_la_contrasena(motor, tmp_path):
    db = server.db
    r1 = await demo.sembrar(db, tmp_path)
    antes = await contar(db)
    assert antes == {"docentes": 1, "clases": 1, "inscritos": 4, "retos": 1,
                     "intentos": 6, "misiones": 4, "usuarios": 4}
    r2 = await demo.sembrar(db, tmp_path)
    assert await contar(db) == antes
    assert r2["contrasena"] == r1["contrasena"] and r2["codigo"] == r1["codigo"]
    assert len(r1["codigo"]) == 8
    cred = demo.leer_credenciales(tmp_path / demo.ARCHIVO_CREDENCIALES)
    assert cred["DOCENTE_PASSWORD"] == r1["contrasena"] and cred["CODIGO_CLASE"] == r1["codigo"]
    reto = await db.reto(r1["reto_id"])
    assert reto["semilla"] == demo.SEMILLA and reto["nivel"] == demo.NIVEL and reto["abierto"]


async def test_el_panel_docente_no_se_ve_vacio(motor, tmp_path, api):
    r = await demo.sembrar(server.db, tmp_path)
    hd = await entrar(api, demo.DOCENTE, r["contrasena"])
    clases = (await api.get("/api/docente/clases", headers=hd)).json()
    assert [(c["nombre"], c["inscritos"]) for c in clases] == [(demo.CLASE, 4)]
    res = (await api.get(f"/api/docente/retos/{r['reto_id']}/resultados", headers=hd)).json()
    conceptos = {k for it in res["intentos"] for k in it["errores_concepto"]}
    assert conceptos == {"balanceo", "mol", "masa", "limitante", "rendimiento"}
    assert {it["completado"] for it in res["intentos"]} == {True, False}


async def test_limpiar_borra_solo_la_demo(motor, tmp_path, api, h):
    db = server.db
    # Datos "reales" del colegio que no deben tocarse
    await api.post("/api/docentes", headers=h,
                   json={"usuario": "profe_real", "nombre": "Real", "contrasena": "clave-docente-1"})
    hd = await entrar(api, "profe_real")
    clase = (await api.post("/api/docente/clases", headers=hd, json={"nombre": "5to B"})).json()
    real = await db.crear_usuario("estu_real", "Estu", "#3FA9F5")
    await db.inscribir(clase["id"], real["id"])

    await demo.sembrar(db, tmp_path)
    await demo.limpiar(db, tmp_path)
    assert await db.buscar_docente(demo.DOCENTE) is None
    assert all([await db.buscar_usuario(u) is None for u, _, _ in demo.ESTUDIANTES])
    assert await db.intentos() == [] and await db.misiones() == []
    assert not (tmp_path / demo.ARCHIVO_CREDENCIALES).exists()
    assert await db.buscar_usuario("estu_real") is not None
    assert [i["usuario"] for i in await db.inscritos(clase["id"])] == ["estu_real"]
    # Y se puede volver a sembrar después de limpiar
    await demo.sembrar(db, tmp_path)
    assert (await contar(db))["intentos"] == 6


@pytest.mark.parametrize("opcion", ["--sembrar-demo", "--limpiar-demo"])
def test_el_exe_siembra_y_limpia_sobre_su_propio_quimica_db(tmp_path, monkeypatch, capsys, opcion):
    """sembrar_demo.bat / limpiar_demo.bat llaman al .exe: los datos van al quimica.db de
    su carpeta y el archivo de credenciales lleva también la contraseña del admin."""
    monkeypatch.setattr(servidor_local, "carpeta_base", lambda: tmp_path)
    for var in ("ADMIN_USER", "ADMIN_PASSWORD", "SQLITE_RUTA", "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(sys, "argv", ["QuimicaServidor.exe", "--sembrar-demo"])
    with pytest.raises(SystemExit) as fin:
        servidor_local.main()
    assert fin.value.code == 0 and (tmp_path / "quimica.db").is_file()
    cred = demo.leer_credenciales(tmp_path / demo.ARCHIVO_CREDENCIALES)
    admin = demo.leer_credenciales(tmp_path / "admin.txt")
    assert cred["ADMIN_PASSWORD"] == admin["ADMIN_PASSWORD"]
    assert cred["DOCENTE_PASSWORD"] in capsys.readouterr().out
    if opcion == "--limpiar-demo":
        monkeypatch.setattr(sys, "argv", ["QuimicaServidor.exe", opcion])
        with pytest.raises(SystemExit) as fin:
            servidor_local.main()
        assert fin.value.code == 0 and not (tmp_path / demo.ARCHIVO_CREDENCIALES).exists()
