"""
Servidor multijugador - Juego de Química (demo)
Protocolo: TCP, un mensaje JSON por línea (terminado en '\n').

Cliente -> servidor:
  {"t":"registro","usuario":"ana","nombre":"Ana","color":"#3FA9F5"}
  {"t":"login","usuario":"ana"}
  {"t":"perfil_editar","nombre":"Ana","color":"#3FA9F5"}
  {"t":"perfil_ver"}
  {"t":"listar"}                       (desde aquí, solo con sesión iniciada)
  {"t":"crear_sala","nombre_sala":"Sala 1","maximo":4}
  {"t":"unirse","sala_id":"AB12"}
  {"t":"salir"}
  {"t":"listo","valor":true}
  {"t":"iniciar"}                      (solo el host)
  {"t":"pos","x":0,"y":0,"z":0,"ry":0}  (durante la partida)
  {"t":"agarrar","obj":"o3"}           (solo player)
  {"t":"soltar","obj":"o3","x":0,"y":0,"z":0}  (solo player)
  {"t":"senalar","obj":"o3"}           (solo wizard)
  {"t":"reiniciar"}                    (solo wizard)
  {"t":"ping"}

Servidor -> cliente:
  perfil, salas, sala, fuera, inicio, pos, salio, obj, senal, estado, error, pong
Detalle completo en docs/protocolo.md
"""
import asyncio
import json
import logging
import math
import os
import random
import re
import string
import time
import uuid
from datetime import datetime, timezone

HOST = "0.0.0.0"
PUERTO = int(os.getenv("PUERTO", "7777"))
DATABASE_URL = os.getenv("DATABASE_URL")  # si no existe, el servidor funciona sin BD

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("servidor")

db = None  # pool de asyncpg (opcional)

# ----------------------------------------------------------------- perfiles
# La misma paleta está en ClienteRed.cs; el cliente solo la usa para dibujar
# los botones, la regla la impone el servidor.
PALETA = ["#3FA9F5", "#F5D33F", "#E04FD8", "#4FE07A", "#F5913F", "#E04F4F", "#FFFFFF", "#6A5AE0"]
FORMATO_USUARIO = re.compile(r"^[a-z0-9_]{3,16}$")
MISION_AGUA = "agua"
# Solo usuario, nombre visible y color: los usuarios son en su mayoría menores
# de edad, así que no se guarda nada más (minimización de datos).


class ErrorPerfil(Exception):
    """Petición de perfil rechazada; el mensaje se le muestra al jugador tal cual."""


def validar_usuario(m: dict) -> str:
    # Se pasa a minúsculas antes de validar para que "Jona" y "jona" no sean dos perfiles
    usuario = str(m.get("usuario", "")).strip().lower()
    if not FORMATO_USUARIO.match(usuario):
        raise ErrorPerfil("Usuario inválido: de 3 a 16 caracteres, solo letras, números y _")
    return usuario


def validar_nombre_color(m: dict) -> tuple[str, str]:
    nombre = str(m.get("nombre", "")).strip()
    if not 1 <= len(nombre) <= 20:
        raise ErrorPerfil("El nombre visible debe tener de 1 a 20 caracteres")
    color = str(m.get("color", "")).strip().upper()
    if color not in PALETA:
        raise ErrorPerfil("Color no válido: elige uno de la paleta")
    return nombre, color


# Respaldo sin BD (Plan B2): los perfiles viven aquí y se pierden al cerrar.
usuarios_mem: dict[str, dict] = {}
misiones_mem: list[dict] = []
errores_mem: dict[str, int] = {}


