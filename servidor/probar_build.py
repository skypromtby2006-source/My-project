"""
Prueba con el build REAL de Linux (sin ventana) contra el servidor de Docker.
Por qué existe: probar_cliente.py y probar_perfiles.py hablan directo con el servidor,
así que no ven lo que pasa en MenuLobby y GestorPartida, que es justo donde fallaba
la prueba S2-3 aunque esos tests dieran TODO OK. Aquí cada "jugador Unity" es el
ejecutable de Build/Linux en -batchmode, manejado por PruebaAutomatica.cs (los mismos
métodos que los botones), y los demás jugadores son bots.
Uso:  python probar_build.py [escenario ...]   (sin argumentos: todos)
Escenarios:
  laberinto, laberinto_player  el juego nuevo (S4). Levantan su PROPIO servidor con
      semilla fija (NIVEL_SEMILLA, puerto 7788, en memoria): conocen las respuestas de
      los puzzles y no necesitan Docker. "laberinto" incluye el door-cross físico.
  sesion, reinicio             usan el servidor de Docker; "reinicio" lo reinicia.
  panel                        acciones del panel web: necesita ADMIN_PASSWORD en el .env.
La cobertura de los viejos "wizard"/"player"/"progreso" (misión agua) migró a los dos
escenarios de laberinto, porque el cliente ahora siempre inicia en modo laberinto.
"""
import asyncio
import json
import math
import os
import pathlib
import queue
import random
import subprocess
import sys
import tempfile
import threading
import urllib.request
import uuid

RAIZ = pathlib.Path(__file__).resolve().parent.parent
JUEGO = RAIZ / "Build" / "Linux" / "QuimicaDemo.x86_64"
IP, PUERTO = "127.0.0.1", 7777
PUERTO_LAB, PUERTO_PANEL_LAB = 7788, 8008   # servidor propio del escenario laberinto
SEMILLA_LAB = 123                            # debe coincidir con el NIVEL_SEMILLA del servidor
SENALES = pathlib.Path(tempfile.mkdtemp(prefix="quimica_prueba_"))
MSG_WIZARD_SALIO = "El Wizard salió, la sala se cerró"

# El nivel es un dato (nivel.py): con la misma semilla que el servidor, el
# orquestador conoce las respuestas de los 5 puzzles sin mirar el estado interno.
sys.path.insert(0, str(RAIZ / "servidor"))
import nivel  # noqa: E402

_DATOS_NIVEL = nivel.cargar()
_SORTEO_LAB = nivel.sortear(random.Random(SEMILLA_LAB))


def _lado_de(cid):
    for sala in _DATOS_NIVEL["salas"]:
        for lado in ("wizard", "player"):
            if any(c["id"] == cid for c in sala["consolas"][lado]):
                return lado
    return None


def requeridos_por_lado(num):
    """Las consolas requeridas de la sala `num`, separadas por lado: el Wizard (build)
    resuelve su parte y el Player (bot) la suya."""
    req = nivel.requeridos(_SORTEO_LAB, num)
    w = {k: v for k, v in req.items() if _lado_de(k) == "wizard"}
    p = {k: v for k, v in req.items() if _lado_de(k) == "player"}
    return w, p

fallos: list[str] = []
escenario_actual = ""
builds: list["Build"] = []


def comprobar(condicion, que, dato=None):
    # No se corta en el primer fallo: así una corrida muestra todos los síntomas
    print(("  ✔ " if condicion else "  ✘ ") + que + ("" if condicion or dato is None else f"  → {dato}"))
    if not condicion:
        fallos.append(f"[{escenario_actual}] {que}")


def senal(nombre, contenido=""):
    (SENALES / nombre).write_text(contenido)


def cerca(x1, z1, x2, z2):
    return math.hypot(x1 - x2, z1 - z2) < 0.05


