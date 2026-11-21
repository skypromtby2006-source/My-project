"""Rol docente en la capa de datos (revisión 20/11): docentes, clases, inscripciones,
retos e intentos. Solo SQLite y PostgreSQL: el rol docente necesita una BD."""
import auth
import server

MOTORES = ("sqlite", "postgres")


def test_hash_de_contrasena_con_scrypt():
    h = auth.hash_contrasena("clave-larga-1")
    assert h.startswith("scrypt$") and "clave-larga-1" not in h
    assert auth.verificar_contrasena("clave-larga-1", h)
    assert not auth.verificar_contrasena("otra", h)
    assert not auth.verificar_contrasena("clave-larga-1", "basura")
    # Sal aleatoria: la misma contraseña da otro hash
    assert auth.hash_contrasena("clave-larga-1") != h


async def test_docente_clase_inscripcion_reto_e_intento(motor):
    db = server.db
    doc = await db.crear_docente("profe", "Profe Ana", auth.hash_contrasena("x" * 8))
    assert doc["activo"] is True
    assert await db.crear_docente("profe", "Otro", "h") is None   # usuario repetido
    assert (await db.buscar_docente("profe"))["hash"].startswith("scrypt$")

    clase = await db.crear_clase(doc["id"], "3°A", "ABCD2345")
    assert await db.crear_clase(doc["id"], "Otra", "ABCD2345") is None   # código repetido
    est = await db.crear_usuario("estu1", "Estu", "#3FA9F5")
    assert await db.inscribir(clase["id"], est["id"]) is True
    assert await db.inscribir(clase["id"], est["id"]) is False   # ya estaba
    assert [i["usuario"] for i in await db.inscritos(clase["id"])] == ["estu1"]
    assert (await db.clases_de_docente(doc["id"]))[0]["inscritos"] == 1
    assert (await db.clase_por_codigo("ABCD2345"))["docente"] == "Profe Ana"
    assert await db.estudiantes_de_docente(doc["id"]) == {"estu1"}

    reto = await db.crear_reto(clase["id"], "laberinto_01", 1234, 2, None)
    assert reto["docente_id"] == doc["id"] and reto["abierto"] is True and reto["tiempo_limite_s"] is None
    assert [r["id"] for r in await db.retos_abiertos_de_usuario(est["id"])] == [reto["id"]]

    await db.guardar_intento(reto["id"], "AB12", est["id"], 95.5, {"mol": 2}, True)
    filas = await db.intentos(reto_id=reto["id"])
    assert filas[0]["errores_concepto"] == {"mol": 2} and filas[0]["completado"] is True
    assert len(await db.intentos(usuario="estu1", docente_id=doc["id"])) == 1
    assert (await db.retos_de_docente(doc["id"]))[0]["jugaron"] == 1

    await db.cerrar_reto(reto["id"])
    assert await db.retos_abiertos_de_usuario(est["id"]) == []
    assert await db.fijar_docente_activo("profe", False)
    assert (await db.buscar_docente("profe"))["activo"] is False
    assert not await db.fijar_docente_activo("nadie", False)
    assert (await db.listar_docentes())[0]["clases"] == 1