# ----------------------------------------------------------------- modelos
class Jugador:
    def __init__(self, writer: asyncio.StreamWriter):
        self.id = uuid.uuid4().hex[:8]
        self.usuario = ""       # "" = todavía no inició sesión
        self.usuario_id = None  # id en la tabla usuarios (None sin BD)
        self.nombre = "Jugador"
        self.color = PALETA[6]
        self.writer = writer
        self.sala = None
        self.listo = False
        self.ip = (writer.get_extra_info("peername") or ("?",))[0]
        # Última posición conocida: si se desconecta llevando un objeto, ahí se cae
        self.x = self.y = self.z = 0.0

    @property
    def rol(self) -> str:
        # Se deriva del anfitrión en vez de guardarse aparte: así, cuando el
        # anfitrión cambia, el rol cambia solo y no hay dos datos que sincronizar.
        if self.sala is not None and self.sala.host_id == self.id:
            return "wizard"
        return "player"

    async def enviar(self, datos: dict):
        try:
            self.writer.write((json.dumps(datos, ensure_ascii=False) + "\n").encode("utf-8"))
            await self.writer.drain()
        except (ConnectionError, RuntimeError):
            pass  # el cliente ya se fue; lo limpia el bucle principal


class Sala:
    def __init__(self, nombre: str, host: Jugador, maximo: int):
        self.id = nuevo_codigo()
        self.nombre = nombre
        self.host_id = host.id
        self.maximo = maximo
        self.estado = "esperando"  # esperando | jugando
        self.jugadores: dict[str, Jugador] = {}
        self.mision: Mision | None = None

    def info(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "host": self.host_id,
            "maximo": self.maximo,
            "cantidad": len(self.jugadores),
            "estado": self.estado,
            "jugadores": [
                {"id": j.id, "nombre": j.nombre, "color": j.color, "listo": j.listo, "rol": j.rol}
                for j in self.jugadores.values()
            ],
        }


# ----------------------------------------------------------------- misión
# Única fuente de verdad del escenario: el cliente no tiene posiciones propias y
# dibuja la mesa, las esferas y el reactor con lo que llega en inicio.mision.
# Los jugadores aparecen en z=-5 (GestorPartida.cs); el reactor va en el suelo,
# al otro lado de la mesa, para que haya que caminar con cada esfera.
ELEMENTOS = ["H", "H", "O", "Na", "Cl", "C"]
MESA = {"x": 0.0, "y": 0.5, "z": 0.0, "ancho": 4.0, "alto": 1.0, "largo": 1.5}  # centro y tamaño
RADIO_OBJETO = 0.15
# Las 6 esferas en fila sobre la tapa, centradas. 0.7 m de separación para que las
# etiquetas del wizard ("Na", "Cl") no se encimen vistas desde la cámara.
SEPARACION = 0.7
POSICIONES_MESA = [(round(MESA["x"] + (i - (len(ELEMENTOS) - 1) / 2) * SEPARACION, 3),
                    MESA["y"] + MESA["alto"] / 2 + RADIO_OBJETO, MESA["z"])
                   for i in range(len(ELEMENTOS))]
REACTOR = {"x": 0.0, "y": 0.0, "z": 4.0, "radio": 1.0}
RECETA = {"H": 2, "O": 1}
FORMULA = "2 H + 1 O → H2O"  # sin "₂": la fuente del juego no lo tiene y se veía "H□O"


class Objeto:
    def __init__(self, id_: str, elemento: str, pos: tuple):
        self.id = id_
        self.elemento = elemento
        self.inicio = pos  # a dónde vuelve si provoca una reacción fallida
        self.x, self.y, self.z = pos
        self.portador = ""  # id del jugador que lo lleva; "" = nadie

    def info(self) -> dict:
        return {"id": self.id, "elemento": self.elemento,
                "x": self.x, "y": self.y, "z": self.z, "portador": self.portador}


