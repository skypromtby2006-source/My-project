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
import random
import re
import secrets
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import auth

log = logging.getLogger("servidor")

POR_PAGINA = 50
ESTADO_CADA_S = 2.0


class Login(BaseModel):
    usuario: str = Field(max_length=100)
    contrasena: str = Field(max_length=200)


class NuevoDocente(BaseModel):
    usuario: str = Field(min_length=4, max_length=16)
    nombre: str = Field(min_length=1, max_length=40)
    contrasena: str = Field(min_length=8, max_length=200)


class NuevaClase(BaseModel):
    nombre: str = Field(min_length=1, max_length=40)


class NuevoReto(BaseModel):
    clase_id: int
    nivel: str = Field(default="laberinto_01", max_length=60)
    semilla: int | None = Field(default=None, ge=0, le=2_000_000_000)
    jugadores_por_grupo: int = Field(default=2, ge=2, le=8)
    tiempo_limite_s: int | None = Field(default=None, ge=60, le=7200)


# 8 caracteres sin los que se confunden al dictarlos o copiarlos de la pizarra
# (O/0, I/1/L): 31 símbolos^8 ≈ 850 mil millones de códigos, imposible de adivinar a mano.
ALFABETO_CLASE = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
FORMATO_USUARIO = re.compile(r"^[a-z0-9_]{4,16}$")


def nuevo_codigo_clase() -> str:
    return "".join(secrets.choice(ALFABETO_CLASE) for _ in range(8))


def niveles_disponibles() -> list[str]:
    import nivel
    return sorted(x.stem for x in nivel.RUTA_NIVELES.glob("*.json"))


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


def estado_de_estudiantes(juego, estudiantes: set[str]) -> dict:
    """Partidas en vivo vistas por un docente: solo las salas donde hay alguno de SUS
    estudiantes, y en ellas solo se nombra a sus estudiantes (el resto va anónimo)."""
    salas = []
    for s in juego.salas.values():
        if not any(j.usuario in estudiantes for j in s.jugadores.values()):
            continue
        info = info_sala(s)
        for j, x in zip(s.jugadores.values(), info["jugadores"]):
            if j.usuario not in estudiantes:
                x.update(usuario="", nombre="(de otra clase)")
        info["reto"] = getattr(s, "reto", None) and s.reto["id"]
        p = getattr(s, "partida", None)
        if p is not None:
            info["laberinto"] = {"sala": p.sala_num, "errores": p.errores, "completada": p.completada,
                                 "segundos": round(time.monotonic() - p.t_inicio)}
        salas.append(info)
    conectados = [info_jugador(j) for j in juego.jugadores.values() if j.usuario in estudiantes]
    return {"salas": salas, "conectados": conectados}


