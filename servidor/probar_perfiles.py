"""
Prueba de perfiles y progreso sin Unity: simula 3 jugadores.
Ana es wizard; Beto y Caro son players y cometen errores distintos.
Uso:  python probar_perfiles.py [ip] [puerto]
      python probar_perfiles.py --persistencia <usuario> [ip] [puerto]
La segunda forma solo entra con un usuario creado antes y revisa que su
progreso siga ahí (scripts/probar_perfiles.sh la corre tras reiniciar el servidor).
"""
import asyncio
import json
import sys
import uuid

args = sys.argv[1:]
PERSISTENCIA = args[1] if args[:1] == ["--persistencia"] else None
if PERSISTENCIA:
    args = args[2:]
IP = args[0] if len(args) > 0 else "127.0.0.1"
PUERTO = int(args[1]) if len(args) > 1 else 7777

REACTOR = (0.0, 0.15, 4.0)  # centro del reactor en server.py
ERRORES_BETO = 2  # lo que la fase de persistencia espera encontrar


class C:
    def __init__(self, nombre):
        self.nombre = nombre

    async def conectar(self):
        self.r, self.w = await asyncio.open_connection(IP, PUERTO)
        return self

    async def env(self, **m):
        self.w.write((json.dumps(m) + "\n").encode())
        await self.w.drain()

    async def rec(self, tipo):
        while True:
            m = json.loads(await asyncio.wait_for(self.r.readline(), 3))
            print(f"  [{self.nombre}] <- {m['t']}: {json.dumps(m, ensure_ascii=False)[:110]}")
            if m["t"] == tipo:
                return m

    async def error(self, **m):
        await self.env(**m)
        return (await self.rec("error"))["msg"]

    async def perfil(self):
        await self.env(t="perfil_ver")
        return (await self.rec("perfil"))["progreso"]


async def todos(clientes, tipo):
    return [await c.rec(tipo) for c in clientes]


async def persistencia(usuario):
    print(f"Persistencia: {usuario} vuelve a entrar tras reiniciar el servidor")
    c = await C("Beto").conectar()
    await c.env(t="login", usuario=usuario)
    p = (await c.rec("perfil"))["progreso"]
    assert p["completadas"] == 1 and p["errores_totales"] == ERRORES_BETO, p
    print("\nTODO OK ✔")