class Mision:
    def __init__(self):
        # Los elementos se barajan sobre posiciones fijas: si siempre estuvieran
        # en el mismo lugar, el Player los memorizaría y ya no necesitaría al Wizard.
        elementos = random.sample(ELEMENTOS, len(ELEMENTOS))
        self.objetos: dict[str, Objeto] = {
            f"o{i + 1}": Objeto(f"o{i + 1}", e, POSICIONES_MESA[i]) for i, e in enumerate(elementos)
        }
        self.reactor: list[str] = []  # ids de los objetos ya aceptados por el reactor
        self.errores = 0
        self.errores_por: dict[str, int] = {}  # usuario -> errores en esta misión
        self.completada = False
        self.mensaje = ""
        self.t_inicio = time.monotonic()

    def elementos_reactor(self) -> list[str]:
        return [self.objetos[o].elemento for o in self.reactor]

    def faltantes(self) -> list[str]:
        dentro = self.elementos_reactor()
        return [e for e, n in RECETA.items() for _ in range(n - dentro.count(e))]

    def objeto_de(self, jugador_id: str) -> Objeto | None:
        return next((o for o in self.objetos.values() if o.portador == jugador_id), None)

    def estado(self) -> dict:
        return {"reactor": self.elementos_reactor(), "errores": self.errores,
                "completada": self.completada, "mensaje": self.mensaje}

    def info(self) -> dict:
        # La receta va como lista y no como diccionario porque JsonUtility de
        # Unity no sabe leer diccionarios.
        return {
            "objetos": [o.info() for o in self.objetos.values()],
            "reactor": REACTOR,
            "mesa": MESA,
            "radio_objeto": RADIO_OBJETO,
            "receta": [{"elemento": e, "cantidad": n} for e, n in RECETA.items()],
            "formula": FORMULA,
            "estado": self.estado(),
        }


def en_reactor(x: float, z: float) -> bool:
    # Solo cuenta la distancia horizontal: da igual a qué altura se suelte
    return math.hypot(x - REACTOR["x"], z - REACTOR["z"]) <= REACTOR["radio"]


salas: dict[str, Sala] = {}
jugadores: dict[str, Jugador] = {}
sesiones: dict[str, Jugador] = {}  # usuario -> conexión que lo tiene abierto


def nuevo_codigo() -> str:
    # Códigos de 4 caracteres sin letras confusas (O/0, I/1)
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        c = "".join(random.choices(alfabeto, k=4))
        if c not in salas:
            return c


# ----------------------------------------------------------------- base de datos
async def iniciar_bd():
    global db
    if not DATABASE_URL:
        log.warning("Sin DATABASE_URL: perfiles y progreso solo en memoria, se pierden al cerrar el servidor")
        return
    import asyncpg
    for intento in range(1, 11):
        try:
            db = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            # Las tablas se crean aquí y no con un .sql en docker-entrypoint-initdb.d:
            # Postgres solo corre esos scripts con el volumen vacío, y datos_db ya
            # existe en las instalaciones anteriores.
            async with db.acquire() as c:
                await c.execute("""
                    CREATE TABLE IF NOT EXISTS eventos (
                        id SERIAL PRIMARY KEY,
                        tipo TEXT NOT NULL,
                        detalle JSONB,
                        fecha TIMESTAMPTZ DEFAULT now()
                    );
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id SERIAL PRIMARY KEY,
                        usuario TEXT UNIQUE NOT NULL,
                        nombre TEXT NOT NULL,
                        color TEXT NOT NULL,
                        creado TIMESTAMPTZ DEFAULT now(),
                        ultimo_login TIMESTAMPTZ
                    );
                    CREATE TABLE IF NOT EXISTS misiones_completadas (
                        id SERIAL PRIMARY KEY,
                        usuario_id INT REFERENCES usuarios(id),
                        mision TEXT NOT NULL,
                        sala TEXT NOT NULL,
                        duracion_s REAL NOT NULL,
                        errores INT NOT NULL,
                        fecha TIMESTAMPTZ DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS misiones_por_usuario ON misiones_completadas (usuario_id)""")
            log.info("Conectado a PostgreSQL")
            return
        except Exception as e:
            log.warning("BD no disponible (intento %d/10): %s", intento, e)
            await asyncio.sleep(2)
    db = None
    log.error("No se pudo conectar a la BD; perfiles y progreso solo en memoria, se pierden al cerrar")


