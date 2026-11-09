# Receta de PyInstaller del servidor local: QuimicaServidor.exe (modo CARPETA).
#   pyinstaller servidor/quimica_servidor.spec --distpath dist/servidor_exe
# Requiere panel/dist compilado antes (cd panel && npm ci && npm run build).
#
# Modo carpeta y no "onefile": un onefile se descomprime entero en %TEMP% en CADA
# arranque (lento con pandas) y los antivirus lo marcan mucho más seguido.
import pathlib

from PyInstaller.utils.hooks import collect_submodules

SERVIDOR = pathlib.Path(SPECPATH)
RAIZ = SERVIDOR.parent
PANEL = RAIZ / "panel" / "dist"
if not (PANEL / "index.html").is_file():
    raise SystemExit(f"Falta {PANEL}: compila el panel primero (cd panel && npm ci && npm run build)")

a = Analysis(
    [str(SERVIDOR / "servidor_local.py")],
    pathex=[str(SERVIDOR)],
    datas=[(str(SERVIDOR / "niveles"), "niveles"), (str(PANEL), "panel_dist")],
    # server.py importa el panel dentro de funciones (para que sea opcional), y uvicorn
    # elige sus protocolos por nombre en tiempo de ejecución: se declaran a mano.
    hiddenimports=["server", "admin_api", "auth", "registro_logs", "estadisticas",
                   "repositorio", "nivel"] + collect_submodules("uvicorn"),
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="QuimicaServidor",
          console=True)  # con consola: muestra IP, contraseña y logs; cerrarla apaga el servidor
coll = COLLECT(exe, a.binaries, a.datas, name="QuimicaServidor")