async def main():
    s = uuid.uuid4().hex[:6]  # usuarios nuevos en cada corrida: con BD persisten
    ana, beto, caro = C("Ana"), C("Beto"), C("Caro")
    for c in (ana, beto, caro):
        await c.conectar()
        c.usuario = f"{c.nombre.lower()}_{s}"

    print("1) Sin sesión no se puede listar, crear sala ni unirse")
    for m in ({"t": "crear_sala"}, {"t": "listar"}, {"t": "unirse", "sala_id": "ABCD"}, {"t": "perfil_ver"}):
        assert "Inicia sesión" in await ana.error(**m)

    print("2) Registro OK, duplicado y datos inválidos")
    await ana.env(t="registro", usuario=ana.usuario.upper(), nombre="Ana", color="#3fa9f5")
    p = await ana.rec("perfil")
    # Se guarda en minúsculas y con el color normalizado
    assert (p["usuario"], p["nombre"], p["color"]) == (ana.usuario, "Ana", "#3FA9F5")
    assert p["progreso"] == {"completadas": 0, "mejor_tiempo_s": 0, "errores_totales": 0, "historial": []}
    ana.id = p["id"]
    assert "ya existe" in await beto.error(t="registro", usuario=ana.usuario, nombre="X", color="#3FA9F5")
    for malo in ("ab", "a" * 17, "con espacio", "eñe_1", "a-b-c"):
        assert "Usuario inválido" in await beto.error(t="registro", usuario=malo, nombre="X", color="#3FA9F5")
    assert "nombre" in await beto.error(t="registro", usuario=beto.usuario, nombre="  ", color="#3FA9F5")
    assert "nombre" in await beto.error(t="registro", usuario=beto.usuario, nombre="x" * 21, color="#3FA9F5")
    assert "Color" in await beto.error(t="registro", usuario=beto.usuario, nombre="Beto", color="#123456")
    for c, color in ((beto, "#F5D33F"), (caro, "#4FE07A")):
        await c.env(t="registro", usuario=c.usuario, nombre=c.nombre, color=color)
        c.id = (await c.rec("perfil"))["id"]
    assert "Ya iniciaste" in await beto.error(t="login", usuario=beto.usuario)

    print("3) Login inexistente y doble sesión")
    otra = await C("Otra").conectar()
    assert "no encontrado" in await otra.error(t="login", usuario=f"nadie_{s}")
    assert "sesión abierta" in await otra.error(t="login", usuario=ana.usuario)
    otra.w.close()

    print("4) Beto edita su perfil en la sala y los demás lo ven")
    await ana.env(t="crear_sala", nombre_sala="Lab perfiles")
    sala = (await ana.rec("sala"))["sala"]
    assert sala["jugadores"][0]["color"] == "#3FA9F5"
    for c in (beto, caro):
        await c.env(t="unirse", sala_id=sala["id"]); await c.rec("sala")
    await ana.rec("sala"); await ana.rec("sala"); await beto.rec("sala")
    await beto.env(t="perfil_editar", nombre="Beto Nuevo", color="#E04F4F")
    p = await beto.rec("perfil")
    assert (p["usuario"], p["nombre"], p["color"]) == (beto.usuario, "Beto Nuevo", "#E04F4F")
    for c in (ana, caro):
        j = next(x for x in (await c.rec("sala"))["sala"]["jugadores"] if x["id"] == beto.id)
        assert (j["nombre"], j["color"]) == ("Beto Nuevo", "#E04F4F")
    assert "Color" in await beto.error(t="perfil_editar", nombre="Beto", color="rojo")

    print("5-6) Misión: Beto comete 2 errores y Caro 1; luego la completan")
    for c in (beto, caro):
        await c.env(t="listo", valor=True); await todos((ana, beto, caro), "sala")
    await ana.env(t="iniciar")
    mision = (await todos((ana, beto, caro), "inicio"))[0]["mision"]
    por = {}
    for o in mision["objetos"]:
        por.setdefault(o["elemento"], []).append(o["id"])

    async def llevar(c, obj, dx=0.0):
        await c.env(t="agarrar", obj=obj); await todos((ana, beto, caro), "obj")
        await c.env(t="soltar", obj=obj, x=REACTOR[0] + dx, y=REACTOR[1], z=REACTOR[2])
        await todos((ana, beto, caro), "obj")
        return (await todos((ana, beto, caro), "estado"))[0]

    await llevar(beto, por["Na"][0]); await llevar(caro, por["Cl"][0]); await llevar(beto, por["C"][0])
    await llevar(beto, por["H"][0], 0.3); await llevar(beto, por["H"][1], -0.3)
    e = await llevar(caro, por["O"][0])
    assert e["completada"] and e["errores"] == 3

    # Caro va primero: su conexión guardó el progreso de todos, así que cuando
    # responde, los registros de Beto ya están escritos.
    pc = await caro.perfil(); pb = await beto.perfil(); pa = await ana.perfil()
    assert pa == {"completadas": 0, "mejor_tiempo_s": 0, "errores_totales": 0, "historial": []}, pa
    assert pb["completadas"] == 1 and pb["errores_totales"] == ERRORES_BETO, pb
    assert pc["completadas"] == 1 and pc["errores_totales"] == 1, pc
    assert pb["historial"][0]["errores"] == ERRORES_BETO and pc["historial"][0]["errores"] == 1
    # La misión simulada dura milisegundos y redondea a 0.0: se compara contra el historial
    assert pb["mejor_tiempo_s"] >= 0 and pb["historial"][0]["duracion_s"] == pb["mejor_tiempo_s"]
    assert "T" in pb["historial"][0]["fecha"]  # ISO 8601

    print("7) Beto se desconecta y vuelve a entrar: el usuario se liberó y el progreso sigue")
    beto.w.close()
    await ana.rec("salio")
    beto2 = await C("Beto").conectar()
    await beto2.env(t="login", usuario=beto.usuario)
    p = await beto2.rec("perfil")
    assert p["nombre"] == "Beto Nuevo" and p["progreso"]["completadas"] == 1
    print(f"\nUSUARIO_PERSISTENCIA={beto.usuario}")
    print("TODO OK ✔")


asyncio.run(persistencia(PERSISTENCIA) if PERSISTENCIA else main())
