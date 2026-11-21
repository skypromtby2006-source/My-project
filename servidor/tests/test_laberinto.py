"""
Tests de integración del laberinto (S4-1): recorren cada sala por el protocolo TCP
real (dial / interactuar / palanca), con las respuestas correctas y una incorrecta
por concepto, más la ventana de 2 s de las palancas.

Las respuestas correctas no viajan al cliente; el test las lee del objeto Partida
en memoria (server.salas[...].partida.sorteo), igual que haría un test de caja gris.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import nivel   # noqa: E402
import server  # noqa: E402
from conftest import esperar, eventos, misiones  # noqa: E402


def otro_lado(lado: str) -> str:
    return "player" if lado == "wizard" else "wizard"


async def accion(emisor, otro, **msg):
    """Envía una intención y espera el sala_estado en los DOS bots: así el test
    queda sincronizado con el procesamiento del servidor y los buffers no crecen."""
    await emisor.env(**msg)
    await emisor.rec("sala_estado")
    await otro.rec("sala_estado")


async def iniciar_laberinto(bot, servidor_juego):
    w = await bot(servidor_juego, "wiz_test", nombre="Wiz")      # anfitrión -> wizard
    p = await bot(servidor_juego, "play_test", nombre="Play")    # se une -> player
    await w.env(t="crear_sala")
    sala = (await w.rec("sala"))["sala"]
    await p.env(t="unirse", sala_id=sala["id"])
    await p.rec("sala")
    await p.listo(w)
    await w.env(t="iniciar", modo="laberinto")
    await w.rec("inicio")
    await p.rec("inicio")
    partida = server.salas[sala["id"]].partida
    return w, p, {"wizard": w, "player": p}, partida


async def set_dial(bots, partida, cid, valor):
    lado = partida.lado_de_consola[cid]
    await accion(bots[lado], bots[otro_lado(lado)], t="dial", consola=cid, valor=valor)


async def activar(bots, partida, obj):
    lado = partida.lado_de_consola[obj]
    await accion(bots[lado], bots[otro_lado(lado)], t="interactuar", obj=obj, accion="abrir")


async def bajar_palancas(w, p, partida):
    """Baja las dos palancas. Si la del Wizard ya abre la puerta (porque la del
    Player quedó bajada hace < 2 s de un intento anterior), no manda la segunda."""
    antes = (partida.sala_num, partida.completada)
    await accion(w, p, t="palanca", puerta="x")
    if (partida.sala_num, partida.completada) != antes:
        return
    await accion(p, w, t="palanca", puerta="x")


async def resolver_sala(w, p, bots, partida):
    num = partida.sala_num
    for cid, val in nivel.requeridos(partida.sorteo, num).items():
        await set_dial(bots, partida, cid, val)
    for obj in nivel.activaciones(num):
        await activar(bots, partida, obj)
    await bajar_palancas(w, p, partida)


# ----------------------------------------------------------------- recorrido completo
async def test_recorrer_las_5_salas_abre_el_porton(servidor_juego, bot):
    w, p, bots, partida = await iniciar_laberinto(bot, servidor_juego)
    for num in range(1, 6):
        assert partida.sala_num == num
        await resolver_sala(w, p, bots, partida)
    assert partida.completada

    # el progreso del Player quedó guardado como "laberinto" (es lo último que se guarda)
    async def guardado():
        return any(x["usuario"] == "play_test" and x["mision"] == "laberinto" for x in await misiones())
    await esperar(guardado)
    tipos = [e["tipo"] for e in await eventos()]
    assert tipos.count("sala_completada") == 5
    assert "nivel_completado" in tipos


# ----------------------------------------------------------------- un error por concepto
async def test_un_error_por_concepto_y_la_puerta_no_abre_con_la_parte_mal(servidor_juego, bot):
    w, p, bots, partida = await iniciar_laberinto(bot, servidor_juego)
    for num in range(1, 6):
        concepto = nivel.concepto(num)
        req = nivel.requeridos(partida.sorteo, num)
        cid, val = next(iter(req.items()))
        malo = val + 1  # un valor incorrecto para ese concepto

        await set_dial(bots, partida, cid, malo)
        err = (await eventos("error_estequiometria"))[-1]
        assert err["detalle"]["concepto"] == concepto and err["detalle"]["sala"] == num
        assert err["detalle"]["recibido"] == malo and err["detalle"]["esperado"] == val

        # Con la parte mal, aunque bajen las dos palancas, la puerta NO abre
        await bajar_palancas(w, p, partida)
        assert partida.sala_num == num and not partida.completada

        # Corrigiendo todo, la sala se completa
        await resolver_sala(w, p, bots, partida)
        esperado = num + 1 if num < 5 else 5
        assert partida.sala_num == esperado

    assert partida.completada
    conceptos = {e["detalle"]["concepto"] for e in await eventos("error_estequiometria")}
    assert conceptos == set(nivel.CONCEPTOS)


# ----------------------------------------------------------------- ventana de 2 s
async def test_la_puerta_solo_abre_si_las_palancas_bajan_en_menos_de_2s(servidor_juego, bot):
    w, p, bots, partida = await iniciar_laberinto(bot, servidor_juego)
    # Parte correcta de la Sala 1
    for cid, val in nivel.requeridos(partida.sorteo, 1).items():
        await set_dial(bots, partida, cid, val)

    # El Wizard bajó su palanca "hace 5 s"; el Player baja ahora -> no abre
    await accion(w, p, t="palanca", puerta="D1")
    partida.palancas["wizard"] -= 5.0
    await accion(p, w, t="palanca", puerta="D1")
    assert partida.sala_num == 1 and not partida.completada

    # Ahora las dos casi a la vez -> abre
    await accion(w, p, t="palanca", puerta="D1")
    await accion(p, w, t="palanca", puerta="D1")
    assert partida.sala_num == 2


# ----------------------------------------------------------------- anti-trampa de lado
async def test_un_lado_no_puede_tocar_la_consola_del_otro(servidor_juego, bot):
    w, p, bots, partida = await iniciar_laberinto(bot, servidor_juego)
    # dial_o2 es del Player; si el Wizard intenta fijarlo, el servidor lo rechaza
    await w.env(t="dial", consola="dial_o2", valor=1)
    assert (await w.rec("error"))["msg"] == "Esa consola no es de tu lado"
