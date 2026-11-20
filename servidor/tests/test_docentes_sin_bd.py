"""Sin ninguna BD (Plan B2) el rol docente no existe: la API lo dice con un 503 claro."""
MOTORES = ("memoria",)


async def test_sin_bd_el_rol_docente_avisa_que_necesita_la_base(api, h):
    r = await api.post("/api/docentes", headers=h, json={"usuario": "profe_ana", "nombre": "A", "contrasena": "x" * 8})
    assert r.status_code == 503


async def test_sin_bd_unirse_a_clase_da_error(servidor_juego, bot):
    b = await bot(servidor_juego, "estu_1")
    await b.env(t="unirse_clase", codigo="ABCD2345")
    assert "base de datos" in (await b.rec("error"))["msg"]
