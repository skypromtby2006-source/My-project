"""
Prueba rápida del servidor sin Unity: simula 2 jugadores.
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


async def main():
    ana, beto = C("Ana"), C("Beto")
    await ana.conectar(); await beto.conectar()
    await ana.env(t="hola", nombre="Ana"); await ana.rec("bienvenido")
    await beto.env(t="hola", nombre="Beto"); await beto.rec("bienvenido")

    print("1) Ana crea sala")
    await ana.env(t="crear_sala", nombre_sala="Lab 1", maximo=4)
    codigo = (await ana.rec("sala"))["sala"]["id"]

    print("2) Beto lista y se une a", codigo)
    await beto.env(t="listar")
    assert any(s["id"] == codigo for s in (await beto.rec("salas"))["lista"])
    await beto.env(t="unirse", sala_id=codigo.lower())
    await beto.rec("sala"); await ana.rec("sala")

    print("3) Ana intenta iniciar sin que Beto esté listo (debe fallar)")
    await ana.env(t="iniciar"); await ana.rec("error")

    print("4) Beto listo, Ana inicia")
    await beto.env(t="listo", valor=True); await beto.rec("sala"); await ana.rec("sala")
    await ana.env(t="iniciar"); await ana.rec("inicio"); await beto.rec("inicio")

    print("5) Beto se mueve, Ana recibe la posición")
    await beto.env(t="pos", x=1.5, y=0, z=2, ry=90)
    p = await ana.rec("pos"); assert p["x"] == 1.5

    print("6) Unirse a sala inexistente")
    await beto.env(t="unirse", sala_id="ZZZZ"); await beto.rec("error")

    print("7) Ana se desconecta: Beto pasa a ser anfitrión")
    ana.w.close()
    await beto.rec("salio")
    s = await beto.rec("sala"); assert s["sala"]["host"] != ""
    print("\nTODO OK ✔")


asyncio.run(main())
