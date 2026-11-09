"""Tests de las prioridades 🔴 del panel (MDs/SPRINT3.md §0.1 y §3, Fase S3-1)."""
import asyncio
import json
import logging
import socket

import pytest
import uvicorn
import websockets

import server
from conftest import ADMIN, CLAVE

RUTAS_PROTEGIDAS = [
    ("get", "/api/estado"), ("get", "/api/salas"), ("post", "/api/salas/ABCD/cerrar"),
    ("post", "/api/jugadores/abc/expulsar"), ("get", "/api/usuarios"), ("get", "/api/usuarios/ana"),
    ("get", "/api/logs"), ("get", "/api/auditoria"), ("get", "/api/estadisticas"), ("post", "/api/aviso"),
    ("post", "/api/usuarios/ana/bloquear"), ("post", "/api/usuarios/ana/desbloquear"),
]


async def acciones(api, h):
    return [a["accion"] for a in (await api.get("/api/auditoria", headers=h)).json()["acciones"]]


# ----------------------------------------------------------------- 1. login
async def test_login_ok_y_contrasena_mala(api):
    r = await api.post("/api/login", json={"usuario": ADMIN, "contrasena": CLAVE})
    assert r.status_code == 200 and r.json()["token"]
    r = await api.post("/api/login", json={"usuario": ADMIN, "contrasena": "mala"})
    assert r.status_code == 401
    r = await api.post("/api/login", json={"usuario": "otro", "contrasena": CLAVE})
    assert r.status_code == 401


async def test_sexto_intento_en_un_minuto_da_429(api):
    for _ in range(5):
        assert (await api.post("/api/login", json={"usuario": ADMIN, "contrasena": "mala"})).status_code == 401
    # Ni siquiera la contraseña correcta pasa: el límite es por IP, no por acierto
    r = await api.post("/api/login", json={"usuario": ADMIN, "contrasena": CLAVE})
    assert r.status_code == 429


def test_sin_contrasena_el_panel_queda_deshabilitado(monkeypatch):
    import auth
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert auth.Autenticador.desde_entorno() is None


# ----------------------------------------------------------------- 2. sin token
@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
async def test_sin_token_da_401(api, metodo, ruta):
    kw = {"json": {"motivo": "x", "mensaje": "x"}} if metodo == "post" else {}
    assert (await getattr(api, metodo)(ruta, **kw)).status_code == 401
    r = await getattr(api, metodo)(ruta, headers={"Authorization": "Bearer inventado"}, **kw)
    assert r.status_code == 401


async def test_token_de_otro_secreto_no_vale(api):
    import auth
    falso = auth.Autenticador(ADMIN, CLAVE, "otro-secreto-" + "y" * 32).emitir_token(ADMIN)
    assert (await api.get("/api/estado", headers={"Authorization": f"Bearer {falso}"})).status_code == 401


