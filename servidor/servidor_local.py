"""
Punto de entrada del servidor local de un solo ejecutable (QuimicaServidor.exe).

Es el mismo server.py de siempre (juego + API + panel en un proceso). Este archivo solo
agrega lo que necesita alguien que abre el servidor con doble clic, sin Docker ni
terminal:
  - Los datos (quimica.db) y la configuración (.env / admin.txt) van en la carpeta
    del ejecutable, no en la carpeta desde la que se lo abrió.
  - Sin .env, inventa una contraseña de admin al azar, la guarda en admin.txt y la
    muestra. La siguiente vez reusa la misma: si cambiara en cada arranque, el docente
    tendría que volver a mirarla siempre. Nunca hay una contraseña fija por defecto.
  - Muestra las IP, el puerto del juego y la URL del panel, y abre el navegador.

QUIMICA_SIN_NAVEGADOR=1 evita abrir el navegador (lo usa scripts/probar_paquete.sh).
"""
import asyncio
import os
import pathlib
import secrets
import socket
import sys
import threading
import time
import webbrowser


def carpeta_base() -> pathlib.Path:
    """La carpeta del .exe (PyInstaller) o la de este archivo (corriendo con Python)."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parent


def cargar_archivo_env(ruta: pathlib.Path) -> bool:
    """Lee CLAVE=valor sin pisar variables ya definidas (mismo formato que .env)."""
    if not ruta.is_file():
        return False
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
    return True


def contrasena_al_azar(largo: int = 12) -> str:
    """Letras y números sin los que se confunden al copiarlos a mano (0/O, 1/l/I): el
    docente la lee en la ventana y la escribe en el navegador."""
    alfabeto = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(largo))


def preparar_admin(base: pathlib.Path) -> pathlib.Path | None:
    """Devuelve la ruta de admin.txt si las credenciales salen de ahí (para mostrarlas)."""
    cargar_archivo_env(base / ".env")
    if os.getenv("ADMIN_USER") and os.getenv("ADMIN_PASSWORD"):
        return None
    ruta = base / "admin.txt"
    if not ruta.is_file():
        ruta.write_text(
            "# Credenciales del panel de administración, generadas al azar en el primer arranque.\n"
            "# Para cambiarlas, edita este archivo (o borra el archivo y se generan otras).\n"
            "ADMIN_USER=admin\n"
            f"ADMIN_PASSWORD={contrasena_al_azar()}\n"
            # Fijo entre reinicios: así las sesiones abiertas del panel siguen valiendo
            f"JWT_SECRET={secrets.token_hex(32)}\n",
            encoding="utf-8")
    cargar_archivo_env(ruta)
    return ruta


def ips_locales() -> list[str]:
    ips = set()
    try:
        ips.update(i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    try:
        # "Conectar" un socket UDP no manda nada: solo pregunta qué interfaz se usaría
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def abrir_navegador_cuando_este(puerto: int):
    """Espera a que el panel acepte conexiones y recién ahí abre el navegador: si se
    abre antes, el docente ve "no se puede acceder al sitio" y piensa que falló."""
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", puerto), timeout=0.5):
                webbrowser.open(f"http://localhost:{puerto}")
                return
        except OSError:
            time.sleep(0.5)


def main():
    # Con la salida redirigida a un archivo, Windows usa cp1252: un "→" de los logs
    # rompería esa línea. Con errors="replace" sale un "?" y el servidor sigue.
    for flujo in (sys.stdout, sys.stderr):
        if flujo is not None and hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")
    base = carpeta_base()
    admin_txt = preparar_admin(base)
    os.environ.setdefault("SQLITE_RUTA", str(base / "quimica.db"))
    if getattr(sys, "frozen", False):
        # panel/dist viaja dentro del paquete (ver quimica_servidor.spec)
        os.environ.setdefault("PANEL_DIR", str(pathlib.Path(sys._MEIPASS) / "panel_dist"))

    import server  # después de preparar el entorno: server.py lee las variables al importarse

    puerto_panel = int(os.getenv("PUERTO_PANEL", "8000"))
    linea = "=" * 62
    print(linea)
    print("  Servidor del Juego de Química — servidor local")
    print(linea)
    print(f"  Puerto del juego: {server.PUERTO}")
    print("  En esta PC, el juego se conecta a: 127.0.0.1")
    ips = ips_locales()
    if ips:
        print("  Desde otra PC de la red, usa alguna de estas IP:")
        for ip in ips:
            print(f"      {ip}")
    print(f"\n  Panel de administración: http://localhost:{puerto_panel}")
    if admin_txt is not None:
        print(f"      usuario: {os.environ['ADMIN_USER']}   contraseña: {os.environ['ADMIN_PASSWORD']}")
        print(f"      (guardadas en {admin_txt})")
    print(f"\n  Datos guardados en: {os.environ['SQLITE_RUTA']}")
    print("  Para apagar el servidor, cierra esta ventana.")
    print(linea, flush=True)

    if not os.getenv("QUIMICA_SIN_NAVEGADOR"):
        threading.Thread(target=abrir_navegador_cuando_este, args=(puerto_panel,), daemon=True).start()
    try:
        asyncio.run(server.main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