class ServidorLocal:
    """El servidor del juego en un proceso propio, con semilla fija (NIVEL_SEMILLA) y
    BD en memoria. El escenario del laberinto lo usa en vez del servidor de Docker:
    así el orquestador conoce las respuestas (semilla) y puede reiniciarlo para la
    prueba B4 sin depender de Docker. Usa un puerto propio (PUERTO_LAB) para no chocar
    con un servidor de Docker que esté levantado."""

    def __init__(self):
        self.proc = None

    def _python(self):
        venv = RAIZ / ".venv" / "bin" / "python"
        return str(venv) if venv.exists() else sys.executable

    async def arrancar(self):
        env = dict(os.environ)
        env["NIVEL_SEMILLA"] = str(SEMILLA_LAB)
        env["PUERTO"] = str(PUERTO_LAB)
        env["PUERTO_PANEL"] = str(PUERTO_PANEL_LAB)
        env.pop("DATABASE_URL", None)   # en memoria: no toca la BD de nadie
        self.proc = subprocess.Popen([self._python(), str(RAIZ / "servidor" / "server.py")],
                                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                _, w = await asyncio.open_connection(IP, PUERTO_LAB)
                w.close()
                return
            except OSError:
                await asyncio.sleep(0.25)
        raise TimeoutError("el servidor local del laberinto no arrancó en 20 s")

    async def reiniciar(self):
        self.detener()
        await asyncio.sleep(0.5)
        await self.arrancar()

    def detener(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class Build:
    """Una instancia del juego. Los pasos son los de PruebaAutomatica.cs."""

    def __init__(self, nombre, pasos):
        self.nombre = nombre
        self.cola = queue.Queue()
        self.log = open(RAIZ / "logs" / f"prueba_{nombre}.log", "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [str(JUEGO), "-batchmode", "-nographics", "-logFile", "-", "-prueba", ";".join(pasos),
             "-ip", IP, "-puerto", str(PUERTO), "-senales", str(SENALES)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        threading.Thread(target=self._leer, daemon=True).start()
        builds.append(self)

    def _leer(self):
        for linea in self.proc.stdout:
            self.log.write(linea)
            self.log.flush()
            if linea.startswith("[Prueba] "):
                self.cola.put(linea[len("[Prueba] "):].rstrip("\n"))
        self.cola.put(None)

    async def esperar(self, clave, timeout=60):
        """Espera "REPORTE <etiqueta>" (devuelve el estado), "MARCA <texto>" o "FIN"."""
        while True:
            try:
                linea = await asyncio.to_thread(self.cola.get, True, timeout)
            except queue.Empty:
                raise TimeoutError(f"{self.nombre}: no llegó '{clave}'")
            if linea is None:
                raise RuntimeError(f"{self.nombre}: el juego terminó antes de '{clave}' (logs/prueba_{self.nombre}.log)")
            if linea.startswith("FALLO"):
                raise RuntimeError(f"{self.nombre}: {linea}")
            if linea.startswith("PASO"):
                continue
            print(f"  [{self.nombre}] {linea[:160]}")
            if linea.startswith(clave):
                resto = linea[len(clave):].strip()
                return json.loads(resto) if clave.startswith("REPORTE") else resto

    async def terminar(self, timeout=30):
        return await asyncio.to_thread(self.proc.wait, timeout)


class Bot:
    """Jugador simulado que habla directo con el servidor."""

    @classmethod
    async def nuevo(cls, usuario, nombre, color="#F5D33F"):
        b = cls()
        b.nombre = nombre
        b.r, b.w = await asyncio.open_connection(IP, PUERTO)
        await b.env(t="registro", usuario=usuario, nombre=nombre, color=color)
        b.id = (await b.rec("perfil"))["id"]
        return b

    async def env(self, **m):
        self.w.write((json.dumps(m) + "\n").encode())
        await self.w.drain()

    async def rec(self, tipo, timeout=20):
        while True:
            linea = await asyncio.wait_for(self.r.readline(), timeout)
            if not linea:
                raise ConnectionError(f"{self.nombre}: el servidor cerró la conexión")
            m = json.loads(linea)
            if m["t"] != "pos":  # el build manda pos 15 veces por segundo
                print(f"  [{self.nombre}] <- {json.dumps(m, ensure_ascii=False)[:120]}")
            if m["t"] == tipo:
                return m

    async def crear_sala(self, archivo_codigo):
        await self.env(t="crear_sala", nombre_sala=f"Sala de {self.nombre}")
        sala = (await self.rec("sala"))["sala"]
        senal(archivo_codigo, sala["id"])
        return sala["id"]

    async def esperar_sala_lista(self):
        # Hasta que haya alguien más y todos los que no son el host estén listos
        while True:
            sala = (await self.rec("sala"))["sala"]
            if sala["cantidad"] >= 2 and all(j["listo"] or j["id"] == sala["host"] for j in sala["jugadores"]):
                return sala

    async def unirse_a(self, nombre_host):
        for _ in range(40):
            await self.env(t="listar")
            for s in (await self.rec("salas"))["lista"]:
                if any(j["nombre"] == nombre_host and j["rol"] == "wizard" for j in s["jugadores"]):
                    await self.env(t="unirse", sala_id=s["id"])
                    await self.rec("sala")
                    await self.env(t="listo", valor=True)
                    return s["id"]
            await asyncio.sleep(0.5)
        raise TimeoutError(f"{self.nombre}: no apareció la sala de {nombre_host}")

    # ---- laberinto (S4): el bot es el otro jugador y resuelve SU lado ----
    async def entrar_laberinto(self, nombre_host):
        """Se une a la sala del Wizard (build), marca listo y recibe el inicio del
        laberinto. El build inicia la partida; el bot espera el `inicio`."""
        await self.unirse_a(nombre_host)
        self.inicio = await self.rec("inicio")
        return self.inicio

    async def dial(self, cid, valor):
        await self.env(t="dial", consola=cid, valor=valor)
        await self.rec("sala_estado")

    async def palanca(self):
        await self.env(t="palanca", puerta="x")
        await self.rec("sala_estado")

    def cerrar(self):
        self.w.close()


async def escenario_sesion(s):
    """B4: sesión única con ventanas reales, y que el usuario se libere al cerrar."""
    u = f"u_{s}"
    a = Build("sesion_a", ["conectar", "registro|abc|Corto|#6A5AE0", "esperar_aviso|de 4 a 16",  # B7
                           f"registro|{u}|U{s}|#6A5AE0", "esperar_pantalla|Salas", "marca|logueado",
                           "esperar_senal|cerrar_a", "fin"])
    await a.esperar("MARCA logueado")
    b = Build("sesion_b", ["conectar", f"login|{u}", "esperar|2", "reporte|rechazo",
                           "esperar_senal|a_cerrado", f"login|{u}", "esperar_pantalla|Salas", "reporte|entro",
                           "desconectar", "marca|desconectado", "esperar_senal|c_listo", "fin"])
    r = await b.esperar("REPORTE rechazo")
    comprobar(r["pantalla"] == "Perfil" and "sesión abierta" in (r["aviso"] or ""),
              "una segunda ventana con el mismo usuario se rechaza", r)
    print("Se cierra la primera ventana: el usuario se libera")
    senal("cerrar_a")
    comprobar(await a.terminar() == 0, "la primera ventana se cerró")
    senal("a_cerrado")
    r = await b.esperar("REPORTE entro")
    comprobar(r["pantalla"] == "Salas" and r["usuario"] == u, "la segunda ventana entra tras cerrar la primera", r)
    await b.esperar("MARCA desconectado")
    print("Botón Desconectar y una tercera ventana entra; luego se mata a la fuerza")
    c = Build("sesion_c", ["conectar", f"login|{u}", "esperar_pantalla|Salas", "reporte|entro", "esperar|60"])
    r = await c.esperar("REPORTE entro")
    comprobar(r["pantalla"] == "Salas", "tras Desconectar, otra ventana entra con ese usuario", r)
    senal("c_listo")
    c.proc.kill()  # como si el juego se colgara y se cerrara a la fuerza
    await c.terminar()
    d = Build("sesion_d", ["conectar", f"login|{u}", "esperar_pantalla|Salas", "reporte|entro", "fin"])
    r = await d.esperar("REPORTE entro")
    comprobar(r["pantalla"] == "Salas", "tras matar el proceso, el usuario se libera", r)
    await d.esperar("FIN")
    await b.esperar("FIN")


async def reiniciar_servidor():
    # Lo mismo que hace Jona en la S2-3
    for script in ("servidor_detener.sh", "servidor_iniciar.sh"):
        await asyncio.to_thread(subprocess.run, [str(RAIZ / "scripts" / script)], check=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        logs = await asyncio.to_thread(subprocess.run, ["docker", "compose", "logs", "servidor"],
                                       cwd=RAIZ, capture_output=True, text=True)
        if "Servidor escuchando" in logs.stdout:
            return
        await asyncio.sleep(1)
    raise TimeoutError("el servidor no volvió a arrancar")


async def escenario_reinicio(s):
    """B4: conectar y entrar apenas termina servidor_iniciar.sh, como lo haría una persona."""
    u = f"r_{s}"
    p = Build("reinicio", ["conectar", f"registro|{u}|R{s}|#FFFFFF", "esperar_pantalla|Salas", "marca|reiniciar",
                           "esperar_pantalla|Conexion", "esperar_senal|iniciar_termino",
                           "conectar", "esperar|0.5", f"login|{u}", "esperar|3", "reporte|tras_login", "fin"])
    await p.esperar("MARCA reiniciar")
    for script in ("servidor_detener.sh", "servidor_iniciar.sh"):  # sin esperar el log del servidor
        await asyncio.to_thread(subprocess.run, [str(RAIZ / "scripts" / script)], check=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    senal("iniciar_termino")
    r = await p.esperar("REPORTE tras_login", timeout=90)
    comprobar(r["pantalla"] == "Salas" and r["usuario"] == u,
              "B4: se puede entrar apenas termina servidor_iniciar.sh", r)
    await p.esperar("FIN")
    await reiniciar_servidor()  # deja el servidor escuchando para el siguiente escenario


async def escenario_laberinto(s):
    """Laberinto (S4), con el Wizard en el build y el Player como bot, contra un
    servidor propio con semilla fija:
      - Door-cross FÍSICO: una puerta cerrada bloquea de verdad; al completarse la
        sala, la misma puerta abre y deja pasar (regla del juego, no arte).
      - B1: dos partidas seguidas sin cerrar la ventana; en cada una el Wizard ve al
        Player y, al volver al lobby, no queda la escena vieja.
      - B2: el Player sale a mitad y el Wizard sigue en la partida.
      - B4: reconexión después de reiniciar el servidor.
    """
    global PUERTO
    orig_puerto = PUERTO
    PUERTO = PUERTO_LAB
    srv = ServidorLocal()
    w = f"wl_{s}"
    reqw, reqp = requeridos_por_lado(1)       # sala 1 (balanceo): dial_h2 / dial_o2
    h2, o2 = reqw["dial_h2"], reqp["dial_o2"]
    # Colocamos al jugador al ESTE de la puerta D1 (col 6, fila 2 = x 12, z -4) y lo
    # empujamos al OESTE contra D1 (centro x 8): ese tramo no tiene marcadores.
    ESTE_DE_D1, EMPUJE_OESTE = "colocar|12|1.1|-4", "empujar|-1|0|2.5"

    def partida(nombre):
        return ["crear_sala", f"marca|{nombre}", "esperar_jugadores|2", "esperar_listos", "iniciar",
                "esperar_pantalla|Partida", "esperar_escena", "esperar|0.5"]

    try:
        await srv.arrancar()
        build = Build("laberinto", [
            "conectar", f"registro|{w}|WLab{s}|#3FA9F5", "esperar_pantalla|Salas",
            *partida("p1"), "reporte|p1_inicio",
            ESTE_DE_D1, EMPUJE_OESTE, "esperar|0.2", "reporte|dc_cerrada",
            f"dial|dial_h2|{h2}", "marca|s1_wiz_listo", "esperar_senal|s1_baja", "palanca|D1",
            "esperar_sala|2", "reporte|sala2",
            ESTE_DE_D1, EMPUJE_OESTE, "esperar|0.2", "reporte|dc_abierta",
            "esperar_senal|player_fuera", "esperar|1", "reporte|tras_player",
            "salir", "esperar_pantalla|Salas", "esperar|0.3", "reporte|lobby1",
            *partida("p2"), "reporte|p2_inicio", "salir", "esperar_pantalla|Salas",
            "marca|reiniciar", "esperar_pantalla|Conexion", "esperar_senal|servidor_ok",
            "conectar", "esperar_pantalla|Perfil", f"registro|{w}b|WLab2{s}|#3FA9F5",
            "esperar_pantalla|Salas", "reporte|reconectado", "fin"])

        # ---- Partida 1 ----
        await build.esperar("MARCA p1")
        bot = await Bot.nuevo(f"bl1_{s}", f"BL1{s}", "#4FE07A")
        await bot.entrar_laberinto(f"WLab{s}")
        r = await build.esperar("REPORTE p1_inicio")
        comprobar(r["escena"] and r["sala_lab"] == 1, "laberinto: el Wizard entra a la sala 1", r)
        remoto = next((x for x in r["remotos"] if x["id"] == bot.id), None)
        comprobar(remoto is not None, "B1: el Wizard ve la cápsula del Player", r["remotos"])

        r = await build.esperar("REPORTE dc_cerrada")
        comprobar(r["local_x"] > 9.0, "la puerta CERRADA bloquea: el Wizard no la cruza", r["local_x"])
        comprobar(r["local_x"] < 11.9, "y el empuje sí lo movió hacia la puerta (no quedó quieto)", r["local_x"])

        # Resolver la sala 1: el bot fija su dial y las dos palancas bajan casi a la vez
        await build.esperar("MARCA s1_wiz_listo")
        await bot.dial("dial_o2", o2)
        senal("s1_baja")           # el build baja su palanca enseguida
        await bot.palanca()        # y el bot la suya (< 2 s)
        r = await build.esperar("REPORTE sala2")
        comprobar(r["sala_lab"] == 2, "con las dos partes y las dos palancas, la sala 1 se completa", r["sala_lab"])

        r = await build.esperar("REPORTE dc_abierta")
        comprobar(r["local_x"] < 8.0, "la puerta ABIERTA deja pasar: el Wizard la cruza", r["local_x"])

        # ---- B2: el Player sale, el Wizard sigue ----
        await bot.env(t="salir")
        await bot.rec("fuera")
        senal("player_fuera")
        r = await build.esperar("REPORTE tras_player")
        comprobar(r["pantalla"] == "Partida", "B2: si sale el Player, el Wizard sigue jugando", r["pantalla"])
        comprobar(r["remotos"] == [], "y el Player que salió ya no se dibuja", r["remotos"])
        r = await build.esperar("REPORTE lobby1")
        comprobar(r["pantalla"] == "Salas" and not r["escena"], "B1: al volver al lobby no queda la escena vieja", r)
        bot.cerrar()

        # ---- Partida 2 (sin cerrar la ventana) ----
        await build.esperar("MARCA p2")
        bot2 = await Bot.nuevo(f"bl2_{s}", f"BL2{s}", "#E04FD8")
        await bot2.entrar_laberinto(f"WLab{s}")
        r = await build.esperar("REPORTE p2_inicio")
        comprobar(r["escena"] and r["sala_lab"] == 1, "B1: segunda partida seguida, escena nueva de la sala 1", r)
        comprobar(any(x["id"] == bot2.id for x in r["remotos"]), "B1: el Wizard ve al nuevo Player", r["remotos"])
        bot2.cerrar()

        # ---- B4: reinicio del servidor ----
        await build.esperar("MARCA reiniciar")
        await srv.reiniciar()
        senal("servidor_ok")
        r = await build.esperar("REPORTE reconectado", timeout=90)
        comprobar(r["pantalla"] == "Salas", "B4: el Wizard reconecta tras reiniciar el servidor", r)
        await build.esperar("FIN")
    finally:
        srv.detener()
        PUERTO = orig_puerto


async def escenario_laberinto_player(s):
    """Laberinto (S4) con el Player en el build y el Wizard como bot: B1 (el Player ve
    al Wizard) y B2 (sale el Wizard y la sala se cierra para el Player)."""
    global PUERTO
    orig_puerto = PUERTO
    PUERTO = PUERTO_LAB
    srv = ServidorLocal()
    try:
        await srv.arrancar()
        build = Build("laberinto_p", [
            "conectar", f"registro|pl_{s}|PLab{s}|#4FE07A", "esperar_pantalla|Salas",
            "unirse_codigo|codlab", "esperar_pantalla|Sala", "listo", "esperar_pantalla|Partida",
            "esperar_escena", "esperar|0.5", "reporte|inicio",
            "esperar_senal|wiz_fuera", "esperar|1.5", "reporte|tras_wiz", "fin"])
        wiz = await Bot.nuevo(f"zl_{s}", f"ZL{s}", "#E04FD8")
        await wiz.crear_sala("codlab")
        await wiz.esperar_sala_lista()
        await wiz.env(t="iniciar", modo="laberinto")
        await wiz.rec("inicio")
        await wiz.env(t="pos", x=-2.0, y=1, z=2.0, ry=0)
        r = await build.esperar("REPORTE inicio")
        comprobar(r["escena"] and r["sala_lab"] == 1, "laberinto: el Player entra a la sala 1", r)
        remoto = next((x for x in r["remotos"] if x["id"] == wiz.id), None)
        comprobar(remoto is not None, "B1: el Player ve la cápsula del Wizard", r["remotos"])

        await wiz.env(t="salir")
        await wiz.rec("fuera")
        senal("wiz_fuera")
        r = await build.esperar("REPORTE tras_wiz")
        comprobar(r["pantalla"] == "Salas", "B2: si sale el Wizard, el Player vuelve al lobby", r["pantalla"])
        comprobar(MSG_WIZARD_SALIO in (r["aviso"] or ""), "B2: el Player ve el aviso de sala cerrada", r["aviso"])
        comprobar(not r["escena"], "B1: no queda la escena de la partida vieja", r)
        await build.esperar("FIN")
        wiz.cerrar()
    finally:
        srv.detener()
        PUERTO = orig_puerto


def panel(ruta, datos=None, token=None):
    """Llama a la API del panel web (solo biblioteca estándar, como el resto del script)."""
    pedido = urllib.request.Request(f"http://{IP}:8000/api{ruta}", method="POST" if datos is not None else "GET",
                                    data=json.dumps(datos).encode() if datos is not None else None,
                                    headers={"Content-Type": "application/json",
                                             **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(pedido, timeout=10) as r:
        return json.loads(r.read())


def clave_admin():
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if linea.startswith("ADMIN_PASSWORD="):
            return linea.split("=", 1)[1].strip()
    raise RuntimeError("falta ADMIN_PASSWORD en el .env")


async def escenario_panel(s):
    """S3-4: el juego real reacciona a las acciones del panel: aviso global, cierre de sala,
    expulsión y cuenta bloqueada, mostrando siempre el texto que mandó el admin."""
    u = f"pp_{s}"  # prefijos propios: "progreso" ya usa p_ y w_ en la misma corrida
    p = Build("panel_p", ["conectar", f"registro|{u}|Pepa|#4FE07A", "esperar_pantalla|Salas",
                          "unirse_codigo|codigo_panel", "listo", "esperar_pantalla|Partida", "marca|jugando",
                          "esperar_aviso_global|Hola desde el panel", "reporte|aviso",
                          "esperar_aviso|Fin de la clase", "reporte|cerrada",
                          "esperar_aviso|Prueba automática", "reporte|expulsado",
                          "esperar_senal|bloqueado", "conectar", f"login|{u}", "esperar_aviso|Cuenta bloqueada",
                          "reporte|bloqueado", "fin"])
    w = await Bot.nuevo(f"pw_{s}", "Wiz")
    try:
        sala = await w.crear_sala("codigo_panel")
        await w.esperar_sala_lista()
        await w.env(t="iniciar")
        await p.esperar("MARCA jugando")
        datos = {"usuario": "admin", "contrasena": clave_admin()}
        token = (await asyncio.to_thread(panel, "/login", datos))["token"]
        print("El admin manda un aviso global en plena partida")
        await asyncio.to_thread(panel, "/aviso", {"mensaje": "Hola desde el panel"}, token)
        r = await p.esperar("REPORTE aviso")
        comprobar(r["pantalla"] == "Partida" and "Hola desde el panel" in (r["aviso_global"] or ""),
                  "el aviso global aparece en la partida", r)
        print("El admin cierra la sala desde el panel")
        await asyncio.to_thread(panel, f"/salas/{sala}/cerrar", {"motivo": "Fin de la clase"}, token)
        r = await p.esperar("REPORTE cerrada")
        comprobar(r["pantalla"] == "Salas", "con sala_cerrada el juego vuelve al lobby", r)
        comprobar("Fin de la clase" in (r["aviso"] or ""), "y muestra el motivo", r)
        print("El admin expulsa al jugador desde el panel")
        estado = await asyncio.to_thread(panel, "/estado", None, token)
        jid = next(j["id"] for j in estado["jugadores"] if j["usuario"] == u)
        await asyncio.to_thread(panel, f"/jugadores/{jid}/expulsar", {"motivo": "Prueba automática"}, token)
        r = await p.esperar("REPORTE expulsado")
        comprobar(r["pantalla"] == "Conexion", "con expulsado el juego vuelve a la pantalla de conexión", r)
        comprobar("expulsado" in (r["aviso"] or "") and "Prueba automática" in (r["aviso"] or ""),
                  "y muestra el motivo (no 'Se perdió la conexión')", r)
        print("El admin bloquea la cuenta y el jugador intenta volver a entrar")
        await asyncio.to_thread(panel, f"/usuarios/{u}/bloquear", {"motivo": "Prueba de bloqueo"}, token)
        senal("bloqueado")
        r = await p.esperar("REPORTE bloqueado")
        comprobar(r["pantalla"] == "Perfil" and "Cuenta bloqueada: Prueba de bloqueo" in (r["aviso"] or ""),
                  "una cuenta bloqueada no puede iniciar sesión y ve el motivo", r)
        await p.esperar("FIN")
    finally:
        w.cerrar()


ESCENARIOS = {"laberinto": escenario_laberinto, "laberinto_player": escenario_laberinto_player,
              "sesion": escenario_sesion, "reinicio": escenario_reinicio,
              "panel": escenario_panel}


async def main():
    global escenario_actual
    pedidos = sys.argv[1:] or list(ESCENARIOS)
    if not JUEGO.exists():
        sys.exit(f"No existe {JUEGO}: genera el build de Linux primero")
    (RAIZ / "logs").mkdir(exist_ok=True)
    s = uuid.uuid4().hex[:6]  # usuarios nuevos en cada corrida: con BD persisten
    for nombre in pedidos:
        escenario_actual = nombre
        print(f"\n=== Escenario {nombre} ===")
        try:
            await asyncio.wait_for(ESCENARIOS[nombre](s), 240)
        except Exception as e:
            fallos.append(f"[{nombre}] se cortó: {e!r}")
            print(f"  ✘ se cortó: {e!r}")
        finally:
            for b in builds:
                if b.proc.poll() is None:
                    b.proc.kill()
            builds.clear()
    if fallos:
        print("\nFALLOS:")
        for f in fallos:
            print("  ✘", f)
        sys.exit(1)
    print("\nTODO OK ✔")


asyncio.run(main())
