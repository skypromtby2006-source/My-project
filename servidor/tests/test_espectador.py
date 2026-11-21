"""Docente espectador en el juego (revisión 20/11, 🟡): entra con usuario y contraseña,
mira cualquier sala sin contar para el límite y sin poder interactuar."""
import asyncio
import json

import pytest

import auth
import server
from test_laberinto import iniciar_laberinto

MOTORES = ("sqlite", "postgres")

# Conexiones de docente abiertas en el test: el servidor de prueba espera a que terminen
# todos sus clientes al cerrarse, así que una que quede abierta cuelga el teardown.
_abiertas: list = []


@pytest.fixture(autouse=True)
def cerrar_docentes(servidor_juego):   # se desmonta antes que el servidor
    yield
    while _abiertas:
        _abiertas.pop().close()


async def docente(servidor_juego, contrasena="clave-docente-1"):
    await server.db.crear_docente("profe_ana", "Profe Ana", auth.hash_contrasena("clave-docente-1"))
    r, w = await asyncio.open_connection("127.0.0.1", servidor_juego)
    _abiertas.append(w)

    class D:
        async def env(self, **m):
            w.write((json.dumps(m) + "\n").encode())
            await w.drain()

        async def rec(self, tipo, timeout=3):
            while True:
                m = json.loads(await asyncio.wait_for(r.readline(), timeout))
                if m["t"] == tipo:
                    return m

        async def nada(self, tipo, espera=0.4):
            """True si NO llega ningún mensaje de ese tipo en `espera` segundos."""
            try:
                await self.rec(tipo, timeout=espera)
                return False
            except asyncio.TimeoutError:
                return True

        def cerrar(self):
            w.close()
    d = D()
    await d.env(t="login_docente", usuario="profe_ana", contrasena=contrasena)
    return d


async def test_contrasena_mala_no_entra(servidor_juego, bot, motor):
    d = await docente(servidor_juego, contrasena="mala")
    assert "incorrectos" in (await d.rec("error"))["msg"]


async def test_espectador_en_partida_en_curso_mira_sin_contar_ni_interactuar(servidor_juego, bot, motor):
    w, p, bots, partida = await iniciar_laberinto(bot, servidor_juego)
    sala_id = next(iter(server.salas))
    d = await docente(servidor_juego)
    perfil = await d.rec("perfil")
    assert perfil["docente"] is True and perfil["nombre"] == "Profe Ana"
    await d.env(t="espectar", sala_id=sala_id.lower())
    esp = await d.rec("espectando")
    assert esp["sala"]["espectadores"] == 1 and esp["sala"]["cantidad"] == 2   # no cuenta como jugador
    inicio = await d.rec("inicio")
    assert inicio["nivel"]["sala"]["sala"] == 1
    # Recibe los movimientos de los jugadores...
    await p.env(t="pos", x=1, y=1, z=2, ry=0)
    assert (await d.rec("pos"))["id"] == p.id
    # ...pero su pos no se reenvía a nadie y sus acciones se rechazan
    await d.env(t="pos", x=9, y=1, z=9, ry=0)
    with pytest.raises(asyncio.TimeoutError):   # el wizard nunca ve un pos del docente
        await w.rec("pos", cuando=lambda m: m["id"] == perfil["id"], timeout=0.4)
    await d.env(t="palanca", puerta="x")
    assert "espectadores" in (await d.rec("error"))["msg"]
    assert not partida.palancas
    await d.env(t="crear_sala")
    assert "espectadores" in (await d.rec("error"))["msg"]
    # El sala_estado de una acción de los jugadores también le llega
    await w.env(t="interactuar", obj="x", accion="abrir")
    assert (await d.rec("sala_estado"))["sala"] == 1
    # Al cerrarse la sala, vuelve a la lista como los demás
    w.cerrar()
    assert "Wizard" in (await d.rec("fuera"))["msg"]
    assert server.salas == {}
    d.cerrar()


async def test_espectador_no_cuenta_para_el_maximo_y_recibe_el_inicio(servidor_juego, bot, motor):
    w = await bot(servidor_juego, "wiz_esp")
    await w.env(t="crear_sala", maximo=2)
    sala = (await w.rec("sala"))["sala"]
    d = await docente(servidor_juego)
    await d.rec("perfil")
    await d.env(t="espectar", sala_id=sala["id"])
    await d.rec("espectando")
    p = await bot(servidor_juego, "play_esp")   # la sala de 2 todavía tiene lugar
    await p.env(t="unirse", sala_id=sala["id"])
    assert (await p.rec("sala"))["sala"]["cantidad"] == 2
    await p.listo(w)
    await w.env(t="iniciar", modo="laberinto")
    assert (await d.rec("inicio"))["nivel"]
    await d.env(t="salir")
    await d.rec("fuera")
    assert server.salas[sala["id"]].espectadores == {}


async def test_un_jugador_no_puede_espectar(servidor_juego, bot, motor):
    b = await bot(servidor_juego, "estu_1")
    await b.env(t="espectar", sala_id="ABCD")
    assert "docente" in (await b.rec("error"))["msg"]