async def registrar(tipo: str, detalle: dict):
    if db is None:
        return
    try:
        async with db.acquire() as c:
            await c.execute("INSERT INTO eventos (tipo, detalle) VALUES ($1, $2)",
                            tipo, json.dumps(detalle, ensure_ascii=False))
    except Exception as e:
        log.warning("No se pudo registrar evento: %s", e)


# Cada función tiene dos caminos (BD y memoria) para que el Plan B2, sin Docker,
# siga funcionando igual salvo por la persistencia.
async def buscar_usuario(usuario: str) -> dict | None:
    if db is None:
        return usuarios_mem.get(usuario)
    async with db.acquire() as c:
        fila = await c.fetchrow("SELECT id, usuario, nombre, color FROM usuarios WHERE usuario = $1", usuario)
    return dict(fila) if fila else None


async def crear_usuario(usuario: str, nombre: str, color: str) -> dict | None:
    """Devuelve None si el usuario ya existe."""
    if db is None:
        if usuario in usuarios_mem:
            return None
        usuarios_mem[usuario] = {"id": None, "usuario": usuario, "nombre": nombre, "color": color}
        return usuarios_mem[usuario]
    # ON CONFLICT en vez de consultar antes: si dos clientes registran el mismo
    # usuario a la vez, la restricción UNIQUE decide sin carrera.
    async with db.acquire() as c:
        fila = await c.fetchrow(
            "INSERT INTO usuarios (usuario, nombre, color, ultimo_login) VALUES ($1, $2, $3, now()) "
            "ON CONFLICT (usuario) DO NOTHING RETURNING id, usuario, nombre, color",
            usuario, nombre, color)
    return dict(fila) if fila else None


async def marcar_login(usuario: str):
    if db is not None:
        async with db.acquire() as c:
            await c.execute("UPDATE usuarios SET ultimo_login = now() WHERE usuario = $1", usuario)


async def actualizar_usuario(usuario: str, nombre: str, color: str):
    if db is None:
        usuarios_mem[usuario].update(nombre=nombre, color=color)
        return
    async with db.acquire() as c:
        await c.execute("UPDATE usuarios SET nombre = $2, color = $3 WHERE usuario = $1", usuario, nombre, color)


async def guardar_mision(j: "Jugador", sala: str, duracion_s: float, errores: int):
    if db is None:
        misiones_mem.append({"usuario": j.usuario, "mision": MISION_AGUA, "sala": sala,
                             "duracion_s": duracion_s, "errores": errores,
                             "fecha": datetime.now(timezone.utc)})
        return
    async with db.acquire() as c:
        await c.execute(
            "INSERT INTO misiones_completadas (usuario_id, mision, sala, duracion_s, errores) "
            "VALUES ($1, $2, $3, $4, $5)", j.usuario_id, MISION_AGUA, sala, duracion_s, errores)


async def progreso(j: "Jugador") -> dict:
    # Los errores totales salen de los reaccion_fallida de eventos y no de
    # misiones_completadas: así también cuentan los de misiones reiniciadas o
    # abandonadas, y es el mismo dato que se analiza con pandas.
    if db is None:
        propias = [x for x in misiones_mem if x["usuario"] == j.usuario]
        tiempos = [x["duracion_s"] for x in propias if x["mision"] == MISION_AGUA]
        completadas, mejor, errores = len(propias), min(tiempos, default=None), errores_mem.get(j.usuario, 0)
        historial = sorted(propias, key=lambda x: x["fecha"], reverse=True)[:5]
    else:
        async with db.acquire() as c:
            fila = await c.fetchrow(
                "SELECT count(*) AS n, min(duracion_s) FILTER (WHERE mision = $2) AS mejor "
                "FROM misiones_completadas WHERE usuario_id = $1", j.usuario_id, MISION_AGUA)
            errores = await c.fetchval(
                "SELECT count(*) FROM eventos WHERE tipo = 'reaccion_fallida' AND detalle->>'usuario' = $1",
                j.usuario)
            historial = await c.fetch(
                "SELECT fecha, duracion_s, errores FROM misiones_completadas "
                "WHERE usuario_id = $1 ORDER BY fecha DESC LIMIT 5", j.usuario_id)
        completadas, mejor = fila["n"], fila["mejor"]
    return {
        "completadas": completadas,
        # 0 = todavía sin misiones: JsonUtility no lee null en un float
        "mejor_tiempo_s": round(mejor, 1) if mejor is not None else 0,
        "errores_totales": errores,
        "historial": [{"fecha": h["fecha"].isoformat(timespec="seconds"),
                       "duracion_s": round(h["duracion_s"], 1), "errores": h["errores"]}
                      for h in historial],
    }


