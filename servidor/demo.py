"""
Datos de demo para la presentación: una clase con estudiantes que ya jugaron, para que
el panel docente y las estadísticas no se vean vacíos al abrirlos en vivo.

    sembrar  ->  docente_demo (con contraseña generada), la clase "Química 5to A", un
                 reto del laberinto con semilla fija y 4 estudiantes *_demo inscritos,
                 con intentos ya jugados y errores variados por concepto.
    limpiar  ->  borra SOLO eso: el docente demo con su clase y su reto, y todos los
                 usuarios *_demo (también los creados en vivo durante la presentación).

Idempotente: sembrar dos veces no duplica nada y deja la misma contraseña (la lee de
demo_credenciales.txt). Va por `repositorio.py`, así sirve igual para SQLite (servidor
local) y PostgreSQL (servidor dedicado).

Cómo se corre:
  - Windows, servidor local:  Servidor/sembrar_demo.bat  (QuimicaServidor.exe --sembrar-demo)
  - Linux / desarrollo:       scripts/sembrar_demo.py  y  scripts/limpiar_demo.py
  - Docker:                   docker compose exec servidor python demo.py sembrar
"""
import asyncio
import os
import pathlib
import sys

import auth
import repositorio

DOCENTE = "docente_demo"
DOCENTE_NOMBRE = "Prof. Demo"
CLASE = "Química 5to A"
NIVEL = "laberinto_01"         # "Laberinto de las 5 puertas": las salas 1 a 5
SEMILLA = 20261121             # fija: todos los grupos juegan los mismos números
ESTUDIANTES = [                # (usuario, nombre, color de la paleta del juego)
    ("ana_demo", "Ana", "#3FA9F5"),
    ("beto_demo", "Beto", "#F5D33F"),
    ("carla_demo", "Carla", "#E04FD8"),
    ("dani_demo", "Dani", "#4FE07A"),
]
# Intentos ya jugados: (sala, segundos, completado, {usuario: {concepto: errores}}).
# Variados a propósito para que el panel muestre en qué concepto se traba cada uno.
INTENTOS = [
    ("HQ3K", 1265.0, True, {"ana_demo": {"balanceo": 2, "masa": 1},
                            "beto_demo": {"mol": 1, "limitante": 3}}),
    ("TZ7M", 540.0, False, {"carla_demo": {"balanceo": 3},
                            "dani_demo": {"balanceo": 1, "mol": 2}}),
    ("W4PR", 1490.0, True, {"carla_demo": {"limitante": 1, "rendimiento": 2},
                            "dani_demo": {"masa": 2, "rendimiento": 1}}),
]
ARCHIVO_CREDENCIALES = "demo_credenciales.txt"


def leer_credenciales(ruta: pathlib.Path) -> dict:
    datos = {}
    if ruta.is_file():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                datos[k.strip()] = v.strip()
    return datos


def escribir_credenciales(ruta: pathlib.Path, contrasena: str, codigo: str):
    admin_u = os.getenv("ADMIN_USER", "admin")
    admin_p = os.getenv("ADMIN_PASSWORD", "(la de ADMIN_PASSWORD en el .env)")
    ruta.write_text(
        "# Credenciales de la demo, generadas por sembrar_demo. Anotarlas en papel.\n"
        "# Panel: http://localhost:8000 (desde otra PC: http://<IP del servidor>:8000)\n"
        f"ADMIN_USER={admin_u}\n"
        f"ADMIN_PASSWORD={admin_p}\n"
        f"DOCENTE_USER={DOCENTE}\n"
        f"DOCENTE_PASSWORD={contrasena}\n"
        f"CLASE={CLASE}\n"
        f"CODIGO_CLASE={codigo}\n"
        f"SEMILLA_RETO={SEMILLA}\n"
        f"ESTUDIANTES={', '.join(u for u, _, _ in ESTUDIANTES)}   (sin contraseña)\n",
        encoding="utf-8")


