"""
Captura de logs del servidor para el panel web.

Un logging.Handler que, por cada línea de log:
  1. la guarda en un buffer en memoria (las últimas 2000),
  2. la empuja a los WebSocket del panel que estén abiertos (logs en vivo),
  3. la encola para guardarla en la tabla logs de PostgreSQL.

Por qué la BD se escribe en lotes cada 2 s y no en cada línea: un INSERT por línea
pondría una espera de red dentro de cada log.info() del juego. Con la cola, el juego
solo hace un append en memoria y una tarea aparte vacía la cola.
"""
import asyncio
import collections
import logging
from datetime import datetime, timezone

MAXIMO_MEMORIA = 2000
DIAS_CONSERVADOS = 30
NIVELES = ("INFO", "WARNING", "ERROR")


class RegistroLogs(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.buffer: collections.deque[dict] = collections.deque(maxlen=MAXIMO_MEMORIA)
        self.pendientes: list[dict] = []          # aún sin guardar en la BD
        self.suscriptores: set[asyncio.Queue] = set()  # un WebSocket del panel = una cola
        self.siguiente_id = 1                      # id propio para el modo sin BD
        self.db = None

    def emit(self, record: logging.LogRecord):
        try:
            # CRITICAL se muestra como ERROR: el panel filtra por los 3 niveles del brief
            nivel = record.levelname if record.levelname in NIVELES else (
                "ERROR" if record.levelno >= logging.ERROR else "INFO")
            mensaje = record.getMessage()
            if record.exc_info:
                # La traza completa queda en el panel: sin ella, un ERROR no se puede diagnosticar
                mensaje += "\n" + logging.Formatter().formatException(record.exc_info)
            entrada = {"id": self.siguiente_id, "nivel": nivel, "mensaje": mensaje,
                       "fecha": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds")}
            self.siguiente_id += 1
            self.buffer.append(entrada)
            if self.db is not None:
                self.pendientes.append(entrada)
            for cola in list(self.suscriptores):
                if cola.full():
                    # Un navegador lento no debe hacer crecer la memoria sin límite: pierde líneas en vivo
                    continue
                cola.put_nowait({"tipo": "log", **entrada})
        except Exception:
            self.handleError(record)

    # --------------------------------------------------------- base de datos
    async def conectar_bd(self, db):
        """Activa la escritura en PostgreSQL y borra los logs de más de 30 días."""
        self.db = db
        async with db.acquire() as c:
            borrados = await c.execute(
                f"DELETE FROM logs WHERE fecha < now() - interval '{DIAS_CONSERVADOS} days'")
        logging.getLogger("servidor").info("Logs de más de %d días borrados (%s)", DIAS_CONSERVADOS, borrados)

    async def guardar_en_lotes(self, cada_s: float = 2.0):
        while True:
            await asyncio.sleep(cada_s)
            await self.vaciar()

    async def vaciar(self):
        if self.db is None or not self.pendientes:
            return
        lote, self.pendientes = self.pendientes, []
        try:
            async with self.db.acquire() as c:
                await c.executemany(
                    "INSERT INTO logs (nivel, mensaje, fecha) VALUES ($1, $2, $3)",
                    [(e["nivel"], e["mensaje"], datetime.fromisoformat(e["fecha"])) for e in lote])
        except Exception as e:
            # No se usa log.warning: esa línea volvería a entrar en la cola y, con la BD
            # caída, se generaría una línea nueva cada 2 s para siempre.
            print(f"No se pudieron guardar {len(lote)} logs en la BD: {e}", flush=True)

    # --------------------------------------------------------- consultas
    async def consultar(self, nivel: str = "", buscar: str = "", pagina: int = 1, por_pagina: int = 100) -> dict:
        nivel = nivel.upper() if nivel.upper() in NIVELES else ""
        pagina = max(1, pagina)
        if self.db is None:
            filas = [e for e in reversed(self.buffer)
                     if (not nivel or e["nivel"] == nivel) and buscar.lower() in e["mensaje"].lower()]
            total = len(filas)
            filas = filas[(pagina - 1) * por_pagina: pagina * por_pagina]
            return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "logs": filas}
        # Antes de consultar se vacía la cola: si no, lo último que se ve en vivo no aparecería
        await self.vaciar()
        condiciones, args = [], []
        if nivel:
            args.append(nivel)
            condiciones.append(f"nivel = ${len(args)}")
        if buscar:
            args.append(f"%{buscar}%")
            condiciones.append(f"mensaje ILIKE ${len(args)}")
        donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        async with self.db.acquire() as c:
            total = await c.fetchval(f"SELECT count(*) FROM logs {donde}", *args)
            filas = await c.fetch(
                f"SELECT id, nivel, mensaje, fecha FROM logs {donde} ORDER BY id DESC "
                f"LIMIT {por_pagina} OFFSET {(pagina - 1) * por_pagina}", *args)
        return {"total": total, "pagina": pagina, "por_pagina": por_pagina,
                "logs": [{"id": f["id"], "nivel": f["nivel"], "mensaje": f["mensaje"],
                          "fecha": f["fecha"].isoformat(timespec="milliseconds")} for f in filas]}

    def recientes(self, n: int = 200) -> list[dict]:
        return list(self.buffer)[-n:]


registro = RegistroLogs()


def instalar():
    """Engancha el registro al logger raíz: así también se capturan los errores de uvicorn."""
    raiz = logging.getLogger()
    if registro not in raiz.handlers:
        raiz.addHandler(registro)
    return registro
