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
import collections
import json
import logging
import math
import os
import random
import re
import string
import sys
import time
import uuid
from datetime import datetime, timezone

import nivel  # el nivel es un dato: carga, sorteo y validación del laberinto (S4)

HOST = "0.0.0.0"
PUERTO = int(os.getenv("PUERTO", "7777"))
DATABASE_URL = os.getenv("DATABASE_URL")  # si no existe, el servidor usa SQLite (quimica.db)
# Hook de pruebas: con NIVEL_SEMILLA puesto, todas las partidas sortean el nivel
# con esa semilla fija, así `probar_build.py` (y cualquier prueba) importa `nivel`
# y conoce las respuestas de los 5 puzzles. Vacío en producción: sorteo al azar.
SEMILLA_NIVEL = os.getenv("NIVEL_SEMILLA")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("servidor")

db = None  # repositorio.Repositorio (PostgreSQL o SQLite); None = solo memoria

# ----------------------------------------------------------------- perfiles
# La misma paleta está en ClienteRed.cs; el cliente solo la usa para dibujar
# los botones, la regla la impone el servidor.
PALETA = ["#3FA9F5", "#F5D33F", "#E04FD8", "#4FE07A", "#F5913F", "#E04F4F", "#FFFFFF", "#6A5AE0"]
FORMATO_USUARIO = re.compile(r"^[a-z0-9_]{4,16}$")
MISION_AGUA = "agua"
# Solo usuario, nombre visible y color: los usuarios son en su mayoría menores
# de edad, así que no se guarda nada más (minimización de datos).


class ErrorPerfil(Exception):
    """Petición de perfil rechazada; el mensaje se le muestra al jugador tal cual."""


def validar_usuario(m: dict) -> str:
    # Se pasa a minúsculas antes de validar para que "Jona" y "jona" no sean dos perfiles
    usuario = str(m.get("usuario", "")).strip().lower()
    if not FORMATO_USUARIO.match(usuario):
        # "guion bajo" en palabras: la fuente del juego no dibuja el carácter "_"
        raise ErrorPerfil("Usuario inválido: de 4 a 16 caracteres, solo letras, números y guion bajo")
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
# Sin BD, los eventos quedan aquí (los últimos 5000) para que el panel pueda
# mostrar los errores frecuentes de cada usuario también en el Plan B2.
eventos_mem: collections.deque = collections.deque(maxlen=5000)
INICIO = time.time()  # para el uptime del panel


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
        self.desde = time.time()  # hora de conexión, para el panel
        # Última posición conocida: si se desconecta llevando un objeto, ahí se cae
        self.x = self.y = self.z = 0.0

    @property
    def rol(self) -> str:
        # Se deriva del anfitrión en vez de guardarse aparte: así no hay dos datos
        # que sincronizar. El anfitrión no cambia nunca: si se va, la sala se cierra.
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
        self.mision: Mision | None = None      # modo legado "Sintetizar agua"
        self.partida: "Partida | None" = None  # modo laberinto (S4)

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
# Los jugadores aparecen en fila en z=-5 (ver apariciones); el reactor va en el suelo,
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