async def enviar_perfil(j: "Jugador"):
    # Va el id de conexión porque la sala identifica a los jugadores por él
    # (host, portador, pos); antes llegaba en "bienvenido".
    await j.enviar({"t": "perfil", "id": j.id, "usuario": j.usuario, "nombre": j.nombre,
                    "color": j.color, "progreso": await progreso(j)})


async def iniciar_sesion(j: Jugador, datos: dict):
    j.usuario, j.usuario_id = datos["usuario"], datos["id"]
    j.nombre, j.color = datos["nombre"], datos["color"]
    sesiones[j.usuario] = j
    log.info("Sesión de %s (%s) en la conexión %s", j.usuario, j.nombre, j.id)
    await registrar("conexion", {"id": j.id, "usuario": j.usuario, "nombre": j.nombre, "ip": j.ip})
    await enviar_perfil(j)


async def manejar_perfil(j: Jugador, t: str, m: dict):
    if t in ("registro", "login"):
        if j.usuario:
            raise ErrorPerfil("Ya iniciaste sesión en esta conexión")
        usuario = validar_usuario(m)
        if t == "login" and usuario in sesiones:
            raise ErrorPerfil("Ese usuario ya tiene una sesión abierta")
        if t == "registro":
            nombre, color = validar_nombre_color(m)
            datos = await crear_usuario(usuario, nombre, color)
            if datos is None:
                raise ErrorPerfil("Ese usuario ya existe")
            await registrar("perfil_creado", {"usuario": usuario})
        else:
            datos = await buscar_usuario(usuario)
            if datos is None:
                raise ErrorPerfil("Usuario no encontrado")
            await marcar_login(usuario)
        # Se vuelve a mirar después de los await: otra conexión pudo entrar con
        # el mismo usuario mientras se consultaba la BD.
        if usuario in sesiones:
            raise ErrorPerfil("Ese usuario ya tiene una sesión abierta")
        return await iniciar_sesion(j, datos)

    if not j.usuario:
        raise ErrorPerfil("Inicia sesión primero")
    if t == "perfil_editar":
        nombre, color = validar_nombre_color(m)
        await actualizar_usuario(j.usuario, nombre, color)  # primero la BD: si falla, no queda a medias
        j.nombre, j.color = nombre, color
        if j.sala is not None:
            await difundir(j.sala, {"t": "sala", "sala": j.sala.info()})
    await enviar_perfil(j)


# ----------------------------------------------------------------- lógica
async def difundir(sala: Sala, datos: dict, excepto: Jugador | None = None):
    await asyncio.gather(*(j.enviar(datos) for j in list(sala.jugadores.values()) if j is not excepto))


def lista_salas() -> list:
    return [s.info() for s in salas.values()]


