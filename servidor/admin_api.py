"""
API del panel web de administración (FastAPI). Corre en el mismo event loop que el
servidor del juego (ver MDs/SPRINT3.md §2.1), así que lee y modifica directamente
las salas y los jugadores que están en memoria.

`juego` es el módulo server.py. Se recibe como parámetro en vez de hacer
"import server": al ejecutar "python server.py" ese módulo se llama __main__, y un
"import server" cargaría una SEGUNDA copia con sus propias salas, vacías.
"""
import asyncio
import collections
import json
import logging
import os
import pathlib
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

log = logging.getLogger("servidor")

POR_PAGINA = 50
ESTADO_CADA_S = 2.0


class Login(BaseModel):
    usuario: str = Field(max_length=100)
    contrasena: str = Field(max_length=200)


class Aviso(BaseModel):
    mensaje: str = Field(min_length=1, max_length=200)


class ConMotivo(BaseModel):
    # Motivo obligatorio: es lo que hace útil a la auditoría (§2.6)
    motivo: str = Field(min_length=1, max_length=200)


# ----------------------------------------------------------------- auditoría
class Auditoria:
    """Acciones de admin: en la tabla auditoria_admin, o en memoria sin BD (las últimas 2000)."""

    def __init__(self, juego):
        self.juego = juego
        self.memoria: collections.deque = collections.deque(maxlen=2000)
        self.siguiente_id = 1

    async def anotar(self, admin: str, accion: str, objetivo: str = "", detalle: dict | None = None, ip: str = ""):
        detalle = detalle or {}
        log.info("Auditoría: %s → %s %s %s", admin, accion, objetivo, json.dumps(detalle, ensure_ascii=False))
        if self.juego.db is None:
            self.memoria.append({"id": self.siguiente_id, "admin": admin, "accion": accion, "objetivo": objetivo,
                                 "detalle": detalle, "ip": ip, "fecha": datetime.now(timezone.utc)})
            self.siguiente_id += 1
            return
        try:
            await self.juego.db.anotar_auditoria(admin, accion, objetivo, detalle, ip)
        except Exception as e:
            log.error("No se pudo guardar la auditoría (%s %s): %s", accion, objetivo, e)

    async def listar(self, pagina: int, accion: str = "") -> dict:
        pagina = max(1, pagina)
        if self.juego.db is None:
            filas = [f for f in reversed(self.memoria) if not accion or f["accion"] == accion]
            return {"total": len(filas), "pagina": pagina, "por_pagina": POR_PAGINA,
                    "acciones": filas[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA]}
        total, filas = await self.juego.db.listar_auditoria(pagina, POR_PAGINA, accion)
        return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA, "acciones": filas}


# ----------------------------------------------------------------- vistas del estado en memoria
def info_jugador(j) -> dict:
    return {"id": j.id, "usuario": j.usuario, "nombre": j.nombre, "color": j.color, "ip": j.ip,
            "sala": j.sala.id if j.sala else None, "rol": j.rol if j.sala else None,
            "conectado_s": round(time.time() - j.desde)}


def info_sala(s) -> dict:
    mision = None
    if s.mision is not None:
        m = s.mision
        mision = {"reactor": m.elementos_reactor(), "faltantes": m.faltantes(), "errores": m.errores,
                  "completada": m.completada, "segundos": round(time.monotonic() - m.t_inicio)}
    return {"id": s.id, "nombre": s.nombre, "estado": s.estado, "maximo": s.maximo,
            "cantidad": len(s.jugadores), "host": s.host_id,
            "jugadores": [{"id": j.id, "usuario": j.usuario, "nombre": j.nombre, "color": j.color,
                           "rol": j.rol, "listo": j.listo} for j in s.jugadores.values()],
            "mision": mision}


def estado(juego) -> dict:
    jugadores = list(juego.jugadores.values())
    return {
        "uptime_s": round(time.time() - juego.INICIO),
        "conectados": len(jugadores),
        "con_sesion": sum(1 for j in jugadores if j.usuario),
        "salas": len(juego.salas),
        "partidas_en_curso": sum(1 for s in juego.salas.values() if s.estado == "jugando"),
        "modo_bd": juego.db is not None,
        "jugadores": [info_jugador(j) for j in jugadores],
        "lista_salas": [info_sala(s) for s in juego.salas.values()],
    }


