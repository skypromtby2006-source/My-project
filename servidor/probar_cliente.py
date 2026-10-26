"""
Prueba rápida del servidor sin Unity: simula 2 jugadores.
Ana crea la sala (wizard) y Beto se une (player); recorren la misión del agua.
Uso:  python probar_cliente.py [ip] [puerto]
"""
import asyncio
import json
import sys

IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PUERTO = int(sys.argv[2]) if len(sys.argv) > 2 else 7777


class C:
    def __init__(self, nombre):
        self.nombre = nombre

    async def conectar(self):
        self.r, self.w = await asyncio.open_connection(IP, PUERTO)

    async def env(self, **m):
        self.w.write((json.dumps(m) + "\n").encode())
        await self.w.drain()

    async def rec(self, tipo):
        while True:
            m = json.loads(await asyncio.wait_for(self.r.readline(), 3))
            print(f"  [{self.nombre}] <- {m['t']}: {json.dumps(m, ensure_ascii=False)[:110]}")
            if m["t"] == tipo:
                return m


REACTOR = (0.0, 0.15, 4.0)  # centro del reactor en server.py


def rol_de(sala, jugador_id):
    return next(x["rol"] for x in sala["jugadores"] if x["id"] == jugador_id)


async def main():
    ana, beto = C("Ana"), C("Beto")
    await ana.conectar(); await beto.conectar()
    await ana.env(t="hola", nombre="Ana"); ana.id = (await ana.rec("bienvenido"))["id"]
    await beto.env(t="hola", nombre="Beto"); beto.id = (await beto.rec("bienvenido"))["id"]

    print("1) Ana crea sala: es wizard")
    await ana.env(t="crear_sala", nombre_sala="Lab 1", maximo=4)
    sala = (await ana.rec("sala"))["sala"]
    codigo = sala["id"]
    assert rol_de(sala, ana.id) == "wizard"

    print("2) Ana intenta iniciar sola (debe fallar: hacen falta 2)")
    await ana.env(t="iniciar"); assert "2 jugadores" in (await ana.rec("error"))["msg"]

    print("3) Beto lista y se une a", codigo, "como player")
    await beto.env(t="listar")
    assert any(s["id"] == codigo for s in (await beto.rec("salas"))["lista"])
    await beto.env(t="unirse", sala_id=codigo.lower())
    sala = (await beto.rec("sala"))["sala"]; await ana.rec("sala")
    assert rol_de(sala, beto.id) == "player"

    print("4) Ana intenta iniciar sin que Beto esté listo (debe fallar)")
    await ana.env(t="iniciar"); await ana.rec("error")

    print("5) Beto listo, Ana inicia: llega la misión")
    await beto.env(t="listo", valor=True); await beto.rec("sala"); await ana.rec("sala")
    await ana.env(t="iniciar")
    mision = (await ana.rec("inicio"))["mision"]; await beto.rec("inicio")
    assert len(mision["objetos"]) == 6 and mision["estado"]["reactor"] == []
    assert mision["mesa"]["ancho"] > 0 and mision["radio_objeto"] > 0
    por_elem = {}
    for o in mision["objetos"]:
        por_elem.setdefault(o["elemento"], []).append(o)
    na = por_elem["Na"][0]

    print("6) Beto se mueve, Ana recibe la posición")
    await beto.env(t="pos", x=1.5, y=0, z=2, ry=90)
    p = await ana.rec("pos"); assert p["x"] == 1.5

    print("7) Beto agarra Na; Ana intenta agarrar y falla (es wizard)")
    await beto.env(t="agarrar", obj=na["id"])
    assert (await beto.rec("obj"))["obj"]["portador"] == beto.id; await ana.rec("obj")
    await ana.env(t="agarrar", obj=por_elem["H"][0]["id"]); assert "player" in (await ana.rec("error"))["msg"]
    await beto.env(t="agarrar", obj=por_elem["O"][0]["id"]); assert "Ya llevas" in (await beto.rec("error"))["msg"]

    print("8) Beto suelta Na en el reactor: error y vuelve a la mesa")
    await beto.env(t="soltar", obj=na["id"], x=REACTOR[0], y=REACTOR[1], z=REACTOR[2])
    o = (await beto.rec("obj"))["obj"]; await ana.rec("obj")
    assert (o["x"], o["z"], o["portador"]) == (na["x"], na["z"], "")
    e = await beto.rec("estado"); await ana.rec("estado")
    assert e["errores"] == 1 and e["reactor"] == [] and "inestable" in e["mensaje"]

    print("9) Ana señala un H y Beto recibe la señal; Beto no puede señalar")
    await ana.env(t="senalar", obj=por_elem["H"][0]["id"])
    s = await beto.rec("senal"); assert s["obj"] == por_elem["H"][0]["id"] and s["por"] == ana.id
    await ana.rec("senal")
    await beto.env(t="senalar", obj=na["id"]); await beto.rec("error")

    print("10) Beto lleva H, H y O al reactor: misión completada")
    for o in por_elem["H"] + por_elem["O"]:
        await beto.env(t="agarrar", obj=o["id"]); await beto.rec("obj"); await ana.rec("obj")
        await beto.env(t="soltar", obj=o["id"], x=REACTOR[0] + 0.3, y=REACTOR[1], z=REACTOR[2])
        await beto.rec("obj"); await ana.rec("obj")
        e = await beto.rec("estado"); await ana.rec("estado")
    assert e["completada"] and sorted(e["reactor"]) == ["H", "H", "O"] and e["errores"] == 1

    print("11) Ana reinicia: reactor vacío; Beto no puede reiniciar")
    await beto.env(t="reiniciar"); await beto.rec("error")
    await ana.env(t="reiniciar")
    m2 = (await beto.rec("inicio"))["mision"]; await ana.rec("inicio")
    assert m2["estado"] == {"reactor": [], "errores": 0, "completada": False, "mensaje": ""}

    print("12) Unirse a sala inexistente")
    await beto.env(t="unirse", sala_id="ZZZZ"); await beto.rec("error")

    print("13) Beto agarra algo y Ana se desconecta: Beto pasa a ser wizard y suelta el objeto")
    obj = m2["objetos"][0]["id"]
    await beto.env(t="agarrar", obj=obj); await beto.rec("obj"); await ana.rec("obj")
    ana.w.close()
    await beto.rec("salio")
    sala = (await beto.rec("sala"))["sala"]
    assert sala["host"] == beto.id and rol_de(sala, beto.id) == "wizard"
    o = (await beto.rec("obj"))["obj"]; assert o["id"] == obj and o["portador"] == ""
    print("\nTODO OK ✔")


asyncio.run(main())