# ----------------------------------------------------------------- laberinto (S4)
class Partida:
    """Una partida del laberinto de las 5 puertas. El nivel y los números son la
    fuente de verdad (servidor/niveles/laberinto_01.json + nivel.py); el cliente
    solo manda intenciones y el servidor valida. Reemplaza a Mision como juego; la
    misión "Sintetizar agua" queda como modo legado hasta que el panel migre a
    "errores por concepto" (S4-5).

    Esta clase guarda estado y hace comprobaciones puras (sin I/O). Los efectos
    (registrar eventos, guardar progreso) los hace manejar_laberinto."""

    def __init__(self, rng=None):
        if rng is None and SEMILLA_NIVEL:
            rng = random.Random(int(SEMILLA_NIVEL))   # pruebas reproducibles
        self.datos = nivel.cargar()
        self.sorteo = nivel.sortear(rng)
        self.sala_idx = 0                       # 0..4
        self.valores: dict = {}                 # consola_id -> valor fijado
        self.activados: set = set()             # objetos activados (interactuar/montacargas)
        self.palancas: dict = {}                # "wizard"/"player" -> t_monotonic de la bajada
        self.errores = 0                        # del nivel entero
        self.errores_sala = 0                   # de la sala actual (para sala_completada)
        self.errores_por: dict = {}             # usuario -> errores (para el progreso)
        self.errores_por_concepto: dict = {}    # concepto -> veces (dato de S4-5)
        self.completada = False                 # nivel entero terminado
        self.mensaje = ""
        self.t_inicio = time.monotonic()
        self.t_sala = time.monotonic()
        # consola_id -> lado dueño: así el servidor rechaza que el Player toque una
        # consola del Wizard aunque un cliente modificado lo intente.
        self.lado_de_consola: dict = {}
        for s in self.datos["salas"]:
            for lado in ("wizard", "player"):
                for c in s["consolas"][lado]:
                    self.lado_de_consola[c["id"]] = lado

    @property
    def sala_num(self) -> int:
        return self.sala_idx + 1

    def sala_actual(self) -> dict:
        return self.datos["salas"][self.sala_idx]

    def consolas_de_sala(self) -> set:
        s = self.sala_actual()
        return {c["id"] for lado in ("wizard", "player") for c in s["consolas"][lado]}

    def visible(self) -> dict:
        """Lo que ve el cliente de la sala actual: el sorteo de la sala MENOS la
        respuesta correcta y lo que produce (eso no viaja nunca)."""
        s = {k: v for k, v in self.sorteo[self.sala_num].items() if k not in ("resp", "produce")}
        return s

    def inicio_info(self) -> dict:
        # Incluye el layout estático de las salas (ids y posiciones de consolas,
        # palancas, montacargas y puertas) para que el cliente construya el nivel
        # (SPRINT4 §3.1). NO lleva las respuestas: esas viven en `resp` del sorteo,
        # del lado del servidor. Los números visibles de la sala actual van en
        # sala_estado.datos.
        salas = [{k: v for k, v in s.items() if not str(k).startswith("_")}
                 for s in self.datos["salas"]]
        return {
            "nivel": self.datos["id"],
            "lados": self.datos["lados"],
            "ventana_palanca_s": self.datos.get("ventana_palanca_s", 2.0),
            "total_salas": len(self.datos["salas"]),
            "salas": salas,
            "sala": self.sala_estado(),
        }

    def sala_estado(self) -> dict:
        s = self.sala_actual()
        return {
            "sala": self.sala_num,
            "nombre": s["nombre"],
            "concepto": s["concepto"],
            "reaccion": s["reaccion"],
            "luz": s["luz"],
            "puerta": s["puerta"]["id"],
            "datos": self.visible(),
            "palancas": {lado: (lado in self.palancas) for lado in ("wizard", "player")},
            "mensaje": self.mensaje,
            "completada_nivel": self.completada,
        }

    def fijar(self, consola_id: str, valor):
        self.valores[consola_id] = valor

    def valor_ok(self, consola_id: str):
        """True/False si la consola es requerida y su valor coincide; None si no es
        una consola requerida de esta sala."""
        req = nivel.requeridos(self.sorteo, self.sala_num)
        if consola_id not in req:
            return None
        v = self.valores.get(consola_id)
        if v is None:
            return False
        esperado = req[consola_id]
        try:
            if isinstance(esperado, float):
                return abs(float(v) - esperado) < 1e-6
            return int(v) == esperado if isinstance(esperado, int) else v == esperado
        except (TypeError, ValueError):
            return False

    def partes_correctas(self) -> bool:
        """Los dos lados dejaron su parte: todas las consolas requeridas en su valor
        y todos los objetos a activar, activados."""
        req = nivel.requeridos(self.sorteo, self.sala_num)
        if any(self.valor_ok(cid) is not True for cid in req):
            return False
        return all(obj in self.activados for obj in nivel.activaciones(self.sala_num))

    def ambas_palancas(self) -> bool:
        """Las dos palancas bajadas con menos de la ventana (2 s) de diferencia."""
        tw, tp = self.palancas.get("wizard"), self.palancas.get("player")
        if tw is None or tp is None:
            return False
        return nivel.palanca_ok(tw, tp, self.datos.get("ventana_palanca_s", 2.0))