async def salir_de_sala(j: Jugador):
    sala = j.sala
    if sala is None:
        return
    sala.jugadores.pop(j.id, None)
    j.sala = None
    j.listo = False
    if not sala.jugadores:
        salas.pop(sala.id, None)
        log.info("Sala %s cerrada (vacía)", sala.id)
        await registrar("sala_cerrada", {"sala": sala.id})
        return
    caidos = [j]
    if sala.host_id == j.id:  # el host se fue: pasa al siguiente y se vuelve wizard
        sala.host_id = next(iter(sala.jugadores))
        # El nuevo wizard ya no puede soltar (regla de rol), así que si llevaba
        # algo se le cae ahí mismo; si no, el objeto quedaría bloqueado.
        caidos.append(sala.jugadores[sala.host_id])
    await difundir(sala, {"t": "salio", "id": j.id})
    await difundir(sala, {"t": "sala", "sala": sala.info()})
    if sala.mision is not None:
        for quien in caidos:
            o = sala.mision.objeto_de(quien.id)
            if o is not None:
                o.portador = ""
                o.x, o.y, o.z = quien.x, 0.15, quien.z  # al suelo, donde estaba el jugador
                await difundir(sala, {"t": "obj", "obj": o.info()})


async def entrar_a_sala(j: Jugador, sala: Sala):
    j.sala = sala
    j.listo = False
    sala.jugadores[j.id] = j
    await difundir(sala, {"t": "sala", "sala": sala.info()})


async def manejar(j: Jugador, m: dict):
    t = m.get("t")

    if t in ("registro", "login", "perfil_editar", "perfil_ver"):
        try:
            await manejar_perfil(j, t, m)
        except ErrorPerfil as e:
            await j.enviar({"t": "error", "msg": str(e)})
        except Exception:
            # Con la BD caída a mitad de la demo, el jugador recibe un aviso en vez de quedar esperando
            log.exception("Error de perfil en %s", t)
            await j.enviar({"t": "error", "msg": "No se pudo acceder a los perfiles; intenta de nuevo"})
        return

    # Sin identidad no hay a quién asignarle el progreso
    if t in ("listar", "crear_sala", "unirse") and not j.usuario:
        return await j.enviar({"t": "error", "msg": "Inicia sesión primero"})

    if t == "listar":
        await j.enviar({"t": "salas", "lista": lista_salas()})

    elif t == "crear_sala":
        await salir_de_sala(j)
        nombre = str(m.get("nombre_sala", "")).strip()[:30] or f"Sala de {j.nombre}"
        maximo = max(2, min(8, int(m.get("maximo") or 4)))
        sala = Sala(nombre, j, maximo)
        salas[sala.id] = sala
        await entrar_a_sala(j, sala)
        log.info("%s creó la sala %s (%s)", j.nombre, sala.id, nombre)
        await registrar("sala_creada", {"sala": sala.id, "nombre": nombre, "host": j.nombre})

    elif t == "unirse":
        codigo = str(m.get("sala_id", "")).strip().upper()
        sala = salas.get(codigo)
        if sala is None:
            return await j.enviar({"t": "error", "msg": f"No existe la sala {codigo}"})
        if sala is j.sala:
            return
        if sala.estado != "esperando":
            return await j.enviar({"t": "error", "msg": "La partida ya empezó"})
        if len(sala.jugadores) >= sala.maximo:
            return await j.enviar({"t": "error", "msg": "La sala está llena"})
        await salir_de_sala(j)
        await entrar_a_sala(j, sala)
        log.info("%s se unió a %s", j.nombre, sala.id)
        await registrar("union", {"sala": sala.id, "jugador": j.nombre})

    elif t == "salir":
        await salir_de_sala(j)
        await j.enviar({"t": "fuera"})

    elif t == "listo":
        if j.sala is None:
            return
        j.listo = bool(m.get("valor"))
        await difundir(j.sala, {"t": "sala", "sala": j.sala.info()})

    elif t == "iniciar":
        sala = j.sala
        if sala is None or sala.host_id != j.id:
            return await j.enviar({"t": "error", "msg": "Solo el anfitrión puede iniciar"})
        # Sin al menos un Player nadie puede agarrar objetos: la misión sería imposible
        if len(sala.jugadores) < 2:
            return await j.enviar({"t": "error", "msg": "Se necesitan al menos 2 jugadores"})
        if not all(x.listo for x in sala.jugadores.values() if x.id != sala.host_id):
            return await j.enviar({"t": "error", "msg": "Faltan jugadores por marcar 'Listo'"})
        sala.estado = "jugando"
        sala.mision = Mision()
        await difundir(sala, {"t": "inicio", "sala": sala.info(), "mision": sala.mision.info()})
        log.info("Partida iniciada en %s", sala.id)
        await registrar("partida_iniciada", {"sala": sala.id, "jugadores": len(sala.jugadores)})

    elif t == "pos":
        if j.sala is None or j.sala.estado != "jugando":
            return
        datos = {"t": "pos", "id": j.id}
        for k in ("x", "y", "z", "ry"):
            datos[k] = float(m.get(k, 0))
        j.x, j.y, j.z = datos["x"], datos["y"], datos["z"]
        await difundir(j.sala, datos, excepto=j)

    elif t in ("agarrar", "soltar", "senalar", "reiniciar"):
        await manejar_mision(j, t, m)

    elif t == "ping":
        await j.enviar({"t": "pong"})

    else:
        await j.enviar({"t": "error", "msg": f"Mensaje desconocido: {t}"})


