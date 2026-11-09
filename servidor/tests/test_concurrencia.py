"""
El juego no se congela mientras la BD trabaja.

sqlite3 es sincrónico: si una consulta corriera en el event loop, una estadística pesada
del panel dejaría a todos los jugadores sin respuesta hasta que termine. El backend la
corre en un hilo (asyncio.to_thread + threading.Lock) y pandas también va en un hilo.
Este test lo MIDE: con muchos eventos cargados, pide /api/estadisticas y, mientras
tanto, un jugador hace ping por TCP; cada pong tiene que llegar rápido.

Va contra los dos motores con SQL (en memoria no hay consulta que pueda bloquear).
"""
import asyncio
import time

import server

MOTORES = ("sqlite", "postgres")
# Con 500 000 errores, la consulta SQL de las estadísticas tarda ~0,8 s POR SÍ SOLA
# (sin contar pandas): si corriera en el loop, el juego quedaría mudo ese tiempo.
EVENTOS = 500_000
PING_MAXIMO_S = 0.25   # un jugador nota el corte mucho antes de 1 s; 250 ms es holgado
PANDAS_MAXIMO_S = 0.6  # ver test_el_ping_responde_durante_la_estadistica_completa


async def cargar_errores(n: int, usuario: str):
    """Inserta n errores reaccion_fallida de una vez, generados por la propia BD (un
    CTE recursivo, que los dos motores entienden): con un INSERT por fila la carga
    tardaría más que la consulta que se quiere medir."""
    d = server.db.d
    await server.db.bd.execute(f"""
        WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < {int(n)})
        INSERT INTO eventos (tipo, detalle)
        SELECT 'reaccion_fallida',
               CAST('{{"usuario": "{usuario}", "recibido": "Na", "esperado": ["H", "O"], "sala": "X"}}'
                    AS {d.json})
        FROM n""")


async def huecos_de_ping(jugador, tarea) -> list[float]:
    """Hace ping sin parar mientras `tarea` corre y devuelve los HUECOS entre pongs
    consecutivos (y desde el arranque hasta el primero). Se mide el hueco y no el ida y
    vuelta de cada ping: si el loop se congela justo entre dos pings (durante el sleep),
    el ida y vuelta sale corto y el congelamiento no se vería; el hueco sí lo muestra."""
    huecos = []
    anterior = time.perf_counter()
    while not tarea.done():
        await jugador.env(t="ping")
        await jugador.rec("pong", timeout=5)
        ahora = time.perf_counter()
        huecos.append(ahora - anterior)
        anterior = ahora
        await asyncio.sleep(0.01)
    return huecos


async def test_el_ping_responde_mientras_corre_la_consulta_de_estadisticas(servidor_juego, bot, motor):
    """Lo que se exige: la CONSULTA pesada (la de las estadísticas del panel) no frena
    al juego. Contraprueba hecha: con el backend SQLite sin to_thread, este test falla
    con un hueco de ~0,8 s."""
    jugador = await bot(servidor_juego, "ana_test")   # el usuario debe existir para contar sus errores
    await cargar_errores(EVENTOS, "ana_test")

    t0 = time.perf_counter()
    consulta = asyncio.create_task(server.db.datos_estadisticas())
    huecos = await huecos_de_ping(jugador, consulta)
    errores, _ = await consulta
    duracion = time.perf_counter() - t0

    assert len(errores) == EVENTOS
    # El test solo prueba algo si la consulta tardó mucho más que el máximo permitido
    assert duracion > 2 * PING_MAXIMO_S, f"la consulta tardó solo {duracion:.2f} s: sube EVENTOS"
    peor = max(huecos)
    print(f"\n[{motor}] consulta {duracion:.2f} s · {len(huecos)} pongs · peor hueco {peor * 1000:.0f} ms")
    assert peor < PING_MAXIMO_S, (f"el juego no respondió durante {peor * 1000:.0f} ms mientras corría "
                                  f"la consulta ({duracion:.2f} s): el event loop quedó bloqueado")


async def test_el_ping_responde_durante_la_estadistica_completa(api, h, servidor_juego, bot, motor):
    """De punta a punta (consulta + json + pandas por /api/estadisticas). pandas va en
    un hilo, pero armar el DataFrame es una sola llamada en C que retiene el GIL: con
    500 000 errores eso da cortes de ~0,2-0,3 s. Se exige que ningún corte se acerque a
    la duración total (el cálculo no se serializa con el juego), con un margen propio."""
    jugador = await bot(servidor_juego, "ana_test")
    await cargar_errores(EVENTOS, "ana_test")

    t0 = time.perf_counter()
    estadistica = asyncio.create_task(api.get("/api/estadisticas", headers=h))
    huecos = await huecos_de_ping(jugador, estadistica)
    r = await estadistica
    duracion = time.perf_counter() - t0

    assert r.status_code == 200 and r.json()["resumen"]["errores_totales"] == EVENTOS
    peor = max(huecos)
    print(f"\n[{motor}] estadística completa {duracion:.2f} s · {len(huecos)} pongs · "
          f"peor hueco {peor * 1000:.0f} ms")
    assert peor < PANDAS_MAXIMO_S and peor < duracion / 4, (
        f"el juego no respondió durante {peor * 1000:.0f} ms de una estadística de {duracion:.2f} s")