# Puntos de aparición: una fila centrada delante de la mesa, 2.5 m entre jugadores
# (con 8, de x=-8.75 a 8.75). Los decide el servidor para que cada uno tenga el suyo
# y todos los clientes coincidan.
APARICION_Z = -5.0
SEPARACION_APARICION = 2.5


def apariciones(sala: "Sala") -> list[dict]:
    n = len(sala.jugadores)
    return [{"id": jid, "x": round((i - (n - 1) / 2) * SEPARACION_APARICION, 2), "y": 1.0, "z": APARICION_Z}
            for i, jid in enumerate(sala.jugadores)]


def en_reactor(x: float, z: float) -> bool:
    # Solo cuenta la distancia horizontal: da igual a qué altura se suelte
    return math.hypot(x - REACTOR["x"], z - REACTOR["z"]) <= REACTOR["radio"]


MSG_WIZARD_SALIO = "El Wizard salió, la sala se cerró"

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
def ruta_sqlite() -> str:
    """Dónde va `quimica.db` del servidor local. SQLITE_RUTA la cambia (`:memory:` =
    SQLite en RAM, lo usa probar_build.py para no dejar archivos). Si no, va junto al
    ejecutable (PyInstaller) o junto a server.py: así el .exe guarda sus datos en su
    propia carpeta y no en la carpeta desde la que se lo abrió."""
    if os.getenv("SQLITE_RUTA"):
        return os.environ["SQLITE_RUTA"]
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    return os.path.join(base, "quimica.db")


async def iniciar_bd():
    """PostgreSQL si hay DATABASE_URL (servidor dedicado, Docker); si no, SQLite en un
    archivo (servidor local). Solo si los dos fallan, memoria. Todo el SQL está en
    repositorio.py y es el mismo para los dos motores."""
    global db
    import repositorio
    if DATABASE_URL:
        for intento in range(1, 11):
            try:
                db = await repositorio.abrir_postgres(DATABASE_URL)
                # Las tablas se crean aquí y no con un .sql en docker-entrypoint-initdb.d:
                # Postgres solo corre esos scripts con el volumen vacío, y datos_db ya
                # existe en las instalaciones anteriores.
                await db.crear_esquema()
                log.info("Conectado a PostgreSQL")
                return
            except Exception as e:
                log.warning("BD no disponible (intento %d/10): %s", intento, e)
                db = None
                await asyncio.sleep(2)
        log.error("No se pudo conectar a PostgreSQL; perfiles y progreso solo en memoria, se pierden al cerrar")
        return
    ruta = ruta_sqlite()
    try:
        db = repositorio.abrir_sqlite(ruta)
        await db.crear_esquema()
        log.info("Sin DATABASE_URL: datos en SQLite (%s)", ruta)
    except Exception as e:
        db = None
        log.error("No se pudo abrir SQLite en %s (%s); perfiles y progreso solo en memoria, "
                  "se pierden al cerrar el servidor", ruta, e)


async def registrar(tipo: str, detalle: dict):
    if db is None:
        eventos_mem.append({"tipo": tipo, "detalle": detalle, "fecha": datetime.now(timezone.utc)})
        return
    try:
        await db.registrar(tipo, detalle)
    except Exception as e:
        log.warning("No se pudo registrar evento: %s", e)


# Cada función tiene dos caminos (BD y memoria) para que el servidor siga funcionando
# aunque no haya ninguna BD, salvo por la persistencia. El SQL está en repositorio.py.
async def buscar_usuario(usuario: str) -> dict | None:
    if db is None:
        return usuarios_mem.get(usuario)
    return await db.buscar_usuario(usuario)