async def manejar_mision(j: Jugador, t: str, m: dict):
    sala = j.sala
    if sala is None or sala.estado != "jugando" or sala.mision is None:
        return await j.enviar({"t": "error", "msg": "No hay una partida en curso"})
    mision = sala.mision
    # El servidor decide por rol: aunque un cliente modificado mande "agarrar"
    # siendo wizard, aquí se rechaza.
    rol_necesario = "player" if t in ("agarrar", "soltar") else "wizard"
    if j.rol != rol_necesario:
        accion = {"agarrar": "agarrar objetos", "soltar": "soltar objetos",
                  "senalar": "señalar", "reiniciar": "reiniciar la misión"}[t]
        return await j.enviar({"t": "error", "msg": f"Solo un {rol_necesario} puede {accion}"})

    if t == "reiniciar":
        anterior = mision
        sala.mision = Mision()
        await difundir(sala, {"t": "inicio", "sala": sala.info(), "mision": sala.mision.info()})
        log.info("Misión reiniciada en %s", sala.id)
        return await registrar("mision_reiniciada", {
            "sala": sala.id, "errores": anterior.errores, "completada": anterior.completada})

    o = mision.objetos.get(str(m.get("obj", "")))
    if o is None:
        return await j.enviar({"t": "error", "msg": "Ese objeto no existe"})

    if t == "senalar":
        await difundir(sala, {"t": "senal", "obj": o.id, "por": j.id})
        await registrar("senal", {"sala": sala.id, "jugador": j.nombre, "obj": o.id, "elemento": o.elemento})

    elif t == "agarrar":
        if mision.completada:
            return await j.enviar({"t": "error", "msg": "La misión ya está completada"})
        if o.portador:
            return await j.enviar({"t": "error", "msg": "Otro jugador ya lleva ese objeto"})
        if o.id in mision.reactor:
            return await j.enviar({"t": "error", "msg": "Ese objeto ya está en el reactor"})
        if mision.objeto_de(j.id) is not None:
            return await j.enviar({"t": "error", "msg": "Ya llevas un objeto"})
        # Como el bucle atiende un mensaje a la vez, si dos jugadores piden la
        # misma esfera "al mismo tiempo", el primero que llega se la lleva y el
        # segundo choca con la validación de arriba.
        o.portador = j.id
        await difundir(sala, {"t": "obj", "obj": o.info()})
        await registrar("agarrar", {"sala": sala.id, "jugador": j.nombre, "obj": o.id, "elemento": o.elemento})

    elif t == "soltar":
        if o.portador != j.id:
            return await j.enviar({"t": "error", "msg": "No llevas ese objeto"})
        try:
            x, y, z = (float(m.get(k, 0)) for k in ("x", "y", "z"))
        except (TypeError, ValueError):
            return await j.enviar({"t": "error", "msg": "Posición inválida"})
        if not all(math.isfinite(v) for v in (x, y, z)):
            return await j.enviar({"t": "error", "msg": "Posición inválida"})
        o.portador = ""
        o.x, o.y, o.z = x, y, z
        evento = None
        completada_ahora = False
        if mision.completada:
            pass  # se puede seguir moviendo cosas, pero el mensaje de victoria se mantiene
        elif not en_reactor(x, z):
            mision.mensaje = ""
        else:
            faltan = mision.faltantes()
            if o.elemento in faltan:
                mision.reactor.append(o.id)
                if len(faltan) == 1:  # era el último que faltaba
                    mision.completada = True
                    completada_ahora = True
                    mision.mensaje = f"¡Reacción completada! {FORMULA}"
                    evento = ("mision_completada", {
                        "sala": sala.id, "errores": mision.errores,
                        "duracion_s": round(time.monotonic() - mision.t_inicio, 1)})
                else:
                    mision.mensaje = f"{o.elemento} agregado al reactor"
            else:
                mision.errores += 1
                # El error es de quien soltó: permite el análisis por estudiante
                mision.errores_por[j.usuario] = mision.errores_por.get(j.usuario, 0) + 1
                if db is None:  # con BD el total se cuenta desde la tabla eventos
                    errores_mem[j.usuario] = errores_mem.get(j.usuario, 0) + 1
                o.x, o.y, o.z = o.inicio  # vuelve a la mesa
                mision.mensaje = f"Reacción inestable: {o.elemento} no va en la receta"
                # Este evento es el dato de "errores frecuentes" para el análisis posterior
                evento = ("reaccion_fallida", {
                    "sala": sala.id, "jugador": j.nombre, "usuario": j.usuario,
                    "esperado": faltan, "recibido": o.elemento})
        await difundir(sala, {"t": "obj", "obj": o.info()})
        await difundir(sala, {"t": "estado", **mision.estado()})
        await registrar("soltar", {"sala": sala.id, "jugador": j.nombre, "obj": o.id,
                                   "elemento": o.elemento, "x": x, "z": z})
        if evento:
            await registrar(*evento)
        if completada_ahora:
            await guardar_progreso(sala, mision, evento[1]["duracion_s"])


