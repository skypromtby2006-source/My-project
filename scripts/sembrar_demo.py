#!/usr/bin/env python3
"""Sembrar los datos de demo de la presentación (ver servidor/demo.py).

Uso: scripts/sembrar_demo.py [ruta/a/quimica.db]
  - Sin argumento y con DATABASE_URL puesta: PostgreSQL (servidor dedicado).
  - Sin argumento y sin DATABASE_URL: servidor/quimica.db (el SQLite del servidor local).
  - En Windows, con el paquete: Servidor/sembrar_demo.bat (no necesita Python).
Las credenciales quedan en demo_credenciales.txt, junto a la base de datos.
"""
import asyncio
import os
import pathlib
import sys

SERVIDOR = pathlib.Path(__file__).resolve().parent.parent / "servidor"
sys.path.insert(0, str(SERVIDOR))
import demo  # noqa: E402

if __name__ == "__main__":
    sqlite = sys.argv[1] if len(sys.argv) > 1 else None
    if sqlite is None and not os.getenv("DATABASE_URL"):
        sqlite = str(SERVIDOR / "quimica.db")
    carpeta = pathlib.Path(sqlite).resolve().parent if sqlite else pathlib.Path.cwd()
    sys.exit(asyncio.run(demo.ejecutar("sembrar", carpeta, sqlite)))
