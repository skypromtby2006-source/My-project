"""
Prueba con el build REAL de Linux (sin ventana) contra el servidor de Docker.
Por qué existe: probar_cliente.py y probar_perfiles.py hablan directo con el servidor,
así que no ven lo que pasa en MenuLobby y GestorPartida, que es justo donde fallaba
la prueba S2-3 aunque esos tests dieran TODO OK. Aquí cada "jugador Unity" es el
ejecutable de Build/Linux en -batchmode, manejado por PruebaAutomatica.cs (los mismos
métodos que los botones), y los demás jugadores son bots.
Uso:  python probar_build.py [escenario ...]   (sin argumentos: todos)
Escenarios: wizard, player, sesion, progreso (este último reinicia el servidor)
"""
import asyncio
import json
import math
import pathlib
import queue
import subprocess
import sys
import tempfile
import threading
import uuid

RAIZ = pathlib.Path(__file__).resolve().parent.parent
JUEGO = RAIZ / "Build" / "Linux" / "QuimicaDemo.x86_64"
IP, PUERTO = "127.0.0.1", 7777
SENALES = pathlib.Path(tempfile.mkdtemp(prefix="quimica_prueba_"))
MSG_WIZARD_SALIO = "El Wizard salió, la sala se cerró"

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

    def cerrar(self):
        self.w.close()


def aparicion_de(inicio, jugador_id):
    a = next((x for x in inicio.get("apariciones", []) if x["id"] == jugador_id), None)
    return (a["x"], a["z"]) if a else None


# ----------------------------------------------------------------- escenarios
async def escenario_wizard(s):
    """B1 (el Wizard ve a los demás en cada partida), B2 (sale un Player) y B5 (apariciones)."""
    w = f"w_{s}"

    def partida(n):
        return ["crear_sala", f"marca|sala{n}", "esperar_jugadores|2", "esperar_listos", "iniciar",
                "esperar_pantalla|Partida", "esperar|0.5", f"reporte|p{n}_aparicion",
                f"esperar_senal|p{n}_pos", "esperar|0.5", f"reporte|p{n}"]

    b = Build("wizard", ["conectar", f"registro|{w}|W{s}|#3FA9F5", "esperar_pantalla|Salas", *partida(1),
                         "esperar_senal|p1_salio", "esperar|1", "reporte|p1_tras_salida",
                         "salir", "esperar_pantalla|Salas", "esperar|0.5", "reporte|lobby1",
                         # Partida 2: después de editar el perfil (el caso de la S2-3)
                         "abrir_perfil", f"guardar_perfil|W2{s}|#E04F4F", "volver", *partida(2),
                         "salir", "esperar_pantalla|Salas",
                         # Partida 3: después de cerrar sesión y volver a entrar (MiId nuevo)
                         "desconectar", "conectar", f"login|{w}", "esperar_pantalla|Salas", *partida(3),
                         "fin"])

    for n, nombre_host in ((1, f"W{s}"), (2, f"W2{s}"), (3, f"W2{s}")):
        print(f"Partida {n}: un bot se une a la sala del Wizard (build)")
        await b.esperar(f"MARCA sala{n}")
        bot = await Bot.nuevo(f"b{n}_{s}", f"B{n}{s}")
        await bot.unirse_a(nombre_host)
        inicio = await bot.rec("inicio")
        r = await b.esperar(f"REPORTE p{n}_aparicion")
        comprobar(r["local"], f"p{n}: el Wizard tiene su cápsula")
        remoto = next((x for x in r["remotos"] if x["id"] == bot.id), None)
        comprobar(remoto is not None, f"p{n}: el Wizard tiene la cápsula del Player", r["remotos"])
        if remoto:
            comprobar(not cerca(r["local_x"], r["local_z"], remoto["x"], remoto["z"]),
                      f"p{n}: Wizard y Player aparecen en puntos distintos", r)
        if "apariciones" in inicio["mision"] or "apariciones" in inicio:
            ap = inicio.get("apariciones")
            mia, suya = aparicion_de(inicio, r["mi_id"]), aparicion_de(inicio, bot.id)
            comprobar(len({(x["x"], x["z"]) for x in ap}) == len(ap), f"p{n}: el servidor asigna apariciones distintas", ap)
            comprobar(mia and cerca(r["local_x"], r["local_z"], *mia), f"p{n}: el Wizard aparece donde dice el servidor", (r, mia))
            if remoto and suya:
                comprobar(cerca(remoto["x"], remoto["z"], *suya), f"p{n}: el Player aparece donde dice el servidor", (remoto, suya))

        await bot.env(t="pos", x=2.5, y=1, z=1.0, ry=0)
        senal(f"p{n}_pos")
        r = await b.esperar(f"REPORTE p{n}")
        remoto = next((x for x in r["remotos"] if x["id"] == bot.id), None)
        comprobar(remoto is not None and cerca(remoto["x"], remoto["z"], 2.5, 1.0),
                  f"p{n}: el Wizard ve moverse al Player", r["remotos"])
        comprobar(r["mi_id"] in r["jugadores_sala"], f"p{n}: MiId está en la sala", r)

        if n == 1:
            print("El Player sale a mitad de la misión: el Wizard sigue en la partida")
            await bot.env(t="salir")
            await bot.rec("fuera")
            senal("p1_salio")
            r = await b.esperar("REPORTE p1_tras_salida")
            comprobar(r["pantalla"] == "Partida", "B2: si sale un Player, el Wizard sigue jugando", r["pantalla"])
            comprobar(r["remotos"] == [], "el Player que salió ya no se dibuja", r["remotos"])
            r = await b.esperar("REPORTE lobby1")
            comprobar(r["pantalla"] == "Salas", "el Wizard volvió al lobby con ESC", r["pantalla"])
            comprobar(not r["escena"], "B1: al volver al lobby no queda la escena de la partida vieja", r)
        bot.cerrar()
    await b.esperar("FIN")


