"""Rol docente en el panel (revisión 20/11): login con rol en el JWT, el admin gestiona
docentes y cada docente ve solo lo suyo."""
import jwt

import server
from conftest import ADMIN, CLAVE

MOTORES = ("sqlite", "postgres")


async def crear_docente(api, h, usuario, contrasena="clave-docente-1", nombre=None):
    r = await api.post("/api/docentes", headers=h,
                       json={"usuario": usuario, "nombre": nombre or usuario.title(), "contrasena": contrasena})
    assert r.status_code == 200, r.text
    return r.json()


async def entrar(api, usuario, contrasena="clave-docente-1"):
    r = await api.post("/api/login", json={"usuario": usuario, "contrasena": contrasena})
    assert r.status_code == 200, r.text
    assert r.json()["rol"] == "docente"
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def test_admin_crea_docente_y_el_login_lleva_el_rol_en_el_jwt(api, h, autenticador):
    await crear_docente(api, h, "profe_ana")
    r = await api.post("/api/login", json={"usuario": "profe_ana", "contrasena": "clave-docente-1"})
    datos = jwt.decode(r.json()["token"], autenticador.secreto, algorithms=["HS256"])
    assert datos["rol"] == "docente" and datos["sub"] == "profe_ana"
    r = await api.post("/api/login", json={"usuario": ADMIN, "contrasena": CLAVE})
    assert jwt.decode(r.json()["token"], autenticador.secreto, algorithms=["HS256"])["rol"] == "admin"
    # Contraseña mala de docente: 401 igual que la del admin
    r = await api.post("/api/login", json={"usuario": "profe_ana", "contrasena": "mala-mala"})
    assert r.status_code == 401
    # La contraseña no se guarda en claro
    assert "clave-docente-1" not in (await server.db.buscar_docente("profe_ana"))["hash"]
    assert [d["usuario"] for d in (await api.get("/api/docentes", headers=h)).json()] == ["profe_ana"]
    # Repetido o con contraseña corta
    r = await api.post("/api/docentes", headers=h, json={"usuario": "profe_ana", "nombre": "X", "contrasena": "x" * 8})
    assert r.status_code == 409
    r = await api.post("/api/docentes", headers=h, json={"usuario": "profe_bea", "nombre": "X", "contrasena": "corta"})
    assert r.status_code == 422


async def test_solo_el_admin_crea_docentes_y_el_docente_no_entra_a_lo_del_admin(api, h):
    await crear_docente(api, h, "profe_ana")
    hd = await entrar(api, "profe_ana")
    r = await api.post("/api/docentes", headers=hd, json={"usuario": "intruso", "nombre": "X", "contrasena": "x" * 8})
    assert r.status_code == 403
    for ruta in ("/api/estado", "/api/usuarios", "/api/logs", "/api/auditoria", "/api/docentes"):
        assert (await api.get(ruta, headers=hd)).status_code == 403, ruta
    # Y el admin no usa las rutas del docente (no tiene clases propias)
    assert (await api.get("/api/docente/clases", headers=h)).status_code == 403


async def test_desactivar_un_docente_corta_su_sesion_y_su_login(api, h):
    await crear_docente(api, h, "profe_ana")
    hd = await entrar(api, "profe_ana")
    assert (await api.get("/api/docente/clases", headers=hd)).status_code == 200
    assert (await api.post("/api/docentes/profe_ana/desactivar", headers=h)).status_code == 200
    assert (await api.get("/api/docente/clases", headers=hd)).status_code == 401
    r = await api.post("/api/login", json={"usuario": "profe_ana", "contrasena": "clave-docente-1"})
    assert r.status_code == 403
    assert (await api.post("/api/docentes/profe_ana/activar", headers=h)).status_code == 200
    await entrar(api, "profe_ana")