async def guardar_progreso(sala: Sala, mision: Mision, duracion_s: float):
    # Un registro por cada Player presente al completarse; el Wizard guía pero no suma
    for p in [x for x in sala.jugadores.values() if x.rol == "player"]:
        try:
            await guardar_mision(p, sala.id, duracion_s, mision.errores_por.get(p.usuario, 0))
        except Exception as e:
            log.warning("No se pudo guardar el progreso de %s: %s", p.usuario, e)


async def cliente(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    j = Jugador(writer)
    jugadores[j.id] = j
    log.info("Conexión nueva %s desde %s", j.id, j.ip)
    try:
        while True:
            linea = await reader.readline()
            if not linea:
                break
            try:
                m = json.loads(linea)
            except json.JSONDecodeError:
                # Se registra la línea recortada: así un cliente que arma mal el JSON
                # se diagnostica con servidor_logs.sh sin tener que capturar tráfico.
                log.warning("JSON inválido de %s (%s): %r", j.id, j.nombre, linea[:120].decode("utf-8", "replace"))
                await j.enviar({"t": "error", "msg": "JSON inválido"})
                continue
            try:
                await manejar(j, m)
            except Exception:
                log.exception("Error manejando %s", m)
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        await salir_de_sala(j)
        jugadores.pop(j.id, None)
        # Se libera el usuario para que pueda volver a entrar desde otra ventana
        if sesiones.get(j.usuario) is j:
            sesiones.pop(j.usuario)
        log.info("Desconectado %s (%s)", j.id, j.nombre)
        await registrar("desconexion", {"id": j.id, "usuario": j.usuario, "nombre": j.nombre})
        try:
            writer.close()
        except Exception:
            pass


async def main():
    await iniciar_bd()
    servidor = await asyncio.start_server(cliente, HOST, PUERTO)
    log.info("Servidor escuchando en %s:%d", HOST, PUERTO)
    async with servidor:
        await servidor.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
