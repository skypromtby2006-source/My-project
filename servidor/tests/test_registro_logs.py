"""
Los logs del ARRANQUE llegan a la BD: se generan antes de que el registro tenga BD
("Conectado a PostgreSQL" sale justo al conectar, antes de que arranque el panel),
se guardan en memoria y se envían al conectarla. Así aparecen en la página Logs.
"""
import logging

import registro_logs
import server

MOTORES = ("sqlite", "postgres")


async def test_los_logs_del_arranque_se_guardan_al_conectar_la_bd(motor):
    reg = registro_logs.RegistroLogs()   # uno nuevo: todavía sin BD, como al arrancar
    log = logging.getLogger("prueba_arranque")
    log.addHandler(reg)
    try:
        log.info("Conectado a PostgreSQL")
        log.info("Servidor escuchando en 0.0.0.0:7777")
        assert reg.db is None and len(reg.pendientes) == 2   # en memoria, a la espera

        await reg.conectar_bd(server.db)
        assert reg.pendientes == []                          # se enviaron al conectar
        r = await reg.consultar(buscar="Conectado a PostgreSQL")
        assert r["total"] == 1 and r["logs"][0]["nivel"] == "INFO"
        # En el orden en que ocurrieron (el panel muestra lo más nuevo primero)
        # (la tabla es compartida: el fixture también deja su línea de purga)
        mios = ("Servidor escuchando en 0.0.0.0:7777", "Conectado a PostgreSQL")
        todos = [x["mensaje"] for x in (await reg.consultar())["logs"] if x["mensaje"] in mios]
        assert todos == list(mios)
    finally:
        log.removeHandler(reg)


def test_sin_bd_la_memoria_previa_tiene_tope():
    reg = registro_logs.RegistroLogs()
    log = logging.getLogger("prueba_tope")
    log.addHandler(reg)
    try:
        for i in range(registro_logs.MAXIMO_PREVIOS + 50):
            log.info("línea %d", i)
        # Un servidor que nunca tiene BD no acumula para siempre
        assert len(reg.pendientes) == registro_logs.MAXIMO_PREVIOS
    finally:
        log.removeHandler(reg)