async def crear_usuario(usuario: str, nombre: str, color: str) -> dict | None:
    """Devuelve None si el usuario ya existe."""
    if db is None:
        if usuario in usuarios_mem:
            return None
        ahora = datetime.now(timezone.utc)
        usuarios_mem[usuario] = {"id": None, "usuario": usuario, "nombre": nombre, "color": color,
                                 "creado": ahora, "ultimo_login": ahora}
        return usuarios_mem[usuario]
    return await db.crear_usuario(usuario, nombre, color)


async def marcar_login(usuario: str):
    if db is None:
        usuarios_mem[usuario]["ultimo_login"] = datetime.now(timezone.utc)
    else:
        await db.marcar_login(usuario)


async def actualizar_usuario(usuario: str, nombre: str, color: str):
    if db is None:
        usuarios_mem[usuario].update(nombre=nombre, color=color)
    else:
        await db.actualizar_usuario(usuario, nombre, color)


async def guardar_mision(j: "Jugador", sala: str, duracion_s: float, errores: int, mision: str = MISION_AGUA):
    if db is None:
        misiones_mem.append({"usuario": j.usuario, "mision": mision, "sala": sala,
                             "duracion_s": duracion_s, "errores": errores,
                             "fecha": datetime.now(timezone.utc)})
        return
    await db.guardar_mision(j.usuario_id, mision, sala, duracion_s, errores)


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
        completadas, mejor, errores, historial = await db.progreso(j.usuario, j.usuario_id, MISION_AGUA)
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
            if datos.get("bloqueado"):
                # Lo bloqueó un admin desde el panel; el motivo se muestra en la ventana de perfil
                raise ErrorPerfil(f"Cuenta bloqueada: {datos.get('motivo_bloqueo') or 'sin motivo'}")
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
    # Regla del cliente (S2-3), reemplaza el traspaso de anfitrión del Sprint 1: el
    # Wizard es el único que ve la receta, así que sin él la misión no tiene guía.
    if sala.host_id == j.id:
        return await cerrar_sala(sala, MSG_WIZARD_SALIO)
    # Si sale un Player, los demás siguen jugando, incluso a mitad de la misión
    await difundir(sala, {"t": "salio", "id": j.id})
    await difundir(sala, {"t": "sala", "sala": sala.info()})
    if sala.mision is not None:
        o = sala.mision.objeto_de(j.id)
        if o is not None:  # si no se suelta, el objeto quedaría bloqueado para siempre
            o.portador = ""
            o.x, o.y, o.z = j.x, 0.15, j.z  # al suelo, donde estaba el jugador
            await difundir(sala, {"t": "obj", "obj": o.info()})


async def cerrar_sala(sala: Sala, motivo: str, por_admin: bool = False):
    salas.pop(sala.id, None)
    quedan = list(sala.jugadores.values())
    sala.jugadores.clear()
    for x in quedan:
        x.sala = None
        x.listo = False
    # "fuera" con msg: el cliente vuelve al lobby y muestra el motivo.
    # Si la cierra el admin va "sala_cerrada", para que el juego pueda distinguir
    # "el Wizard se fue" de "un administrador cerró la sala".
    aviso = {"t": "sala_cerrada", "motivo": motivo} if por_admin else {"t": "fuera", "msg": motivo}
    await asyncio.gather(*(x.enviar(aviso) for x in quedan))
    log.info("Sala %s cerrada: %s", sala.id, motivo)
    await registrar("sala_cerrada", {"sala": sala.id, "motivo": motivo, "expulsados": len(quedan)})


async def expulsar(j: Jugador, motivo: str):
    """Expulsión desde el panel: avisa al cliente y cierra su conexión.

    La limpieza (salir de la sala, liberar la sesión) la hace el finally de cliente()
    cuando el readline devuelve vacío, igual que en una desconexión normal: así no hay
    un segundo camino de limpieza que pueda quedar distinto.
    """
    log.warning("Jugador %s (%s) expulsado: %s", j.id, j.usuario or j.nombre, motivo)
    await j.enviar({"t": "expulsado", "motivo": motivo})
    await registrar("expulsado", {"id": j.id, "usuario": j.usuario, "motivo": motivo})
    try:
        j.writer.close()
    except Exception:
        pass