def logs_de_estudiantes(juego, logs: list[dict], estudiantes: set[str]) -> list[dict]:
    """Logs que mencionan a un estudiante del docente: por su usuario, por el id de su
    conexión o por el código de la sala donde está (muchas líneas del servidor nombran
    la sala o la conexión y no el usuario). Ver docs/decisiones-revision.md."""
    claves = set(estudiantes)
    for j in juego.jugadores.values():
        if j.usuario in estudiantes:
            claves.add(j.id)
            if j.sala is not None:
                claves.add(j.sala.id)
    if not claves:
        return []
    patron = re.compile(r"\b(" + "|".join(re.escape(c) for c in sorted(claves)) + r")\b")
    return [x for x in logs if patron.search(x["mensaje"])]


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

    def sesion(request: Request) -> dict:
        cabecera = request.headers.get("authorization", "")
        token = cabecera[7:] if cabecera.lower().startswith("bearer ") else ""
        datos = autenticador.leer_token(token) if token else None
        if datos is None:
            raise HTTPException(401, "Sesión inválida o vencida: vuelve a iniciar sesión")
        return datos

    def admin_actual(request: Request) -> str:
        datos = sesion(request)
        if datos["rol"] != "admin":
            # 403 y no 401: el docente tiene una sesión válida, solo que esto no es suyo
            raise HTTPException(403, "Solo el administrador puede hacer esto")
        return datos["sub"]

    def bd():
        if juego.db is None:
            raise HTTPException(503, "El rol docente necesita la base de datos (PostgreSQL o SQLite)")
        return juego.db

    async def docente_actual(request: Request) -> dict:
        """El docente del token, leído de la BD en cada pedido: si el admin lo desactiva,
        su sesión deja de valer en el acto (no hay que esperar a que venza el JWT)."""
        datos = sesion(request)
        if datos["rol"] != "docente":
            raise HTTPException(403, "Esta sección es del rol docente")
        doc = await bd().docente_por_id(int(datos.get("did", 0)))
        if doc is None or not doc["activo"]:
            raise HTTPException(401, "Cuenta de docente desactivada: habla con el administrador")
        return doc

    async def clase_propia(clase_id: int, doc: dict) -> dict:
        # 404 y no 403 con las clases de otro docente: así ni siquiera se entera de que existen
        clase = await bd().clase(clase_id)
        if clase is None or clase["docente_id"] != doc["id"]:
            raise HTTPException(404, "No existe esa clase")
        return clase

    async def reto_propio(reto_id: int, doc: dict) -> dict:
        reto = await bd().reto(reto_id)
        if reto is None or reto["docente_id"] != doc["id"]:
            raise HTTPException(404, "No existe ese reto")
        return reto

    # ---------------------------------------------------------- acceso
    @app.post("/api/login")
    async def login(datos: Login, request: Request):
        ip = ip_de(request)
        if not autenticador.permitir_intento(ip):
            await auditoria.anotar(datos.usuario[:40], "login_bloqueado", ip=ip, detalle={"motivo": "más de 5 intentos por minuto"})
            raise HTTPException(429, "Demasiados intentos: espera un minuto")
        if autenticador.verificar(datos.usuario, datos.contrasena):
            await auditoria.anotar(datos.usuario, "login", ip=ip)
            return {"token": autenticador.emitir_token(datos.usuario), "usuario": datos.usuario,
                    "rol": "admin", "nombre": datos.usuario, "expira_en_s": 8 * 3600}
        # Si no es el admin del .env, puede ser un docente (tabla docentes, hash scrypt)
        doc = None
        if juego.db is not None:
            doc = await juego.db.buscar_docente(datos.usuario.strip().lower())
        if doc is not None and auth.verificar_contrasena(datos.contrasena, doc["hash"]):
            if not doc["activo"]:
                await auditoria.anotar(doc["usuario"], "login_docente_inactivo", ip=ip)
                raise HTTPException(403, "Cuenta de docente desactivada: habla con el administrador")
            await auditoria.anotar(doc["usuario"], "login_docente", ip=ip)
            return {"token": autenticador.emitir_token(doc["usuario"], "docente", doc["id"]),
                    "usuario": doc["usuario"], "rol": "docente", "nombre": doc["nombre"],
                    "expira_en_s": 8 * 3600}
        # Se anota el usuario intentado (recortado), nunca la contraseña
        await auditoria.anotar(datos.usuario[:40], "login_fallido", ip=ip)
        raise HTTPException(401, "Usuario o contraseña incorrectos")

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

    # ---------------------------------------------------------- docentes (solo el admin)
    @app.get("/api/docentes")
    async def ver_docentes(admin: str = Depends(admin_actual)):
        return await bd().listar_docentes()

    @app.post("/api/docentes")
    async def crear_docente(datos: NuevoDocente, request: Request, admin: str = Depends(admin_actual)):
        usuario = datos.usuario.strip().lower()
        if not FORMATO_USUARIO.match(usuario):
            raise HTTPException(422, "Usuario inválido: de 4 a 16 caracteres, solo letras, números y guion bajo")
        if usuario == autenticador.usuario.lower():
            raise HTTPException(409, "Ese usuario es el del administrador")
        doc = await bd().crear_docente(usuario, datos.nombre.strip(), auth.hash_contrasena(datos.contrasena))
        if doc is None:
            raise HTTPException(409, f"Ya existe el docente {usuario}")
        await auditoria.anotar(admin, "crear_docente", usuario, {"nombre": doc["nombre"]}, ip_de(request))
        return doc

    async def activacion(usuario: str, activo: bool, request: Request, admin: str):
        usuario = usuario.strip().lower()
        if not await bd().fijar_docente_activo(usuario, activo):
            raise HTTPException(404, f"No existe el docente {usuario}")
        await auditoria.anotar(admin, "activar_docente" if activo else "desactivar_docente", usuario, ip=ip_de(request))
        return {"ok": True}

    @app.post("/api/docentes/{usuario}/activar")
    async def activar_docente(usuario: str, request: Request, admin: str = Depends(admin_actual)):
        return await activacion(usuario, True, request, admin)

    @app.post("/api/docentes/{usuario}/desactivar")
    async def desactivar_docente(usuario: str, request: Request, admin: str = Depends(admin_actual)):
        return await activacion(usuario, False, request, admin)

    # ---------------------------------------------------------- rol docente: solo lo suyo
    @app.get("/api/docente/yo")
    async def yo(doc: dict = Depends(docente_actual)):
        return {"usuario": doc["usuario"], "nombre": doc["nombre"]}

    @app.get("/api/docente/clases")
    async def mis_clases(doc: dict = Depends(docente_actual)):
        return await bd().clases_de_docente(doc["id"])

    @app.post("/api/docente/clases")
    async def crear_clase(datos: NuevaClase, request: Request, doc: dict = Depends(docente_actual)):
        for _ in range(10):  # un choque de códigos es casi imposible; si pasa, se sortea otro
            clase = await bd().crear_clase(doc["id"], datos.nombre.strip(), nuevo_codigo_clase())
            if clase is not None:
                await auditoria.anotar(doc["usuario"], "crear_clase", clase["codigo"],
                                       {"nombre": clase["nombre"]}, ip_de(request))
                return clase
        raise HTTPException(500, "No se pudo generar un código de clase; intenta de nuevo")

    @app.get("/api/docente/clases/{clase_id}")
    async def ver_clase(clase_id: int, doc: dict = Depends(docente_actual)):
        clase = await clase_propia(clase_id, doc)
        clase.pop("docente_id")
        return {"clase": clase, "inscritos": await bd().inscritos(clase_id)}

    @app.get("/api/docente/niveles")
    async def niveles(doc: dict = Depends(docente_actual)):
        return niveles_disponibles()

    @app.get("/api/docente/retos")
    async def mis_retos(doc: dict = Depends(docente_actual)):
        return await bd().retos_de_docente(doc["id"])

    @app.post("/api/docente/retos")
    async def crear_reto(datos: NuevoReto, request: Request, doc: dict = Depends(docente_actual)):
        await clase_propia(datos.clase_id, doc)
        if datos.nivel not in niveles_disponibles():
            raise HTTPException(422, f"No existe el nivel {datos.nivel}")
        # Semilla fija: todos los grupos del reto juegan el MISMO sorteo de números, así
        # los resultados se pueden comparar. Si el docente no elige una, se sortea al crear.
        semilla = datos.semilla if datos.semilla is not None else random.randint(1, 999_999)
        reto = await bd().crear_reto(datos.clase_id, datos.nivel, semilla,
                                     datos.jugadores_por_grupo, datos.tiempo_limite_s)
        await auditoria.anotar(doc["usuario"], "crear_reto", str(reto["id"]),
                               {"clase": reto["clase"], "semilla": semilla}, ip_de(request))
        return reto

    @app.post("/api/docente/retos/{reto_id}/cerrar")
    async def cerrar_reto(reto_id: int, request: Request, doc: dict = Depends(docente_actual)):
        await reto_propio(reto_id, doc)
        await bd().cerrar_reto(reto_id)
        await auditoria.anotar(doc["usuario"], "cerrar_reto", str(reto_id), ip=ip_de(request))
        return {"ok": True}

    @app.get("/api/docente/retos/{reto_id}/resultados")
    async def resultados_reto(reto_id: int, doc: dict = Depends(docente_actual)):
        reto = await reto_propio(reto_id, doc)
        return {"reto": reto, "intentos": await bd().intentos(reto_id=reto_id)}

    @app.get("/api/docente/estudiantes/{usuario}")
    async def resultados_estudiante(usuario: str, doc: dict = Depends(docente_actual)):
        usuario = usuario.strip().lower()
        if usuario not in await bd().estudiantes_de_docente(doc["id"]):
            raise HTTPException(404, "Ese estudiante no está en tus clases")
        return {"usuario": usuario, "intentos": await bd().intentos(usuario=usuario, docente_id=doc["id"])}

    @app.get("/api/docente/vivo")
    async def vivo_docente(doc: dict = Depends(docente_actual)):
        return estado_de_estudiantes(juego, await bd().estudiantes_de_docente(doc["id"]))

    @app.get("/api/docente/logs")
    async def logs_docente(doc: dict = Depends(docente_actual)):
        estudiantes = await bd().estudiantes_de_docente(doc["id"])
        return {"logs": logs_de_estudiantes(juego, registro.recientes(2000), estudiantes)[-300:]}

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
        if autenticador.validar_token(token) is None:   # solo admin: el docente usa /api/docente/vivo
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
