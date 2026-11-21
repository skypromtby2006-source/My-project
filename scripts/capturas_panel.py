#!/usr/bin/env python3
"""Capturas del panel web (login, admin y docente) con los datos de demo, para el
material de respaldo de la presentación (docs/presentacion/capturas/panel/).

Levanta un servidor propio en puertos libres sobre un SQLite descartable, le siembra
los datos de demo (servidor/demo.py) y saca las capturas con Firefox headless por
WebDriver BiDi (viene con Firefox: no hace falta instalar geckodriver ni Playwright).

Uso: scripts/capturas_panel.py [carpeta_salida]
Requiere panel/dist compilado (cd panel && npm run build) y Firefox.
"""
import asyncio
import base64
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "servidor"))
import demo  # noqa: E402

SALIDA = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "presentacion" / "capturas" / "panel"
CLAVE_ADMIN = "clave-capturas-123"
PAGINAS_ADMIN = [("admin_inicio", ""), ("admin_salas", "salas"), ("admin_usuarios", "usuarios"),
                 ("admin_usuario_ana", "usuarios/ana_demo"), ("admin_estadisticas", "estadisticas"),
                 ("admin_logs", "logs"), ("admin_auditoria", "auditoria"), ("admin_docentes", "docentes")]


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def api(base, ruta, datos=None):
    req = urllib.request.Request(base + "/api" + ruta, data=json.dumps(datos).encode() if datos else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


class Firefox:
    """Lo mínimo de WebDriver BiDi: navegar, ejecutar JS y capturar la pantalla."""

    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def cmd(self, metodo, **params):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "method": metodo, "params": params}))
        while True:
            m = json.loads(await self.ws.recv())
            if m.get("id") == self.n:
                if m.get("type") == "error":
                    raise RuntimeError(f"{metodo}: {m.get('message')}")
                return m["result"]

    async def abrir(self):
        await self.cmd("session.new", capabilities={})
        self.ctx = (await self.cmd("browsingContext.getTree"))["contexts"][0]["context"]

    async def ir(self, url, espera=1.5):
        await self.cmd("browsingContext.navigate", context=self.ctx, url=url, wait="complete")
        await asyncio.sleep(espera)   # que React pida los datos a la API y los dibuje

    async def js(self, codigo):
        await self.cmd("script.evaluate", expression=codigo, target={"context": self.ctx}, awaitPromise=True)

    async def captura(self, nombre):
        r = await self.cmd("browsingContext.captureScreenshot", context=self.ctx, origin="document")
        (SALIDA / f"{nombre}.png").write_bytes(base64.b64decode(r["data"]))
        print(f"  {nombre}.png")


async def capturar(base, tokens):
    puerto_ff = puerto_libre()
    perfil = tempfile.mkdtemp(prefix="ff_capturas_")
    ff = subprocess.Popen(["firefox", "--headless", "--no-remote", "--profile", perfil,
                           f"--remote-debugging-port={puerto_ff}", "--window-size=1366,860"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                ws = await websockets.connect(f"ws://127.0.0.1:{puerto_ff}/session", max_size=None)
                break
            except OSError:
                await asyncio.sleep(0.5)
        else:
            raise RuntimeError("Firefox no abrió el puerto de WebDriver BiDi")
        async with ws:
            b = Firefox(ws)
            await b.abrir()
            await b.ir(base + "/")
            await b.captura("login")
            for rol, paginas in tokens.items():
                await b.js(f"sessionStorage.setItem('panel_token', {json.dumps(paginas['token'])})")
                for nombre, ruta in paginas["paginas"]:
                    # ?nombre cambia la URL: carga completa, así el panel relee el token
                    await b.ir(f"{base}/?{nombre}#/{ruta}", espera=2.5 if "estadisticas" in ruta else 1.5)
                    await b.captura(nombre)
    finally:
        ff.terminate()
        ff.wait(10)
        shutil.rmtree(perfil, ignore_errors=True)


def main():
    if not (RAIZ / "panel" / "dist" / "index.html").is_file():
        sys.exit("Falta panel/dist: cd panel && npm run build")
    SALIDA.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="capturas_panel_"))
    puerto_panel = puerto_libre()
    env = {**os.environ, "SQLITE_RUTA": str(tmp / "quimica.db"), "PUERTO": str(puerto_libre()),
           "PUERTO_PANEL": str(puerto_panel), "ADMIN_USER": "admin", "ADMIN_PASSWORD": CLAVE_ADMIN,
           "JWT_SECRET": "x" * 64, "PANEL_DIR": str(RAIZ / "panel" / "dist")}
    env.pop("DATABASE_URL", None)
    os.environ.update(env)
    r = asyncio.run(demo.ejecutar("sembrar", tmp, env["SQLITE_RUTA"]))
    if r != 0:
        sys.exit(r)
    cred = demo.leer_credenciales(tmp / demo.ARCHIVO_CREDENCIALES)
    srv = subprocess.Popen([sys.executable, "server.py"], cwd=RAIZ / "servidor", env=env,
                           stdout=open(tmp / "servidor.log", "w"), stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{puerto_panel}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        admin = api(base, "/login", {"usuario": "admin", "contrasena": CLAVE_ADMIN})["token"]
        docente = api(base, "/login", {"usuario": demo.DOCENTE, "contrasena": cred["DOCENTE_PASSWORD"]})["token"]
        req = urllib.request.Request(base + "/api/docente/retos", headers={"Authorization": f"Bearer {docente}"})
        reto_id = json.load(urllib.request.urlopen(req))[0]["id"]
        tokens = {
            "admin": {"token": admin, "paginas": PAGINAS_ADMIN},
            "docente": {"token": docente, "paginas": [
                ("docente_clases", ""), ("docente_retos", "retos"),
                ("docente_resultados", f"retos/{reto_id}"), ("docente_estudiante_ana", "estudiantes/ana_demo"),
                ("docente_vivo", "vivo"), ("docente_logs", "logs")]},
        }
        print(f"Capturas del panel en {SALIDA}")
        asyncio.run(capturar(base, tokens))
    finally:
        srv.terminate()
        srv.wait(10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