async def aviso_global(texto: str) -> int:
    """Mensaje del panel a todos los conectados (con o sin sesión). Devuelve a cuántos llegó."""
    conectados = list(jugadores.values())
    await asyncio.gather(*(j.enviar({"t": "aviso", "msg": texto}) for j in conectados))
    log.info("Aviso global a %d conexiones: %s", len(conectados), texto)
    await registrar("aviso", {"msg": texto, "conexiones": len(conectados)})
    return len(conectados)


async def cambiar_bloqueo(usuario: str, bloqueado: bool, motivo: str) -> bool:
    """Devuelve False si el usuario no existe. Si se bloquea y está conectado, se lo expulsa."""
    if db is None:
        if usuario not in usuarios_mem:
            return False
        usuarios_mem[usuario].update(bloqueado=bloqueado, motivo_bloqueo=motivo if bloqueado else None)
    elif not await db.fijar_bloqueo(usuario, bloqueado, motivo if bloqueado else None):
        return False
    log.warning("Usuario %s %s: %s", usuario, "bloqueado" if bloqueado else "desbloqueado", motivo)
    if bloqueado and usuario in sesiones:
        await expulsar(sesiones[usuario], f"Cuenta bloqueada: {motivo}")
    return True


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
            # Queda en el log: en la S2-3 no se pudo saber qué intentó la ventana que no entró
            log.info("Rechazado %s de %s (usuario %r): %s", t, j.id, m.get("usuario", j.usuario), e)
            await j.enviar({"t": "error", "msg": str(e)})
        except Exception:
            # Con la BD caída a mitad de la demo, el jugador recibe un aviso en vez de quedar esperando
            log.exception("Error de perfil en %s", t)
            await j.enviar({"t": "error", "msg": "No se pudo acceder a los perfiles; intenta de nuevo"})
        return

    # Un cliente de la v0.2 o anterior abre con hola y se quedaría esperando un bienvenido que ya no existe
    if t == "hola":
        return await j.enviar({"t": "error", "msg": "Versión del juego desactualizada, descarga la última"})

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
        puntos = apariciones(sala)
        for pt in puntos:  # posición inicial: si alguien se va antes de moverse, lo que lleve cae ahí
            x = sala.jugadores[pt["id"]]
            x.x, x.y, x.z = pt["x"], pt["y"], pt["z"]
        # "agua" (legado, misión Sintetizar agua) | "laberinto" (juego nuevo del Sprint 4).
        # Por ahora el default es "agua" para no cambiar al cliente ya desplegado ni al
        # panel; el cliente de primera persona (S4-2) pedirá modo "laberinto". El retiro
        # definitivo del agua va con la migración del panel a "errores por concepto" (S4-5).
        modo = str(m.get("modo", "agua"))
        if modo == "laberinto":
            sala.mision = None
            sala.partida = Partida()
            await difundir(sala, {"t": "inicio", "sala": sala.info(),
                                  "nivel": sala.partida.inicio_info(), "apariciones": puntos})
        else:
            sala.partida = None
            sala.mision = Mision()
            await difundir(sala, {"t": "inicio", "sala": sala.info(),
                                  "mision": sala.mision.info(), "apariciones": puntos})
        log.info("Partida iniciada en %s (modo %s)", sala.id, modo)
        await registrar("partida_iniciada", {"sala": sala.id, "jugadores": len(sala.jugadores), "modo": modo})

    elif t == "pos":
        if j.sala is None or j.sala.estado != "jugando":
            return
        datos = {"t": "pos", "id": j.id}
        # pitch (inclinación de la cabeza) se agrega en S4 para ver hacia dónde mira
        # el otro jugador en primera persona; los clientes viejos no lo mandan (0).
        for k in ("x", "y", "z", "ry", "pitch"):
            datos[k] = float(m.get(k, 0))
        j.x, j.y, j.z = datos["x"], datos["y"], datos["z"]
        await difundir(j.sala, datos, excepto=j)

    elif t in ("agarrar", "soltar", "senalar", "reiniciar"):
        await manejar_mision(j, t, m)

    elif t in ("dial", "interactuar", "montacargas", "palanca"):
        await manejar_laberinto(j, t, m)

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
        errores = mision.errores_por.get(p.usuario, 0)
        try:
            await guardar_mision(p, sala.id, duracion_s, errores)
            # Así servidor_logs.sh responde "¿se guardó?" sin abrir la BD
            log.info("Progreso guardado: %s en %s (%.1f s, %d errores)", p.usuario, sala.id, duracion_s, errores)
        except Exception as e:
            log.warning("No se pudo guardar el progreso de %s: %s", p.usuario, e)