async def escenario_player(s):
    """B1 desde el Player (ve al Wizard en cada partida) y B2 (sale el Wizard)."""
    p = Build("player", ["conectar", f"registro|p_{s}|P{s}|#4FE07A", "esperar_pantalla|Salas",
                         "unirse_codigo|codigo1", "esperar_pantalla|Sala", "listo", "esperar_pantalla|Partida",
                         "esperar_senal|g1_pos", "esperar|0.5", "reporte|g1",
                         "esperar_senal|g1_wizard_salio", "esperar|1.5", "reporte|tras_wizard",
                         "unirse_codigo|codigo2", "esperar_pantalla|Sala", "listo", "esperar_pantalla|Partida",
                         "esperar_senal|g2_pos", "esperar|0.5", "reporte|g2", "fin"])
    for n in (1, 2):
        print(f"Partida {n}: el Player (build) se une a la sala de un bot Wizard")
        wiz = await Bot.nuevo(f"z{n}_{s}", f"Z{n}{s}", "#E04FD8")
        await wiz.crear_sala(f"codigo{n}")
        await wiz.esperar_sala_lista()
        await wiz.env(t="iniciar")
        await wiz.rec("inicio")
        await wiz.env(t="pos", x=-2.0, y=1, z=2.0, ry=0)
        senal(f"g{n}_pos")
        r = await p.esperar(f"REPORTE g{n}")
        remoto = next((x for x in r["remotos"] if x["id"] == wiz.id), None)
        comprobar(r["local"], f"g{n}: el Player tiene su cápsula")
        comprobar(remoto is not None and cerca(remoto["x"], remoto["z"], -2.0, 2.0),
                  f"g{n}: el Player ve al Wizard y lo ve moverse", r["remotos"])
        if n == 1:
            print("El Wizard sale: la sala se cierra para todos")
            await wiz.env(t="salir")
            await wiz.rec("fuera")
            senal("g1_wizard_salio")
            r = await p.esperar("REPORTE tras_wizard")
            comprobar(r["pantalla"] == "Salas", "B2: si sale el Wizard, el Player vuelve al lobby", r["pantalla"])
            comprobar(MSG_WIZARD_SALIO in (r["aviso"] or ""), "B2: el Player ve el aviso de sala cerrada", r["aviso"])
            comprobar(not r["escena"], "B1: no queda la escena de la partida vieja", r)
        wiz.cerrar()
    await p.esperar("FIN")


async def escenario_sesion(s):
    """B4: sesión única con ventanas reales, y que el usuario se libere al cerrar."""
    u = f"u_{s}"
    a = Build("sesion_a", ["conectar", f"registro|{u}|U{s}|#6A5AE0", "esperar_pantalla|Salas", "marca|logueado",
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


async def escenario_progreso(s):
    """B3: el Player completa la misión y la ve en Mi perfil; B4: reconexión tras reiniciar el servidor."""
    q = f"q_{s}"
    p = Build("progreso", ["conectar", f"registro|{q}|Q{s}|#F5913F", "esperar_pantalla|Salas",
                           "unirse_codigo|codigo_q", "esperar_pantalla|Sala", "listo", "esperar_pantalla|Partida",
                           "llevar|H", "llevar|H", "llevar|O", "esperar|0.5", "reporte|completada",
                           # La hipótesis del PM: que el Wizard salga justo al terminar
                           "esperar_senal|wiz_salio", "esperar|1", "salir", "esperar_pantalla|Salas", "abrir_perfil", "reporte|perfil1", "volver",
                           "marca|reiniciar", "esperar_pantalla|Conexion", "reporte|caido",
                           "esperar_senal|servidor_arriba", "reconectar", f"login|{q}", "esperar_pantalla|Salas",
                           "abrir_perfil", "reporte|perfil2", "fin"])
    wiz = await Bot.nuevo(f"zq_{s}", f"ZQ{s}", "#E04FD8")
    await wiz.crear_sala("codigo_q")
    await wiz.esperar_sala_lista()
    await wiz.env(t="iniciar")
    r = await p.esperar("REPORTE completada")
    comprobar(r["mision_completada"], "el Player (build) completó la misión", r)
    await wiz.env(t="salir")
    await wiz.rec("fuera")
    senal("wiz_salio")
    r = await p.esperar("REPORTE perfil1")
    comprobar(r["pantalla"] == "EditarPerfil", "Mi perfil está abierto", r["pantalla"])
    comprobar(r["completadas"] == 1 and r["historial"] == 1, "B3: Mi perfil muestra la misión completada", r)
    await p.esperar("MARCA reiniciar")
    wiz.cerrar()
    print("servidor_detener.sh + servidor_iniciar.sh con el juego abierto")
    await reiniciar_servidor()
    r = await p.esperar("REPORTE caido")
    comprobar(r["pantalla"] == "Conexion", "el juego detecta que el servidor se cayó", r)
    senal("servidor_arriba")
    r = await p.esperar("REPORTE perfil2", timeout=90)
    comprobar(r["usuario"] == q, "B4: vuelve a entrar con el mismo usuario tras reiniciar el servidor", r)
    comprobar(r["completadas"] == 1 and r["historial"] == 1, "B3: el progreso sigue tras reiniciar el servidor", r)
    await p.esperar("FIN")


ESCENARIOS = {"wizard": escenario_wizard, "player": escenario_player,
              "sesion": escenario_sesion, "progreso": escenario_progreso}


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