async def sembrar(repo: repositorio.Repositorio, carpeta: pathlib.Path) -> dict:
    """Deja la BD lista para presentar y devuelve lo que se muestra en pantalla."""
    from admin_api import nuevo_codigo_clase

    ruta = carpeta / ARCHIVO_CREDENCIALES
    contrasena = leer_credenciales(ruta).get("DOCENTE_PASSWORD") or auth.contrasena_al_azar()
    hash_ = auth.hash_contrasena(contrasena)
    doc = await repo.crear_docente(DOCENTE, DOCENTE_NOMBRE, hash_)
    if doc is None:   # ya existía: se le vuelve a poner la contraseña del archivo
        await repo.fijar_hash_docente(DOCENTE, hash_)
        doc = await repo.buscar_docente(DOCENTE)

    clase = next((c for c in await repo.clases_de_docente(doc["id"]) if c["nombre"] == CLASE), None)
    while clase is None:   # un choque de códigos es casi imposible; si pasa, se sortea otro
        clase = await repo.crear_clase(doc["id"], CLASE, nuevo_codigo_clase())

    reto = next((r for r in await repo.retos_de_docente(doc["id"])
                 if r["clase_id"] == clase["id"] and r["semilla"] == SEMILLA), None)
    if reto is None:
        reto = await repo.crear_reto(clase["id"], NIVEL, SEMILLA, 2, None)

    ids = {}
    for usuario, nombre, color in ESTUDIANTES:
        u = await repo.crear_usuario(usuario, nombre, color) or await repo.buscar_usuario(usuario)
        ids[usuario] = u["id"]
        await repo.inscribir(clase["id"], u["id"])   # False si ya estaba: no duplica

    # Los intentos solo la primera vez: si el reto ya tiene intentos de demo, no se repiten
    if not await repo.intentos(reto_id=reto["id"]):
        for sala, segundos, completado, por_usuario in INTENTOS:
            for usuario, errores in por_usuario.items():
                await repo.guardar_intento(reto["id"], sala, ids[usuario], segundos, errores, completado)
                if completado:   # el historial y las estadísticas del admin
                    await repo.guardar_mision(ids[usuario], "laberinto", sala, segundos, sum(errores.values()))

    escribir_credenciales(ruta, contrasena, clase["codigo"])
    return {"docente": DOCENTE, "contrasena": contrasena, "clase": CLASE,
            "codigo": clase["codigo"], "reto_id": reto["id"], "semilla": SEMILLA,
            "credenciales": ruta}


async def limpiar(repo: repositorio.Repositorio, carpeta: pathlib.Path):
    # Todos los *_demo: también los estudiantes que se crearon en vivo en la presentación
    await repo.borrar_datos_demo(DOCENTE, await repo.usuarios_demo())
    (carpeta / ARCHIVO_CREDENCIALES).unlink(missing_ok=True)


async def abrir_repo(sqlite: str | None = None) -> repositorio.Repositorio:
    """PostgreSQL si hay DATABASE_URL (como server.py); si no, el SQLite indicado."""
    if os.getenv("DATABASE_URL") and sqlite is None:
        repo = await repositorio.abrir_postgres(os.environ["DATABASE_URL"])
    else:
        repo = repositorio.abrir_sqlite(sqlite or os.getenv("SQLITE_RUTA") or "quimica.db")
    await repo.crear_esquema()
    return repo


async def ejecutar(accion: str, carpeta: pathlib.Path, sqlite: str | None = None) -> int:
    repo = await abrir_repo(sqlite)
    try:
        if accion == "sembrar":
            r = await sembrar(repo, carpeta)
            linea = "=" * 62
            print(linea)
            print("  Datos de demo listos")
            print(linea)
            print(f"  Docente:     {r['docente']}   contraseña: {r['contrasena']}")
            print(f"  Clase:       {r['clase']}   código: {r['codigo']}")
            print(f"  Reto:        laberinto (salas 1 a 5), semilla {r['semilla']}")
            print(f"  Estudiantes: {', '.join(u for u, _, _ in ESTUDIANTES)} (sin contraseña)")
            print(f"  Guardado en: {r['credenciales']}")
            print(linea)
        elif accion == "limpiar":
            await limpiar(repo, carpeta)
            print("Datos de demo borrados (docente_demo, su clase, su reto y los usuarios *_demo).")
        else:
            print("Uso: demo.py sembrar|limpiar")
            return 1
        return 0
    finally:
        await repo.cerrar()


if __name__ == "__main__":
    # Dentro del contenedor del servidor dedicado: usa DATABASE_URL del compose
    sys.exit(asyncio.run(ejecutar(sys.argv[1] if len(sys.argv) > 1 else "", pathlib.Path.cwd())))