async def manejar_laberinto(j: Jugador, t: str, m: dict):
    sala = j.sala
    if sala is None or sala.estado != "jugando" or sala.partida is None:
        return await j.enviar({"t": "error", "msg": "No hay una partida de laberinto en curso"})
    p = sala.partida
    if p.completada:
        return await j.enviar({"t": "error", "msg": "El nivel ya está completo"})
    lado = j.rol  # "wizard" (anfitrión) o "player"

    if t == "dial":
        cid = str(m.get("consola", ""))
        if cid not in p.consolas_de_sala():
            return await j.enviar({"t": "error", "msg": "Esa consola no es de esta sala"})
        if p.lado_de_consola.get(cid) != lado:
            return await j.enviar({"t": "error", "msg": "Esa consola no es de tu lado"})
        p.fijar(cid, m.get("valor"))
        # Cada valor mal puesto en una consola requerida es un error de estequiometría:
        # es el dato de "errores por concepto" que analiza el panel (S4-5).
        if p.valor_ok(cid) is False:
            await registrar_error_estq(p, j, cid)
        else:
            p.mensaje = ""

    elif t == "interactuar":
        obj = str(m.get("obj", ""))
        p.activados.add(obj)
        p.mensaje = f"{obj}: {str(m.get('accion', 'usar'))[:20]}"

    elif t == "montacargas":
        # Pasa el producto al otro lado / a la sala siguiente. En greybox es un
        # marcador; el encadenamiento numérico lo valida el servidor con el sorteo.
        p.activados.add(f"mont_{p.sala_num}")
        p.mensaje = "Objeto enviado por el montacargas"

    elif t == "palanca":
        p.palancas[lado] = time.monotonic()
        if p.ambas_palancas() and p.partes_correctas():
            await completar_sala(p, sala)
        elif p.palancas.get("wizard") and p.palancas.get("player") and not p.ambas_palancas():
            p.mensaje = "Las palancas no bajaron a la vez (menos de 2 s)"
        elif not p.partes_correctas():
            p.mensaje = "Falta la parte correcta de algún lado"

    await difundir(sala, {"t": "sala_estado", **p.sala_estado()})


async def registrar_error_estq(p: Partida, j: Jugador, consola_id: str):
    concepto = p.sorteo[p.sala_num]["concepto"]
    esperado = nivel.requeridos(p.sorteo, p.sala_num)[consola_id]
    recibido = p.valores.get(consola_id)
    p.errores += 1
    p.errores_sala += 1
    p.errores_por[j.usuario] = p.errores_por.get(j.usuario, 0) + 1
    p.errores_por_concepto[concepto] = p.errores_por_concepto.get(concepto, 0) + 1
    p.mensaje = f"{concepto}: valor incorrecto"
    await registrar("error_estequiometria", {
        "sala": p.sala_num, "concepto": concepto,
        "esperado": esperado, "recibido": recibido, "usuario": j.usuario})


async def completar_sala(p: Partida, sala: Sala):
    seg = round(time.monotonic() - p.t_sala, 1)
    await registrar("sala_completada", {"sala": p.sala_num, "segundos": seg, "errores": p.errores_sala})
    log.info("Sala %d completada en %s (%.1f s, %d errores)", p.sala_num, sala.id, seg, p.errores_sala)
    if p.sala_num >= len(p.datos["salas"]):
        p.completada = True
        p.mensaje = "¡Nivel completado!"
        await registrar("nivel_completado", {
            "sala": sala.id, "segundos": round(time.monotonic() - p.t_inicio, 1), "errores": p.errores})
        await guardar_nivel(sala, p)
    else:
        p.mensaje = f"Sala {p.sala_num} completada"
        p.sala_idx += 1
        p.errores_sala = 0
        p.palancas.clear()
        p.t_sala = time.monotonic()