# ----------------------------------------------------------------- perfiles y progreso
async def listar_usuarios(juego, buscar: str, pagina: int) -> dict:
    pagina = max(1, pagina)
    buscar = buscar.strip().lower()
    if juego.db is None:
        filas = []
        for u in juego.usuarios_mem.values():
            if buscar and buscar not in u["usuario"] and buscar not in u["nombre"].lower():
                continue
            propias = [m for m in juego.misiones_mem if m["usuario"] == u["usuario"]]
            tiempos = [m["duracion_s"] for m in propias if m["mision"] == juego.MISION_AGUA]
            filas.append({"usuario": u["usuario"], "nombre": u["nombre"], "color": u["color"],
                          "creado": u.get("creado"), "ultimo_login": u.get("ultimo_login"),
                          "bloqueado": u.get("bloqueado", False), "completadas": len(propias),
                          "mejor_tiempo_s": min(tiempos, default=None),
                          "errores": juego.errores_mem.get(u["usuario"], 0)})
        filas.sort(key=lambda f: f["ultimo_login"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        total = len(filas)
        filas = filas[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA]
    else:
        total, filas = await juego.db.listar_usuarios(buscar, pagina, POR_PAGINA, juego.MISION_AGUA)
    for f in filas:
        f["conectado"] = f["usuario"] in juego.sesiones
        f["bloqueado"] = bool(f.get("bloqueado"))
        if f["mejor_tiempo_s"] is not None:
            f["mejor_tiempo_s"] = round(f["mejor_tiempo_s"], 1)
    return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA, "usuarios": filas}


def resumir_errores(fallos: list[dict]) -> tuple[list, list]:
    """De los eventos reaccion_fallida saca los errores por elemento y las confusiones.

    "esperado" es la lista de lo que faltaba en el reactor cuando el jugador soltó el
    elemento equivocado; "Llevó Na cuando faltaba H" es la confusión que le interesa al docente.
    """
    por_elemento = Counter(f["recibido"] for f in fallos)
    confusiones = Counter()
    for f in fallos:
        for faltaba in sorted(set(f.get("esperado") or [])):
            confusiones[(f["recibido"], faltaba)] += 1
    return ([{"elemento": e, "veces": n} for e, n in por_elemento.most_common()],
            [{"llevo": a, "faltaba": b, "veces": n} for (a, b), n in confusiones.most_common()])


async def detalle_usuario(juego, usuario: str) -> dict | None:
    usuario = usuario.strip().lower()
    if juego.db is None:
        u = juego.usuarios_mem.get(usuario)
        if u is None:
            return None
        perfil = {k: u.get(k) for k in ("usuario", "nombre", "color", "creado", "ultimo_login")}
        perfil["bloqueado"] = u.get("bloqueado", False)
        perfil["motivo_bloqueo"] = u.get("motivo_bloqueo")
        historial = sorted([{"fecha": m["fecha"], "mision": m["mision"], "sala": m["sala"],
                             "duracion_s": m["duracion_s"], "errores": m["errores"]}
                            for m in juego.misiones_mem if m["usuario"] == usuario],
                           key=lambda h: h["fecha"], reverse=True)
        fallos = [{**e["detalle"], "fecha": e["fecha"]} for e in juego.eventos_mem
                  if e["tipo"] == "reaccion_fallida" and e["detalle"].get("usuario") == usuario]
    else:
        datos = await juego.db.detalle_usuario(usuario)
        if datos is None:
            return None
        perfil, historial, fallos = datos
    for h in historial:
        h["duracion_s"] = round(h["duracion_s"], 1)
    tiempos = [h["duracion_s"] for h in historial if h["mision"] == juego.MISION_AGUA]
    por_elemento, confusiones = resumir_errores(fallos)
    conexion = juego.sesiones.get(usuario)
    return {
        "perfil": perfil,
        "conectado": conexion is not None,
        "jugador_id": conexion.id if conexion else None,  # para expulsarlo desde el detalle
        "sala": conexion.sala.id if conexion and conexion.sala else None,
        "resumen": {"completadas": len(historial), "mejor_tiempo_s": min(tiempos, default=None),
                    "promedio_s": round(sum(tiempos) / len(tiempos), 1) if tiempos else None,
                    "errores": len(fallos)},
        "historial": historial,
        "errores_por_elemento": por_elemento,
        "confusiones": confusiones,
        "ultimos_errores": [{"fecha": f["fecha"], "sala": f.get("sala"), "llevo": f["recibido"],
                             "faltaba": f.get("esperado") or []} for f in fallos[:20]],
    }


# ----------------------------------------------------------------- la app
def carpeta_panel() -> pathlib.Path | None:
    aqui = pathlib.Path(__file__).resolve().parent
    candidatas = [os.getenv("PANEL_DIR", ""), aqui / "panel_dist", aqui.parent / "panel" / "dist"]
    for c in candidatas:
        if c and (pathlib.Path(c) / "index.html").is_file():
            return pathlib.Path(c)
    return None


def crear_app(juego, autenticador, registro) -> FastAPI:
    app = FastAPI(title="Panel Química VR", docs_url=None, redoc_url=None, openapi_url=None)
    auditoria = Auditoria(juego)
    app.state.auditoria = auditoria

    def ip_de(request: Request) -> str:
        return request.client.host if request.client else "?"

    def admin_actual(request: Request) -> str:
        cabecera = request.headers.get("authorization", "")
        token = cabecera[7:] if cabecera.lower().startswith("bearer ") else ""
        admin = autenticador.validar_token(token) if token else None
        if admin is None:
            raise HTTPException(401, "Sesión inválida o vencida: vuelve a iniciar sesión")
        return admin

    # ---------------------------------------------------------- acceso
    @app.post("/api/login")
    async def login(datos: Login, request: Request):
        ip = ip_de(request)
        if not autenticador.permitir_intento(ip):
            await auditoria.anotar(datos.usuario[:40], "login_bloqueado", ip=ip, detalle={"motivo": "más de 5 intentos por minuto"})
            raise HTTPException(429, "Demasiados intentos: espera un minuto")
        if not autenticador.verificar(datos.usuario, datos.contrasena):
            # Se anota el usuario intentado (recortado), nunca la contraseña
            await auditoria.anotar(datos.usuario[:40], "login_fallido", ip=ip)
            raise HTTPException(401, "Usuario o contraseña incorrectos")
        await auditoria.anotar(datos.usuario, "login", ip=ip)
        return {"token": autenticador.emitir_token(datos.usuario), "usuario": datos.usuario,
                "expira_en_s": 8 * 3600}

    # ---------------------------------------------------------- gestión del servidor
    @app.get("/api/estado")
    async def ver_estado(admin: str = Depends(admin_actual)):
        return estado(juego)

    @app.get("/api/salas")
    async def ver_salas(admin: str = Depends(admin_actual)):
        return [info_sala(s) for s in juego.salas.values()]

    @app.post("/api/salas/{sala_id}/cerrar")
    async def cerrar_sala(sala_id: str, datos: ConMotivo, request: Request, admin: str = Depends(admin_actual)):
        sala = juego.salas.get(sala_id.upper())
        if sala is None:
            raise HTTPException(404, f"No existe la sala {sala_id}")
        jugadores = [j.usuario or j.nombre for j in sala.jugadores.values()]
        motivo = datos.motivo.strip()
        await juego.cerrar_sala(sala, f"Un administrador cerró la sala: {motivo}", por_admin=True)
        await auditoria.anotar(admin, "cerrar_sala", sala.id, {"motivo": motivo, "jugadores": jugadores}, ip_de(request))
        return {"ok": True}

    @app.post("/api/jugadores/{jugador_id}/expulsar")
    async def expulsar(jugador_id: str, datos: ConMotivo, request: Request, admin: str = Depends(admin_actual)):
        j = juego.jugadores.get(jugador_id)
        if j is None:
            raise HTTPException(404, "Ese jugador ya no está conectado")
        motivo = datos.motivo.strip()
        await juego.expulsar(j, motivo)
        await auditoria.anotar(admin, "expulsar", j.usuario or j.id,
                               {"motivo": motivo, "nombre": j.nombre, "sala": j.sala.id if j.sala else None},
                               ip_de(request))
        return {"ok": True}

    @app.post("/api/aviso")
    async def aviso(datos: Aviso, request: Request, admin: str = Depends(admin_actual)):
        texto = datos.mensaje.strip()
        if not texto:
            raise HTTPException(422, "El aviso está vacío")
        n = await juego.aviso_global(texto)
        await auditoria.anotar(admin, "aviso", "todos", {"mensaje": texto, "conexiones": n}, ip_de(request))
        return {"ok": True, "conexiones": n}

    async def bloqueo(usuario: str, bloquear: bool, datos: ConMotivo, request: Request, admin: str):
        usuario = usuario.strip().lower()
        conectado = usuario in juego.sesiones
        if not await juego.cambiar_bloqueo(usuario, bloquear, datos.motivo.strip()):
            raise HTTPException(404, f"No existe el usuario {usuario}")
        detalle = {"motivo": datos.motivo.strip()}
        if bloquear:
            detalle["expulsado"] = conectado
        await auditoria.anotar(admin, "bloquear" if bloquear else "desbloquear", usuario, detalle, ip_de(request))
        return {"ok": True}

    @app.post("/api/usuarios/{usuario}/bloquear")
    async def bloquear(usuario: str, datos: ConMotivo, request: Request, admin: str = Depends(admin_actual)):
        return await bloqueo(usuario, True, datos, request, admin)

    @app.post("/api/usuarios/{usuario}/desbloquear")
    async def desbloquear(usuario: str, datos: ConMotivo, request: Request, admin: str = Depends(admin_actual)):
        return await bloqueo(usuario, False, datos, request, admin)

    # ---------------------------------------------------------- auditoría de perfiles
    @app.get("/api/usuarios")
    async def usuarios(buscar: str = "", pagina: int = 1, admin: str = Depends(admin_actual)):
        return await listar_usuarios(juego, buscar[:50], pagina)

    @app.get("/api/usuarios/{usuario}")
    async def usuario(usuario: str, admin: str = Depends(admin_actual)):
        datos = await detalle_usuario(juego, usuario)
        if datos is None:
            raise HTTPException(404, f"No existe el usuario {usuario}")
        return datos

    @app.get("/api/estadisticas")
    async def ver_estadisticas(admin: str = Depends(admin_actual)):
        try:
            import estadisticas  # pandas es pesado: solo se carga si alguien abre la página
        except ImportError:
            raise HTTPException(503, "Falta pandas en el servidor: instala servidor/requirements.txt")
        return await estadisticas.obtener(juego)

    # ---------------------------------------------------------- logs y auditoría de admin
    @app.get("/api/logs")
    async def logs(nivel: str = "", buscar: str = "", pagina: int = 1, admin: str = Depends(admin_actual)):
        return await registro.consultar(nivel, buscar[:100], pagina)

    @app.get("/api/auditoria")
    async def ver_auditoria(pagina: int = 1, accion: str = "", admin: str = Depends(admin_actual)):
        return await auditoria.listar(pagina, accion)

    # ---------------------------------------------------------- en vivo
    @app.websocket("/api/ws")
    async def en_vivo(ws: WebSocket, token: str = ""):
        # El token va en la URL porque el navegador no deja poner headers al abrir un WebSocket
        await ws.accept()
        if autenticador.validar_token(token) is None:
            # 4401 = código propio; el panel lo reconoce y vuelve al login
            await ws.close(code=4401, reason="token inválido")
            return
        cola: asyncio.Queue = asyncio.Queue(maxsize=1000)
        registro.suscriptores.add(cola)

        async def emitir():
            await ws.send_json({"tipo": "inicio", "logs": registro.recientes(200), "estado": estado(juego)})
            proximo = time.monotonic() + ESTADO_CADA_S
            while True:
                try:
                    msg = await asyncio.wait_for(cola.get(), max(0.0, proximo - time.monotonic()))
                    await ws.send_json(msg)
                except asyncio.TimeoutError:
                    await ws.send_json({"tipo": "estado", "estado": estado(juego)})
                    proximo = time.monotonic() + ESTADO_CADA_S

        async def escuchar():
            # Solo sirve para enterarse enseguida de que el navegador cerró la pestaña
            while True:
                await ws.receive_text()

        tareas = [asyncio.create_task(emitir()), asyncio.create_task(escuchar())]
        try:
            await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in tareas:
                t.cancel()
            registro.suscriptores.discard(cola)
            for t in tareas:
                # Se recogen las excepciones (WebSocketDisconnect, etc.) para que asyncio no las reporte
                try:
                    await t
                except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                    pass

    # ---------------------------------------------------------- el panel compilado
    carpeta = carpeta_panel()
    if carpeta is not None:
        # Va al final: las rutas /api/* ya están registradas y tienen prioridad
        app.mount("/", StaticFiles(directory=carpeta, html=True), name="panel")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def sin_panel():
            return ("<h1>Panel no compilado</h1><p>La API funciona en /api, pero falta compilar "
                    "el panel: <code>cd panel && npm install && npm run build</code></p>")
    return app
