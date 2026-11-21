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
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

RAIZ = pathlib.Path(__file__).resolve().parent.parent
JUEGO = RAIZ / "Build" / "Linux" / "QuimicaDemo.x86_64"
IP, PUERTO = "127.0.0.1", 7777
PUERTO_LAB, PUERTO_PANEL_LAB = 7788, 8008   # servidor propio del escenario laberinto
SEMILLA_LAB = 123                            # debe coincidir con el NIVEL_SEMILLA del servidor
SENALES = pathlib.Path(tempfile.mkdtemp(prefix="quimica_prueba_"))
# Capturas de cada sala (escenario laberinto): quedan para mirarlas después de la corrida
CAPTURAS = RAIZ / "logs" / "capturas"
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
        env.pop("DATABASE_URL", None)   # sin PostgreSQL: no toca la BD de nadie
        env["SQLITE_RUTA"] = ":memory:"  # SQLite en RAM: no deja un quimica.db de la prueba
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

    def __init__(self, nombre, pasos, graficos=False):
        self.nombre = nombre
        self.cola = queue.Queue()
        self.log = open(RAIZ / "logs" / f"prueba_{nombre}.log", "w", encoding="utf-8")
        args = [str(JUEGO), "-batchmode", "-logFile", "-", "-prueba", ";".join(pasos),
                "-ip", IP, "-puerto", str(PUERTO), "-senales", str(SENALES)]
        if graficos:
            # Las capturas necesitan GPU. En -batchmode igual no se abre ninguna ventana,
            # pero el player de Linux necesita un servidor gráfico para crear el contexto:
            # sin DISPLAY se cuelga (OpenGL) o se cae (Vulkan). Sin sesión gráfica -> Xvfb.
            args += ["-capturas", str(CAPTURAS / nombre)]
            if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                if not shutil.which("xvfb-run"):
                    raise RuntimeError("las capturas necesitan una sesión gráfica o xvfb-run "
                                       "(sudo pacman -S xorg-server-xvfb)")
                args = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24"] + args
        else:
            args.insert(2, "-nographics")
        self.proc = subprocess.Popen(
            args,
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


# SPRINT_UI: tras el login el juego va al Menú principal; las salas se abren con su
# botón "Ver salas", como lo haría una persona.
A_SALAS = ("esperar_pantalla|Menu", "abrir_salas", "esperar_pantalla|Salas")

async def escenario_sesion(s):
    """B4: sesión única con ventanas reales, y que el usuario se libere al cerrar."""
    u = f"u_{s}"
    a = Build("sesion_a", ["conectar", "registro|abc|Corto|#6A5AE0", "esperar_aviso|de 4 a 16",  # B7
                           f"registro|{u}|U{s}|#6A5AE0", "esperar_pantalla|Menu", "marca|logueado",
                           "esperar_senal|cerrar_a", "fin"])
    await a.esperar("MARCA logueado")
    b = Build("sesion_b", ["conectar", f"login|{u}", "esperar|2", "reporte|rechazo",
                           "esperar_senal|a_cerrado", f"login|{u}", "esperar_pantalla|Menu", "reporte|entro",
                           "desconectar", "marca|desconectado", "esperar_senal|c_listo", "fin"])
    r = await b.esperar("REPORTE rechazo")
    comprobar(r["pantalla"] == "Login" and "sesión abierta" in (r["aviso"] or ""),
              "una segunda ventana con el mismo usuario se rechaza", r)
    print("Se cierra la primera ventana: el usuario se libera")
    senal("cerrar_a")
    comprobar(await a.terminar() == 0, "la primera ventana se cerró")
    senal("a_cerrado")
    r = await b.esperar("REPORTE entro")
    comprobar(r["pantalla"] == "Menu" and r["usuario"] == u, "la segunda ventana entra tras cerrar la primera", r)
    await b.esperar("MARCA desconectado")
    print("Botón Desconectar y una tercera ventana entra; luego se mata a la fuerza")
    c = Build("sesion_c", ["conectar", f"login|{u}", "esperar_pantalla|Menu", "reporte|entro", "esperar|60"])
    r = await c.esperar("REPORTE entro")
    comprobar(r["pantalla"] == "Menu", "tras Desconectar, otra ventana entra con ese usuario", r)
    senal("c_listo")
    c.proc.kill()  # como si el juego se colgara y se cerrara a la fuerza
    await c.terminar()
    d = Build("sesion_d", ["conectar", f"login|{u}", "esperar_pantalla|Menu", "reporte|entro", "fin"])
    r = await d.esperar("REPORTE entro")
    comprobar(r["pantalla"] == "Menu", "tras matar el proceso, el usuario se libera", r)
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
    p = Build("reinicio", ["conectar", f"registro|{u}|R{s}|#FFFFFF", "esperar_pantalla|Menu", "marca|reiniciar",
                           "esperar_pantalla|Login", "esperar_senal|iniciar_termino",
                           "conectar", "esperar|0.5", f"login|{u}", "esperar|3", "reporte|tras_login", "fin"])
    await p.esperar("MARCA reiniciar")
    for script in ("servidor_detener.sh", "servidor_iniciar.sh"):  # sin esperar el log del servidor
        await asyncio.to_thread(subprocess.run, [str(RAIZ / "scripts" / script)], check=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    senal("iniciar_termino")
    r = await p.esperar("REPORTE tras_login", timeout=90)
    comprobar(r["pantalla"] == "Menu" and r["usuario"] == u,
              "B4: se puede entrar apenas termina servidor_iniciar.sh", r)
    await p.esperar("FIN")
    await reiniciar_servidor()  # deja el servidor escuchando para el siguiente escenario


def comprobar_capturas(r):
    """El arte, verificado sin que nadie juegue: una captura por sala y por lado desde la
    cámara del jugador. Los umbrales separan "se ve algo" de una imagen negra, quemada,
    plana o con el magenta de un shader faltante; que se vea BIEN lo juzga una persona
    mirando los PNG de logs/capturas/."""
    print(f"  capturas con {r['dispositivo']} en {CAPTURAS / 'laberinto'}")
    comprobar(r["shaders_error"] == 0, f"ningún material del nivel con shader faltante ({r['renderers']} renderers)", r)
    salas = {c["sala"] for c in r["capturas"]}
    comprobar(len(salas) == len(nivel.cargar()["salas"]) and len(r["capturas"]) == 2 * len(salas),
              f"una captura por sala y por lado ({len(r['capturas'])} imágenes)", [c["archivo"] for c in r["capturas"]])
    for c in r["capturas"]:
        lum, con, mag = c["luminancia"], c["contraste"], c["magenta"]
        detalle = f"luminancia {lum:.2f} · contraste {con:.2f} · magenta {mag:.1%} → {c['archivo']}"
        comprobar(0.06 <= lum <= 0.94 and con >= 0.03 and mag < 0.01,
                  f"sala {c['sala']} ({c['nombre']}), lado {c['lado']}: se ve algo", detalle)


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
        build = Build("laberinto", graficos=True, pasos=[
            "conectar", f"registro|{w}|WLab{s}|#3FA9F5", *A_SALAS,
            *partida("p1"), "reporte|p1_inicio", "capturas", "medir_fps|4",
            ESTE_DE_D1, EMPUJE_OESTE, "esperar|0.2", "reporte|dc_cerrada",
            f"dial|dial_h2|{h2}", "marca|s1_wiz_listo", "esperar_senal|s1_baja", "palanca|D1",
            "esperar_sala|2", "reporte|sala2",
            ESTE_DE_D1, EMPUJE_OESTE, "esperar|0.2", "reporte|dc_abierta",
            "esperar_senal|player_fuera", "esperar|1", "reporte|tras_player",
            "salir", "esperar_pantalla|Salas", "esperar|0.3", "reporte|lobby1",
            *partida("p2"), "reporte|p2_inicio", "salir", "esperar_pantalla|Salas",
            "marca|reiniciar", "esperar_pantalla|Login", "esperar_senal|servidor_ok",
            "conectar", "esperar_conectado", f"registro|{w}b|WLab2{s}|#3FA9F5",
            "esperar_pantalla|Menu", "reporte|reconectado", "fin"])

        # ---- Partida 1 ----
        await build.esperar("MARCA p1")
        bot = await Bot.nuevo(f"bl1_{s}", f"BL1{s}", "#4FE07A")
        await bot.entrar_laberinto(f"WLab{s}")
        r = await build.esperar("REPORTE p1_inicio")
        comprobar(r["escena"] and r["sala_lab"] == 1, "laberinto: el Wizard entra a la sala 1", r)
        remoto = next((x for x in r["remotos"] if x["id"] == bot.id), None)
        comprobar(remoto is not None, "B1: el Wizard ve la cápsula del Player", r["remotos"])
        comprobar_capturas(await build.esperar("REPORTE capturas", timeout=90))
        f = await build.esperar("REPORTE fps", timeout=30)
        comprobar(f["fps"] >= 60, f"≥ 60 FPS a 1920×1080 ({f['fps']:.0f} FPS, {f['ms_medio']:.1f} ms de media, "
                                 f"peor cuadro {f['ms_peor']:.1f} ms, {f['dispositivo']})", f)

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
        comprobar(r["pantalla"] == "Menu", "B4: el Wizard reconecta tras reiniciar el servidor", r)
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
            "conectar", f"registro|pl_{s}|PLab{s}|#4FE07A", *A_SALAS,
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


async def escenario_hud(s):
    """UI-3: HUD, pausa y avisos con el diseño nuevo. El build es el Player (laberinto con
    servidor propio, como laberinto_player); captura el HUD y la pausa con el panel de UI
    Toolkit encima (logs/capturas/hud/) y comprueba que la pausa se abre y que "Salir de
    la sala" desde ahí vuelve a la lista."""
    global PUERTO
    orig_puerto = PUERTO
    PUERTO = PUERTO_LAB
    srv = ServidorLocal()
    try:
        await srv.arrancar()
        build = Build("hud", graficos=True, pasos=[
            "conectar", f"registro|ph_{s}|PHud{s}|#4FE07A", *A_SALAS,
            "unirse_codigo|codhud", "esperar_pantalla|Sala", "listo", "esperar_pantalla|Partida",
            "esperar_escena", "esperar|1", "captura_pantalla|hud_player", "reporte|hud",
            "pausa", "esperar|0.3", "captura_pantalla|hud_pausa", "reporte|pausa",
            "continuar", "esperar|0.3", "reporte|continua",
            "pausa", "salir", "esperar_pantalla|Salas", "reporte|fuera", "fin"])
        wiz = await Bot.nuevo(f"zh_{s}", f"ZH{s}", "#E04FD8")
        await wiz.crear_sala("codhud")
        await wiz.esperar_sala_lista()
        await wiz.env(t="iniciar", modo="laberinto")
        await wiz.rec("inicio")
        r = await build.esperar("REPORTE hud")
        comprobar(r["pantalla"] == "Partida" and r["hud"] and not r["pausa"], "en partida se ve el HUD nuevo, sin pausa", r)
        r = await build.esperar("REPORTE pausa")
        comprobar(r["pausa"] and r["hud"], "la pausa se abre sobre el HUD", r)
        r = await build.esperar("REPORTE continua")
        comprobar(not r["pausa"] and r["pantalla"] == "Partida", "Continuar vuelve a la partida", r)
        r = await build.esperar("REPORTE fuera")
        comprobar(r["pantalla"] == "Salas" and not r["hud"] and not r["escena"], "Salir de la sala desde la pausa vuelve a la lista y oculta el HUD", r)
        await build.esperar("FIN")
        for n in ("hud_player", "hud_pausa"):
            comprobar((CAPTURAS / "hud" / f"{n}.png").exists(), f"captura {n}.png", str(CAPTURAS / "hud"))
        wiz.cerrar()
    finally:
        srv.detener()
        PUERTO = orig_puerto


def panel(ruta, datos=None, token=None):
    """Llama a la API del panel web (solo biblioteca estándar, como el resto del script).
    El panel acepta 5 logins por minuto por IP: con todos los escenarios seguidos se
    puede pasar, así que un 429 en /login espera a que se libere y reintenta."""
    for intento in range(3):
        try:
            return _panel(ruta, datos, token)
        except urllib.error.HTTPError as e:
            if e.code != 429 or ruta != "/login" or intento == 2:
                raise
            print("  (límite de logins del panel: espero 30 s)")
            time.sleep(30)


def _panel(ruta, datos=None, token=None):
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
    p = Build("panel_p", ["conectar", f"registro|{u}|Pepa|#4FE07A", *A_SALAS,
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
        await w.env(t="iniciar", modo="laberinto")  # como el cliente real desde S4-2: el modo agua tira el build
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
        comprobar(r["pantalla"] == "Login", "con expulsado el juego vuelve al Login", r)
        comprobar("expulsado" in (r["aviso"] or "") and "Prueba automática" in (r["aviso"] or ""),
                  "y muestra el motivo (no 'Se perdió la conexión')", r)
        print("El admin bloquea la cuenta y el jugador intenta volver a entrar")
        await asyncio.to_thread(panel, f"/usuarios/{u}/bloquear", {"motivo": "Prueba de bloqueo"}, token)
        senal("bloqueado")
        r = await p.esperar("REPORTE bloqueado")
        comprobar(r["pantalla"] == "Login" and "Cuenta bloqueada: Prueba de bloqueo" in (r["aviso"] or ""),
                  "una cuenta bloqueada no puede iniciar sesión y ve el motivo", r)
        await p.esperar("FIN")
    finally:
        w.cerrar()


async def escenario_reto(s):
    """Revisión 20/11, rol docente con el juego real: el admin crea un docente; el docente
    crea una clase y un reto con semilla fija; el build (anfitrión) se une a la clase
    desde Mi perfil, elige el reto en el Lobby y lo inicia con un bot como Player. Se
    comprueba que la partida usa la semilla del reto y que se guarda un intento por jugador."""
    semilla = 4000 + int(s[:3], 16)
    datos = {"usuario": "admin", "contrasena": clave_admin()}
    admin = (await asyncio.to_thread(panel, "/login", datos))["token"]
    profe = f"pr_{s}"
    await asyncio.to_thread(panel, "/docentes", {"usuario": profe, "nombre": "Profe Prueba",
                                                 "contrasena": "clave-de-prueba"}, admin)
    doc = (await asyncio.to_thread(panel, "/login", {"usuario": profe, "contrasena": "clave-de-prueba"}))["token"]
    clase = await asyncio.to_thread(panel, "/docente/clases", {"nombre": f"Clase {s}"}, doc)
    reto = await asyncio.to_thread(panel, "/docente/retos", {"clase_id": clase["id"], "semilla": semilla,
                                                             "tiempo_limite_s": 600}, doc)
    senal("codigo_clase", clase["codigo"])
    b = Build("reto", ["conectar", f"registro|rh_{s}|Host{s}|#3FA9F5", "esperar_pantalla|Menu",
                       "abrir_perfil", "unirse_clase|codigo_clase", "reporte|perfil", "volver",
                       *A_SALAS, "crear_sala", "esperar_pantalla|Sala", "cambiar_reto", "reporte|lobby",
                       "esperar_jugadores|2", "esperar|1", "iniciar", "esperar_pantalla|Partida",
                       "esperar_escena", "reporte|partida", "esperar_senal|fin_reto", "fin"])
    r = await b.esperar("REPORTE perfil")
    comprobar(r["clases"] == 1 and f"Clase {s}" in (r["info"] or ""), "Unirse a clase desde Mi perfil con el código", r)
    r = await b.esperar("REPORTE lobby")
    comprobar(r["reto"] == reto["id"] and r["retos"] >= 1, "el anfitrión elige el reto en el Lobby", r)
    bot = await Bot.nuevo(f"rp_{s}", f"RP{s}", "#4FE07A")
    try:
        await bot.env(t="unirse_clase", codigo=clase["codigo"])
        await bot.rec("clase_unida")
        inicio = await bot.entrar_laberinto(f"Host{s}")
        r = await b.esperar("REPORTE partida")
        comprobar(r["escena"] and r["sala_lab"] == 1, "la partida del reto arranca en el laberinto", r)
        visible = {k: v for k, v in nivel.sortear(random.Random(semilla))[1].items() if k not in ("resp", "produce")}
        comprobar(inicio["nivel"]["sala"]["datos"] == json.loads(json.dumps(visible)),
                  "la partida usa la semilla del reto (mismos números)", inicio["nivel"]["sala"]["datos"])
        await bot.env(t="salir")
        await bot.rec("fuera")
        senal("fin_reto")
        await b.esperar("FIN")
        for _ in range(40):
            res = await asyncio.to_thread(panel, f"/docente/retos/{reto['id']}/resultados", None, doc)
            if len(res["intentos"]) >= 2:
                break
            await asyncio.sleep(0.25)
        quienes = sorted(i["usuario"] for i in res["intentos"])
        comprobar(quienes == sorted([f"rh_{s}", f"rp_{s}"]), "un intento por jugador en los resultados del docente", quienes)
        comprobar(not any(i["completado"] for i in res["intentos"]), "abandonar a medias = no completado", res["intentos"])
    finally:
        bot.cerrar()


async def escenario_espectador(s):
    """Revisión 20/11 (🟡): el docente entra al juego REAL con usuario y contraseña y mira
    una partida en curso de dos bots, con cámara libre, sin contar como jugador. Ve moverse
    a los jugadores y al salir vuelve a la lista de salas."""
    datos = {"usuario": "admin", "contrasena": clave_admin()}
    admin = (await asyncio.to_thread(panel, "/login", datos))["token"]
    profe = f"pe_{s}"
    await asyncio.to_thread(panel, "/docentes", {"usuario": profe, "nombre": "Profe Mira",
                                                 "contrasena": "clave-de-prueba"}, admin)
    w = await Bot.nuevo(f"ew_{s}", f"EW{s}", "#3FA9F5")
    p = await Bot.nuevo(f"ep_{s}", f"EP{s}", "#4FE07A")
    try:
        codigo = await w.crear_sala("sala_espectar")
        await p.env(t="unirse", sala_id=codigo)
        await p.rec("sala")
        await p.env(t="listo", valor=True)
        await w.esperar_sala_lista()
        await w.env(t="iniciar", modo="laberinto")
        await w.rec("inicio")
        await p.rec("inicio")
        b = Build("espectador", ["conectar", f"login_docente|{profe}|clave-de-prueba", "esperar_pantalla|Salas",
                                 "reporte|salas", "espectar|sala_espectar", "esperar_pantalla|Partida",
                                 "esperar_escena", "esperar|1", "reporte|mirando", "esperar_senal|movido",
                                 "esperar|1", "reporte|movido", "salir", "esperar_pantalla|Salas",
                                 "reporte|fuera", "fin"])
        r = await b.esperar("REPORTE salas")
        comprobar(r["docente"] and r["nombre"] == "Profe Mira", "el docente entra con usuario y contraseña", r)
        r = await b.esperar("REPORTE mirando")
        comprobar(r["escena"] and r["camara_libre"] and r["sala"] == codigo,
                  "entra a la partida en curso como espectador, con cámara libre", r)
        comprobar(r["mi_id"] not in r["jugadores_sala"] and len(r["jugadores_sala"]) == 2 and r["espectadores"] == 1,
                  "no cuenta como jugador (2 jugadores + 1 espectador)", r)
        comprobar(sorted(x["id"] for x in r["remotos"]) == sorted([w.id, p.id]), "ve a los dos jugadores", r["remotos"])
        await p.env(t="pos", x=3.25, y=1, z=-2.5, ry=90)
        senal("movido")
        r = await b.esperar("REPORTE movido")
        pr = next(x for x in r["remotos"] if x["id"] == p.id)
        comprobar(abs(pr["x"] - 3.25) < 0.01 and abs(pr["z"] + 2.5) < 0.01, "ve moverse al Player en vivo", pr)
        r = await b.esperar("REPORTE fuera")
        comprobar(r["pantalla"] == "Salas" and not r["escena"], "con Esc / salir vuelve a la lista de salas", r)
        await b.esperar("FIN")
        await w.env(t="listar")
        sala = next(x for x in (await w.rec("salas"))["lista"] if x["id"] == codigo)
        comprobar(sala["cantidad"] == 2 and sala["estado"] == "jugando", "la partida de los jugadores sigue intacta", sala)
    finally:
        w.cerrar()
        p.cerrar()


async def escenario_menus(s):
    """Presentación: una captura de cada pantalla del menú con el juego real (Login, Menú,
    Mi perfil con una clase, lista de salas y Lobby con el reto elegido y 2 jugadores),
    en logs/capturas/menus/. Es material de respaldo por si algo falla en vivo. Usa el
    servidor de Docker, como "reto", porque las clases necesitan la BD."""
    datos = {"usuario": "admin", "contrasena": clave_admin()}
    admin = (await asyncio.to_thread(panel, "/login", datos))["token"]
    profe = f"pm_{s}"
    await asyncio.to_thread(panel, "/docentes", {"usuario": profe, "nombre": "Profe Demo",
                                                 "contrasena": "clave-de-prueba"}, admin)
    doc = (await asyncio.to_thread(panel, "/login", {"usuario": profe, "contrasena": "clave-de-prueba"}))["token"]
    clase = await asyncio.to_thread(panel, "/docente/clases", {"nombre": "Química 5to A"}, doc)
    await asyncio.to_thread(panel, "/docente/retos", {"clase_id": clase["id"], "semilla": 20261121}, doc)
    senal("codigo_clase", clase["codigo"])
    nombres = ["login", "menu", "perfil", "salas", "sala_reto", "sala_dos"]
    b = Build("menus", graficos=True, pasos=[
        "conectar", "esperar_pantalla|Login", "esperar|0.5", "captura_pantalla|login",
        f"registro|ma_{s}|Ana|#3FA9F5", "esperar_pantalla|Menu", "esperar|0.5", "captura_pantalla|menu",
        "abrir_perfil", "unirse_clase|codigo_clase", "esperar|0.5", "captura_pantalla|perfil", "volver",
        *A_SALAS, "esperar|0.5", "captura_pantalla|salas",
        "crear_sala", "esperar_pantalla|Sala", "cambiar_reto", "esperar|0.5", "captura_pantalla|sala_reto",
        "esperar_jugadores|2", "esperar|1", "captura_pantalla|sala_dos", "reporte|lobby", "fin"])
    bot = await Bot.nuevo(f"mb_{s}", "Beto", "#F5D33F")
    try:
        await bot.env(t="unirse_clase", codigo=clase["codigo"])
        await bot.rec("clase_unida")
        sala = None
        for _ in range(120):   # la sala del build aparece cuando llega a crear_sala
            await bot.env(t="listar")
            sala = next((x for x in (await bot.rec("salas"))["lista"]
                         if any(j["nombre"] == "Ana" for j in x["jugadores"])), None)
            if sala:
                break
            await asyncio.sleep(0.25)
        comprobar(sala is not None, "la sala del build aparece en la lista", None)
        await bot.env(t="unirse", sala_id=sala["id"])
        await bot.rec("sala")
        await bot.env(t="listo", valor=True)
        r = await b.esperar("REPORTE lobby")
        comprobar(r["pantalla"] == "Sala" and r["reto"] is not None, "el Lobby muestra el reto elegido", r)
        await b.esperar("FIN")
        for n in nombres:
            comprobar((CAPTURAS / "menus" / f"{n}.png").exists(), f"captura {n}.png", str(CAPTURAS / "menus"))
    finally:
        bot.cerrar()


ESCENARIOS = {"laberinto": escenario_laberinto, "laberinto_player": escenario_laberinto_player,
              "sesion": escenario_sesion, "reinicio": escenario_reinicio,
              "panel": escenario_panel, "reto": escenario_reto, "espectador": escenario_espectador,
              "hud": escenario_hud, "menus": escenario_menus}


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
