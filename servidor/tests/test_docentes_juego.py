"""Rol docente en el juego (revisión 20/11): unirse a una clase con el código, elegir
el reto en el lobby, jugar con la semilla del reto y guardar un intento por jugador."""
import asyncio
import random

import auth
import nivel
import server
from conftest import esperar
from test_laberinto import resolver_sala, set_dial

MOTORES = ("sqlite", "postgres")


async def preparar_reto(semilla=777, jugadores=2, tiempo=None):
    doc = await server.db.crear_docente("profe_ana", "Profe Ana", auth.hash_contrasena("x" * 8))
    clase = await server.db.crear_clase(doc["id"], "3°A", "ABCD2345")
    reto = await server.db.crear_reto(clase["id"], "laberinto_01", semilla, jugadores, tiempo)
    return clase, reto


async def sala_con_reto(bot, servidor_juego, reto):
    w = await bot(servidor_juego, "wiz_reto", nombre="Wiz")
    p = await bot(servidor_juego, "play_reto", nombre="Play")
    for b in (w, p):
        await b.env(t="unirse_clase", codigo="abcd 2345")   # minúsculas y espacios se toleran
        assert (await b.rec("clase_unida"))["nombre"] == "3°A"
        perfil = await b.rec("perfil")
        assert perfil["clases"] == [{"codigo": "ABCD2345", "nombre": "3°A", "docente": "Profe Ana"}]
    await w.env(t="crear_sala")
    sala = (await w.rec("sala"))["sala"]
    assert [r["id"] for r in sala["retos"]] == [reto["id"]] and sala["reto"] == 0
    await w.env(t="elegir_reto", reto=reto["id"])
    assert (await w.rec("sala", cuando=lambda m: m["sala"]["reto"]))["sala"]["reto"] == reto["id"]
    await p.env(t="unirse", sala_id=sala["id"])
    await p.rec("sala")
    await p.listo(w)
    await w.env(t="iniciar")   # sin modo: con reto siempre es el laberinto
    await w.rec("inicio")
    await p.rec("inicio")
    partida = server.salas[sala["id"]].partida
    return w, p, {"wizard": w, "player": p}, partida, sala["id"]


async def test_codigo_inexistente_da_error(servidor_juego, bot, motor):
    b = await bot(servidor_juego, "estu_1")
    await b.env(t="unirse_clase", codigo="ZZZZ9999")
    assert "No existe la clase" in (await b.rec("error"))["msg"]


async def test_el_reto_usa_su_semilla_y_guarda_un_intento_por_jugador(servidor_juego, bot, motor):
    _, reto = await preparar_reto(semilla=777)
    w, p, bots, partida, sala_id = await sala_con_reto(bot, servidor_juego, reto)
    assert partida.sorteo == nivel.sortear(random.Random(777))
    # Un error de concepto del Player en la sala 1
    cid = next(iter(nivel.requeridos(partida.sorteo, 1)))
    await set_dial(bots, partida, cid, -1)
    culpable = "play_reto" if partida.lado_de_consola[cid] == "player" else "wiz_reto"
    for _ in range(5):
        await resolver_sala(w, p, bots, partida)
    assert partida.completada

    async def dos():
        return len(await server.db.intentos(reto_id=reto["id"])) == 2
    await esperar(dos)
    intentos = {i["usuario"]: i for i in await server.db.intentos(reto_id=reto["id"])}
    assert all(i["completado"] and i["sala"] == sala_id for i in intentos.values())
    assert intentos[culpable]["errores_concepto"] == {nivel.concepto(1): 1}
    # Al cerrarse la sala después no se duplican
    w.cerrar()
    await asyncio.sleep(0.2)
    assert len(await server.db.intentos(reto_id=reto["id"])) == 2


async def test_abandonar_el_reto_guarda_el_intento_sin_completar(servidor_juego, bot, motor):
    _, reto = await preparar_reto()
    w, p, _, _, _ = await sala_con_reto(bot, servidor_juego, reto)
    p.cerrar()

    async def uno():
        return len(await server.db.intentos(reto_id=reto["id"])) == 1
    await esperar(uno)
    assert (await server.db.intentos(reto_id=reto["id"]))[0]["completado"] is False


async def test_tiempo_limite_detiene_la_partida(servidor_juego, bot, motor):
    _, reto = await preparar_reto(tiempo=1)   # la API exige ≥ 60 s; acá directo en la BD
    w, p, _, partida, _ = await sala_con_reto(bot, servidor_juego, reto)
    m = await w.rec("sala_estado", timeout=4)
    assert m["tiempo_agotado"] is True
    intentos = await server.db.intentos(reto_id=reto["id"])
    assert len(intentos) == 2 and not any(i["completado"] for i in intentos)
    await w.env(t="palanca", puerta="x")
    assert "tiempo" in (await w.rec("error"))["msg"]


async def test_sin_reto_se_juega_como_siempre(servidor_juego, bot, motor):
    w = await bot(servidor_juego, "wiz_libre")
    await w.env(t="crear_sala")
    sala = (await w.rec("sala"))["sala"]
    assert sala["retos"] == [] and sala["reto"] == 0


async def test_grupo_mas_grande_que_el_reto_no_puede_iniciar(servidor_juego, bot, motor):
    _, reto = await preparar_reto(jugadores=2)
    w = await bot(servidor_juego, "wiz_reto")
    await w.env(t="unirse_clase", codigo="ABCD2345")
    await w.rec("perfil")
    await w.env(t="crear_sala", maximo=4)
    sala = (await w.rec("sala"))["sala"]
    await w.env(t="elegir_reto", reto=reto["id"])
    # Se consume el "sala" del reto elegido: con solo el Wizard cumple "todos listos" y
    # b.listo(w) lo tomaría por el listo de un jugador (carrera que falló en PostgreSQL)
    await w.rec("sala", cuando=lambda m: m["sala"]["reto"] == reto["id"])
    for n in ("p_uno", "p_dos"):
        b = await bot(servidor_juego, n)
        await b.env(t="unirse", sala_id=sala["id"])
        await b.rec("sala")
        await b.listo(w)
    await w.env(t="iniciar")
    assert "hasta 2" in (await w.rec("error"))["msg"]
