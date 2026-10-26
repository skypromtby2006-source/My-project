"""
Servidor multijugador - Juego de Química (demo)
Protocolo: TCP, un mensaje JSON por línea (terminado en '\n').

Cliente -> servidor:
  {"t":"hola","nombre":"Ana"}
  {"t":"listar"}
  {"t":"crear_sala","nombre_sala":"Sala 1","maximo":4}
  {"t":"unirse","sala_id":"AB12"}
  {"t":"salir"}
  {"t":"listo","valor":true}
  {"t":"iniciar"}                      (solo el host)
  {"t":"pos","x":0,"y":0,"z":0,"ry":0}  (durante la partida)
  {"t":"ping"}

Servidor -> cliente:
  bienvenido, salas, sala, fuera, inicio, pos, salio, error, pong
"""
import asyncio
import json
import logging
import os
import random
import string
import uuid

HOST = "0.0.0.0"
PUERTO = int(os.getenv("PUERTO", "7777"))
DATABASE_URL = os.getenv("DATABASE_URL")  # si no existe, el servidor funciona sin BD

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("servidor")

db = None  # pool de asyncpg (opcional)


# ----------------------------------------------------------------- modelos
class Jugador:
    def __init__(self, writer: asyncio.StreamWriter):
        self.id = uuid.uuid4().hex[:8]
        self.nombre = "Jugador"
        self.writer = writer
        self.sala = None
        self.listo = False
        self.ip = (writer.get_extra_info("peername") or ("?",))[0]

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

    def info(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "host": self.host_id,
            "maximo": self.maximo,
            "cantidad": len(self.jugadores),
            "estado": self.estado,
            "jugadores": [
                {"id": j.id, "nombre": j.nombre, "listo": j.listo}
                for j in self.jugadores.values()
            ],
        }


salas: dict[str, Sala] = {}
jugadores: dict[str, Jugador] = {}


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
        log.info("Sin DATABASE_URL: se trabaja solo en memoria")
        return
    import asyncpg
    for intento in range(1, 11):
        try:
            db = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            async with db.acquire() as c:
                await c.execute("""
                    CREATE TABLE IF NOT EXISTS eventos (
                        id SERIAL PRIMARY KEY,
                        tipo TEXT NOT NULL,
                        detalle JSONB,
                        fecha TIMESTAMPTZ DEFAULT now()
                    )""")
            log.info("Conectado a PostgreSQL")
            return
        except Exception as e:
            log.warning("BD no disponible (intento %d/10): %s", intento, e)
            await asyncio.sleep(2)
    log.error("No se pudo conectar a la BD; se sigue sin persistencia")


async def registrar(tipo: str, detalle: dict):
    if db is None:
        return
    try:
        async with db.acquire() as c:
            await c.execute("INSERT INTO eventos (tipo, detalle) VALUES ($1, $2)",
                            tipo, json.dumps(detalle, ensure_ascii=False))
    except Exception as e:
        log.warning("No se pudo registrar evento: %s", e)


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
    if sala.host_id == j.id:  # el host se fue: pasa al siguiente
        sala.host_id = next(iter(sala.jugadores))
    await difundir(sala, {"t": "salio", "id": j.id})
    await difundir(sala, {"t": "sala", "sala": sala.info()})


async def entrar_a_sala(j: Jugador, sala: Sala):
    j.sala = sala
    j.listo = False
    sala.jugadores[j.id] = j
    await difundir(sala, {"t": "sala", "sala": sala.info()})


async def manejar(j: Jugador, m: dict):
    t = m.get("t")

    if t == "hola":
        nombre = str(m.get("nombre", "")).strip()[:20] or "Jugador"
        j.nombre = nombre
        await j.enviar({"t": "bienvenido", "id": j.id, "nombre": j.nombre})
        await registrar("conexion", {"id": j.id, "nombre": j.nombre, "ip": j.ip})

    elif t == "listar":
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
        if not all(x.listo for x in sala.jugadores.values() if x.id != sala.host_id):
            return await j.enviar({"t": "error", "msg": "Faltan jugadores por marcar 'Listo'"})
        sala.estado = "jugando"
        await difundir(sala, {"t": "inicio", "sala": sala.info()})
        log.info("Partida iniciada en %s", sala.id)
        await registrar("partida_iniciada", {"sala": sala.id, "jugadores": len(sala.jugadores)})

    elif t == "pos":
        if j.sala is None or j.sala.estado != "jugando":
            return
        datos = {"t": "pos", "id": j.id}
        for k in ("x", "y", "z", "ry"):
            datos[k] = float(m.get(k, 0))
        await difundir(j.sala, datos, excepto=j)

    elif t == "ping":
        await j.enviar({"t": "pong"})

    else:
        await j.enviar({"t": "error", "msg": f"Mensaje desconocido: {t}"})


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
        log.info("Desconectado %s (%s)", j.id, j.nombre)
        await registrar("desconexion", {"id": j.id, "nombre": j.nombre})
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