async def test_clase_con_codigo_de_8_sin_letras_ambiguas_y_reto(api, h):
    await crear_docente(api, h, "profe_ana")
    hd = await entrar(api, "profe_ana")
    clase = (await api.post("/api/docente/clases", headers=hd, json={"nombre": "3°A"})).json()
    assert len(clase["codigo"]) == 8 and not set(clase["codigo"]) & set("O0I1L")
    r = await api.post("/api/docente/retos", headers=hd,
                       json={"clase_id": clase["id"], "semilla": 42, "jugadores_por_grupo": 2, "tiempo_limite_s": 600})
    assert r.status_code == 200, r.text
    reto = r.json()
    assert reto["semilla"] == 42 and reto["abierto"] is True
    # Sin semilla, el servidor sortea una y la deja FIJA en el reto
    r = await api.post("/api/docente/retos", headers=hd, json={"clase_id": clase["id"]})
    assert r.json()["semilla"] > 0
    assert len((await api.get("/api/docente/retos", headers=hd)).json()) == 2
    assert (await api.post(f"/api/docente/retos/{reto['id']}/cerrar", headers=hd)).status_code == 200
    r = await api.get(f"/api/docente/retos/{reto['id']}/resultados", headers=hd)
    assert r.json()["reto"]["abierto"] is False and r.json()["intentos"] == []
    r = await api.post("/api/docente/retos", headers=hd, json={"clase_id": clase["id"], "nivel": "no_existe"})
    assert r.status_code == 422


async def test_un_docente_no_ve_las_clases_ni_los_retos_de_otro(api, h):
    """Pertenencia: cada ruta del docente valida que la clase o el reto sean suyos."""
    await crear_docente(api, h, "profe_ana")
    await crear_docente(api, h, "profe_beto")
    ha, hb = await entrar(api, "profe_ana"), await entrar(api, "profe_beto")
    clase = (await api.post("/api/docente/clases", headers=ha, json={"nombre": "De Ana"})).json()
    reto = (await api.post("/api/docente/retos", headers=ha, json={"clase_id": clase["id"]})).json()
    est = await server.db.crear_usuario("estu_ana", "Estu", "#3FA9F5")
    await server.db.inscribir(clase["id"], est["id"])

    assert (await api.get("/api/docente/clases", headers=hb)).json() == []
    assert (await api.get("/api/docente/retos", headers=hb)).json() == []
    assert (await api.get(f"/api/docente/clases/{clase['id']}", headers=hb)).status_code == 404
    assert (await api.get(f"/api/docente/retos/{reto['id']}/resultados", headers=hb)).status_code == 404
    assert (await api.post(f"/api/docente/retos/{reto['id']}/cerrar", headers=hb)).status_code == 404
    assert (await api.post("/api/docente/retos", headers=hb, json={"clase_id": clase["id"]})).status_code == 404
    assert (await api.get("/api/docente/estudiantes/estu_ana", headers=hb)).status_code == 404
    # La dueña sí ve todo
    r = await api.get(f"/api/docente/clases/{clase['id']}", headers=ha)
    assert [i["usuario"] for i in r.json()["inscritos"]] == ["estu_ana"]
    assert (await api.get("/api/docente/estudiantes/estu_ana", headers=ha)).status_code == 200


async def test_vivo_y_logs_del_docente_solo_muestran_a_sus_estudiantes(api, h, servidor_juego, bot):
    await crear_docente(api, h, "profe_ana")
    ha = await entrar(api, "profe_ana")
    clase = (await api.post("/api/docente/clases", headers=ha, json={"nombre": "De Ana"})).json()
    mio = await bot(servidor_juego, "estu_mio", nombre="Mio")
    await bot(servidor_juego, "ajeno_1", nombre="Ajeno")
    await mio.env(t="unirse_clase", codigo=clase["codigo"])
    await mio.rec("perfil", cuando=lambda m: m.get("clases"))
    await mio.env(t="crear_sala")
    sala = (await mio.rec("sala"))["sala"]

    vivo = (await api.get("/api/docente/vivo", headers=ha)).json()
    assert [s["id"] for s in vivo["salas"]] == [sala["id"]]
    assert [c["usuario"] for c in vivo["conectados"]] == ["estu_mio"]
    logs = (await api.get("/api/docente/logs", headers=ha)).json()["logs"]
    assert any("estu_mio" in x["mensaje"] for x in logs)
    assert not any("ajeno_1" in x["mensaje"] for x in logs)