# ----------------------------------------------------------------- estado y salas en vivo
async def test_estado_y_salas_muestran_lo_que_pasa_en_el_juego(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test", nombre="Ana")
    b = await bot(servidor_juego, "beto_test", nombre="Beto")
    await a.env(t="crear_sala", nombre_sala="Química 1", maximo=4)
    sala = (await a.rec("sala"))["sala"]
    await b.env(t="unirse", sala_id=sala["id"])
    await b.rec("sala")

    e = (await api.get("/api/estado", headers=h)).json()
    assert e["conectados"] == 2 and e["con_sesion"] == 2 and e["salas"] == 1
    assert e["partidas_en_curso"] == 0 and e["modo_bd"] is False
    assert {j["usuario"] for j in e["jugadores"]} == {"ana_test", "beto_test"}

    salas = (await api.get("/api/salas", headers=h)).json()
    assert len(salas) == 1 and salas[0]["nombre"] == "Química 1"
    roles = {j["usuario"]: j["rol"] for j in salas[0]["jugadores"]}
    assert roles == {"ana_test": "wizard", "beto_test": "player"}


# ----------------------------------------------------------------- 3. expulsar
async def test_expulsar_avisa_al_cliente_y_cierra_su_conexion(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test")
    r = await api.post(f"/api/jugadores/{a.id}/expulsar", headers=h, json={"motivo": "Lenguaje inapropiado"})
    assert r.status_code == 200
    m = await a.rec("expulsado")
    assert m["motivo"] == "Lenguaje inapropiado"
    assert await a.cerrado()
    await asyncio.sleep(0.05)  # el finally de cliente() libera la sesión
    assert a.id not in server.jugadores and "ana_test" not in server.sesiones
    # Puede volver a entrar (expulsar no es bloquear)
    r2, w2 = await asyncio.open_connection("127.0.0.1", servidor_juego)
    w2.write(b'{"t":"login","usuario":"ana_test"}\n')
    assert json.loads(await asyncio.wait_for(r2.readline(), 3))["t"] == "perfil"
    w2.close()


async def test_expulsar_a_un_player_en_sala_lo_saca_de_la_sala(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test")
    b = await bot(servidor_juego, "beto_test")
    await a.env(t="crear_sala")
    sala = (await a.rec("sala"))["sala"]
    await b.env(t="unirse", sala_id=sala["id"])
    await a.rec("sala")
    await api.post(f"/api/jugadores/{b.id}/expulsar", headers=h, json={"motivo": "prueba"})
    assert (await a.rec("salio"))["id"] == b.id
    assert len(server.salas[sala["id"]].jugadores) == 1


async def test_expulsar_valida_motivo_y_jugador(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test")
    assert (await api.post(f"/api/jugadores/{a.id}/expulsar", headers=h, json={"motivo": ""})).status_code == 422
    assert (await api.post(f"/api/jugadores/{a.id}/expulsar", headers=h, json={})).status_code == 422
    assert (await api.post("/api/jugadores/noexiste/expulsar", headers=h, json={"motivo": "x"})).status_code == 404


# ----------------------------------------------------------------- cerrar sala
async def test_cerrar_sala_manda_sala_cerrada_a_todos(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test")
    b = await bot(servidor_juego, "beto_test")
    await a.env(t="crear_sala")
    sala = (await a.rec("sala"))["sala"]
    await b.env(t="unirse", sala_id=sala["id"])
    await b.rec("sala")
    r = await api.post(f"/api/salas/{sala['id'].lower()}/cerrar", headers=h, json={"motivo": "Fin de la clase"})
    assert r.status_code == 200
    for x in (a, b):
        m = await x.rec("sala_cerrada")
        assert "Fin de la clase" in m["motivo"]
    assert sala["id"] not in server.salas
    # Siguen conectados y con sesión: pueden crear otra sala
    await a.env(t="listar")
    assert (await a.rec("salas"))["lista"] == []
    assert (await api.post("/api/salas/ZZZZ/cerrar", headers=h, json={"motivo": "x"})).status_code == 404


# ----------------------------------------------------------------- usuarios y progreso
async def jugar_mision(a, b):
    """Ana (wizard) y Beto (player) completan la misión; Beto se equivoca una vez con Na."""
    await a.env(t="crear_sala")
    sala = (await a.rec("sala"))["sala"]
    await b.env(t="unirse", sala_id=sala["id"])
    await b.rec("sala")
    await b.env(t="listo", valor=True)
    await a.env(t="iniciar")
    inicio = await b.rec("inicio")
    objetos = {o["elemento"]: [] for o in inicio["mision"]["objetos"]}
    for o in inicio["mision"]["objetos"]:
        objetos[o["elemento"]].append(o["id"])
    for elem in ["Na", "H", "H", "O"]:
        obj = objetos[elem].pop() if elem != "Na" else objetos["Na"][0]
        await b.env(t="agarrar", obj=obj)
        await b.rec("obj")
        await b.env(t="soltar", obj=obj, x=0, y=0.5, z=4)  # dentro del reactor
        await b.rec("estado")
    return sala["id"]


async def test_usuarios_y_detalle_con_progreso_y_errores_frecuentes(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test", nombre="Ana")
    b = await bot(servidor_juego, "beto_test", nombre="Beto", color="#E04F4F")
    await jugar_mision(a, b)

    lista = (await api.get("/api/usuarios", headers=h)).json()
    assert lista["total"] == 2
    beto = next(u for u in lista["usuarios"] if u["usuario"] == "beto_test")
    assert beto["completadas"] == 1 and beto["errores"] == 1 and beto["conectado"] is True
    assert beto["color"] == "#E04F4F" and beto["mejor_tiempo_s"] is not None and beto["creado"]
    assert (await api.get("/api/usuarios?buscar=ana", headers=h)).json()["total"] == 1

    d = (await api.get("/api/usuarios/BETO_TEST", headers=h)).json()
    assert d["perfil"]["nombre"] == "Beto" and d["conectado"] and d["jugador_id"] == b.id
    assert d["resumen"]["completadas"] == 1 and d["resumen"]["errores"] == 1
    assert len(d["historial"]) == 1 and d["historial"][0]["errores"] == 1
    assert d["errores_por_elemento"] == [{"elemento": "Na", "veces": 1}]
    # Cuando llevó Na faltaban H y O: queda registrada la confusión con los dos
    assert {(c["llevo"], c["faltaba"]) for c in d["confusiones"]} == {("Na", "H"), ("Na", "O")}
    assert (await api.get("/api/usuarios/nadie", headers=h)).status_code == 404


# ----------------------------------------------------------------- 6. auditoría
async def test_cada_accion_deja_su_fila_en_la_auditoria(api, h, servidor_juego, bot):
    await api.post("/api/login", json={"usuario": ADMIN, "contrasena": "mala"})
    a = await bot(servidor_juego, "ana_test")
    b = await bot(servidor_juego, "beto_test")
    await a.env(t="crear_sala")
    sala = (await a.rec("sala"))["sala"]
    await api.post(f"/api/salas/{sala['id']}/cerrar", headers=h, json={"motivo": "m1"})
    await api.post(f"/api/jugadores/{b.id}/expulsar", headers=h, json={"motivo": "m2"})

    filas = (await api.get("/api/auditoria", headers=h)).json()["acciones"]
    assert [f["accion"] for f in filas] == ["expulsar", "cerrar_sala", "login_fallido", "login"]
    expulsar, cerrar = filas[0], filas[1]
    assert expulsar["admin"] == ADMIN and expulsar["objetivo"] == "beto_test"
    assert expulsar["detalle"]["motivo"] == "m2" and expulsar["ip"] == "10.0.0.1" and expulsar["fecha"]
    assert cerrar["objetivo"] == sala["id"] and cerrar["detalle"]["jugadores"] == ["ana_test"]
    # La contraseña nunca queda en la auditoría
    assert "mala" not in json.dumps(filas)


# ----------------------------------------------------------------- logs
async def test_logs_se_filtran_por_nivel_y_texto(api, h):
    log = logging.getLogger("servidor")
    log.info("mensaje normal de prueba")
    log.warning("advertencia de prueba")
    log.error("fallo de prueba XYZ")
    r = (await api.get("/api/logs?nivel=warning", headers=h)).json()
    assert [x["mensaje"] for x in r["logs"]] == ["advertencia de prueba"]
    r = (await api.get("/api/logs?buscar=xyz", headers=h)).json()
    assert len(r["logs"]) == 1 and r["logs"][0]["nivel"] == "ERROR"
    r = (await api.get("/api/logs", headers=h)).json()
    assert r["logs"][0]["mensaje"] == "fallo de prueba XYZ"  # lo más nuevo primero


# ----------------------------------------------------------------- WebSocket en vivo
def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_websocket_empuja_logs_y_estado(app, token, servidor_juego, bot):
    import admin_api
    admin_api.ESTADO_CADA_S = 0.3
    puerto = puerto_libre()
    web = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    tarea = asyncio.create_task(web.serve())
    while not web.started:
        await asyncio.sleep(0.02)
    try:
        # Token malo → cierre con 4401 (el panel vuelve al login)
        async with websockets.connect(f"ws://127.0.0.1:{puerto}/api/ws?token=malo") as ws:
            with pytest.raises(websockets.ConnectionClosed) as e:
                await ws.recv()
            assert e.value.rcvd.code == 4401

        async with websockets.connect(f"ws://127.0.0.1:{puerto}/api/ws?token={token}") as ws:
            inicio = json.loads(await ws.recv())
            assert inicio["tipo"] == "inicio" and "conectados" in inicio["estado"]
            await bot(servidor_juego, "ana_test")  # genera el log "Sesión de ana_test..."
            vistos = []
            while not any(m["tipo"] == "log" and "ana_test" in m["mensaje"] for m in vistos) \
                    or not any(m["tipo"] == "estado" and m["estado"]["con_sesion"] == 1 for m in vistos):
                vistos.append(json.loads(await asyncio.wait_for(ws.recv(), 3)))
    finally:
        admin_api.ESTADO_CADA_S = 2.0
        web.should_exit = True
        await tarea


# ----------------------------------------------------------------- 🟡 estadísticas
async def test_estadisticas_con_pandas(api, h, servidor_juego, bot):
    vacio = (await api.get("/api/estadisticas", headers=h)).json()
    assert vacio["resumen"]["errores_totales"] == 0 and vacio["por_dia"] == []
    a = await bot(servidor_juego, "ana_test")
    b = await bot(servidor_juego, "beto_test")
    await jugar_mision(a, b)
    e = (await api.get("/api/estadisticas", headers=h)).json()
    assert e["resumen"] == {"errores_totales": 1, "misiones_completadas": 1,
                            "usuarios_con_errores": 1, "usuarios_con_misiones": 1}
    assert e["errores_por_elemento"] == [{"elemento": "Na", "veces": 1, "porcentaje": 100.0, "usuarios": 1}]
    assert {(c["llevo"], c["faltaba"]) for c in e["confusiones"]} == {("Na", "H"), ("Na", "O")}
    assert e["por_mision"][0]["mision"] == "agua" and e["por_mision"][0]["completadas"] == 1
    assert e["por_dia"][0]["completadas"] == 1
    assert e["usuarios_con_mas_errores"] == [{"usuario": "beto_test", "errores": 1}]
    assert (await api.get("/api/estadisticas")).status_code == 401


# ----------------------------------------------------------------- 🟡 5. aviso global
async def test_aviso_llega_a_todos_los_clientes(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test")
    b = await bot(servidor_juego, "beto_test")
    r = await api.post("/api/aviso", headers=h, json={"mensaje": "  El servidor se reinicia en 5 minutos "})
    assert r.status_code == 200 and r.json()["conexiones"] == 2
    for x in (a, b):
        assert (await x.rec("aviso"))["msg"] == "El servidor se reinicia en 5 minutos"
    assert (await api.post("/api/aviso", headers=h, json={"mensaje": "x" * 201})).status_code == 422
    assert (await api.post("/api/aviso", headers=h, json={"mensaje": "   "})).status_code == 422
    assert (await api.post("/api/aviso", json={"mensaje": "hola"})).status_code == 401
    assert (await acciones(api, h))[0] == "aviso"


# ----------------------------------------------------------------- 🟡 4. bloquear
async def test_bloquear_impide_el_login_y_expulsa_si_esta_conectado(api, h, servidor_juego, bot):
    a = await bot(servidor_juego, "ana_test")
    r = await api.post("/api/usuarios/ANA_TEST/bloquear", headers=h, json={"motivo": "Insultos en el chat"})
    assert r.status_code == 200
    assert (await a.rec("expulsado"))["motivo"] == "Cuenta bloqueada: Insultos en el chat"
    assert await a.cerrado()
    await asyncio.sleep(0.05)

    async def intentar_login():
        r2, w2 = await asyncio.open_connection("127.0.0.1", servidor_juego)
        w2.write(b'{"t":"login","usuario":"ana_test"}\n')
        m = json.loads(await asyncio.wait_for(r2.readline(), 3))
        w2.close()
        return m
    m = await intentar_login()
    assert m == {"t": "error", "msg": "Cuenta bloqueada: Insultos en el chat"}
    lista = (await api.get("/api/usuarios", headers=h)).json()["usuarios"]
    assert lista[0]["bloqueado"] is True
    d = (await api.get("/api/usuarios/ana_test", headers=h)).json()
    assert d["perfil"]["bloqueado"] and d["perfil"]["motivo_bloqueo"] == "Insultos en el chat"

    assert (await api.post("/api/usuarios/ana_test/desbloquear", headers=h, json={"motivo": "Pidió disculpas"})).status_code == 200
    assert (await intentar_login())["t"] == "perfil"
    filas = (await api.get("/api/auditoria", headers=h)).json()["acciones"]
    assert [f["accion"] for f in filas[:2]] == ["desbloquear", "bloquear"]
    assert filas[1]["detalle"] == {"motivo": "Insultos en el chat", "expulsado": True}
    assert (await api.post("/api/usuarios/nadie/bloquear", headers=h, json={"motivo": "x"})).status_code == 404
    assert (await api.post("/api/usuarios/ana_test/bloquear", headers=h, json={"motivo": ""})).status_code == 422


# ----------------------------------------------------------------- basura binaria en el puerto del juego
async def test_bytes_binarios_no_tumban_al_servidor(servidor_juego, bot, caplog):
    # Un navegador o un escáner de puertos manda bytes que no son UTF-8 ni JSON.
    r, w = await asyncio.open_connection("127.0.0.1", servidor_juego)
    w.write(b"\xff\xfe\x00\x01GET / HTTP/1.1\x80\x81\n")
    await w.drain()
    with caplog.at_level(logging.WARNING):
        # El servidor cierra esa conexión: readline() devuelve vacío.
        assert await asyncio.wait_for(r.readline(), 3) == b""
    w.close()
    assert any("Datos no válidos desde" in m for m in caplog.messages)
    # Y sigue vivo: un jugador legítimo entra normal después de la basura.
    a = await bot(servidor_juego, "ana_test", nombre="Ana")
    assert a.id