async def guardar_nivel(sala: Sala, p: Partida):
    # Un registro por cada Player presente al terminar el nivel; el Wizard guía.
    duracion = round(time.monotonic() - p.t_inicio, 1)
    for jug in [x for x in sala.jugadores.values() if x.rol == "player"]:
        errores = p.errores_por.get(jug.usuario, 0)
        try:
            await guardar_mision(jug, sala.id, duracion, errores, mision="laberinto")
            log.info("Nivel guardado: %s en %s (%.1f s, %d errores)", jug.usuario, sala.id, duracion, errores)
        except Exception as e:
            log.warning("No se pudo guardar el nivel de %s: %s", jug.usuario, e)


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
            except (UnicodeDecodeError, ValueError):
                # No es texto JSON: suele ser un navegador o un escáner de puertos que
                # pega en el puerto del juego. No se puede responder nada útil, así que
                # se corta la conexión en vez de seguir leyendo basura binaria.
                log.warning("Datos no válidos desde %s (¿navegador o escáner en el puerto del juego?)", j.ip)
                break
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


async def iniciar_panel() -> list:
    """Arranca el panel web en el mismo event loop. Devuelve las tareas a esperar.

    Va en el mismo proceso que el juego porque el panel necesita tocar salas y
    jugadores en memoria (ver MDs/SPRINT3.md §2.1). Si algo falla aquí, el juego
    sigue funcionando igual: el panel es un extra y no puede tumbar la partida.
    """
    try:
        import registro_logs
        registro = registro_logs.registro
        import auth
        auth.cargar_env()
        autenticador = auth.Autenticador.desde_entorno()
        if autenticador is None:
            return []
        import admin_api
        import uvicorn
    except ImportError as e:
        log.warning("Panel web DESHABILITADO: falta una dependencia (%s). "
                    "Instala servidor/requirements.txt para usarlo", e)
        return []
    if db is not None:
        await registro.conectar_bd(db)
    app = admin_api.crear_app(sys.modules[__name__], autenticador, registro)
    puerto = int(os.getenv("PUERTO_PANEL", "8000"))
    # access_log apagado: cada pedido del panel llenaría el log que el propio panel muestra
    config = uvicorn.Config(app, host=HOST, port=puerto, log_level="warning", access_log=False)
    servidor_web = uvicorn.Server(config)

    async def correr():
        try:
            await servidor_web.serve()
        except (SystemExit, Exception) as e:
            # uvicorn hace sys.exit(1) si el puerto está ocupado: se atrapa para que
            # el servidor del juego no se cierre con él.
            log.error("El panel web no pudo arrancar en el puerto %d (%r); el juego sigue funcionando", puerto, e)
            await asyncio.Event().wait()  # no se termina: si no, main() cerraría el juego
    log.info("Panel web en http://%s:%d", HOST, puerto)
    return [asyncio.create_task(correr()), asyncio.create_task(registro.guardar_en_lotes())]


async def main():
    try:
        # Se engancha antes de conectar a la BD para que el panel también muestre los logs del arranque
        import registro_logs
        registro_logs.instalar()
    except ImportError:
        pass
    await iniciar_bd()
    servidor = await asyncio.start_server(cliente, HOST, PUERTO)
    log.info("Servidor escuchando en %s:%d", HOST, PUERTO)
    tareas = await iniciar_panel()
    async with servidor:
        juego = asyncio.create_task(servidor.serve_forever())
        # Si uvicorn termina (Ctrl+C o SIGTERM de docker stop: él atrapa la señal),
        # se cierra también el juego.
        hechas, _ = await asyncio.wait([juego, *tareas], return_when=asyncio.FIRST_COMPLETED)
        for t in [juego, *tareas]:
            t.cancel()


if __name__ == "__main__":
    asyncio.run(main())
