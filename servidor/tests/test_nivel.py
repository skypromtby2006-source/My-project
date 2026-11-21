"""
Tests del nivel-como-dato (S4-1). Validan el diseño de los 5 puzzles SIN levantar
el servidor ni Unity: que el sorteo siempre dé enteros, que el encadenamiento
(lo que produce una sala = lo que recibe la siguiente) cierre, y la ventana de
2 s de las palancas.
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import nivel  # noqa: E402


def es_entero(x) -> bool:
    return abs(x - round(x)) < 1e-6


def test_el_json_carga_y_tiene_las_5_salas_y_los_dos_lados():
    n = nivel.cargar()
    assert len(n["salas"]) == 5
    assert [s["concepto"] for s in n["salas"]] == nivel.CONCEPTOS
    for lado in ("wizard", "player"):
        g = n["lados"][lado]["grilla"]
        assert g and len({len(fila) for fila in g}) == 1  # grilla rectangular


def test_masa_molar_de_secundaria():
    assert nivel.masa_molar({"Na": 1, "Cl": 1}) == 58.5
    assert nivel.masa_molar({"H": 1, "Cl": 1}) == 36.5
    assert nivel.masa_molar({"N": 2}) == 28.0


def test_el_sorteo_siempre_da_enteros_en_las_5_salas():
    rng = random.Random(0)
    for _ in range(3000):
        s = nivel.sortear(rng)
        assert s["base_n"] % 6 == 0                      # la condición que lo hace cerrar
        # Sala 1: balanceo -> mol enteros
        assert es_entero(s[1]["resp"]["H2_mol"]) and es_entero(s[1]["resp"]["O2_mol"])
        # Sala 2: mol -> mol entero
        assert es_entero(s[2]["resp"]["Na_mol"])
        # Sala 3: masa -> gramos enteros (pese a las masas molares .5)
        assert es_entero(s[3]["hcl_g"]) and es_entero(s[3]["resp"]["nacl_g"])
        # Sala 4: limitante -> NH3 entero
        assert es_entero(s[4]["resp"]["nh3_mol"])
        # Sala 5: rendimiento -> % entero
        assert es_entero(s[5]["resp"]["rendimiento_pct"])


def test_el_encadenamiento_cierra_entre_salas():
    """Lo que produce una sala es exactamente lo que recibe la siguiente."""
    rng = random.Random(1)
    for _ in range(1000):
        s = nivel.sortear(rng)
        assert s[2]["agua_mol"] == s[1]["produce"]["agua_mol"]        # agua 1 -> 2
        assert s[3]["naoh_mol"] == s[2]["produce"]["naoh_mol"]        # NaOH 2 -> 3
        assert s[4]["h2_mol"] == s[2]["produce"]["h2_mol"]            # H2 2 -> 4 (limitante)
        assert s[5]["nh3_mol"] == s[4]["produce"]["nh3_mol"]          # NH3 4 -> 5 (reactivo real)


def test_el_rendimiento_es_real_sobre_teorica():
    rng = random.Random(2)
    for _ in range(1000):
        s = nivel.sortear(rng)
        pct = s[5]["resp"]["rendimiento_pct"]
        assert abs(s[5]["real_g"] - s[5]["teorica_g"] * pct / 100) < 0.05


def test_requeridos_y_activaciones_por_sala():
    s = nivel.sortear(random.Random(3))
    # Sala 1: hay que fijar los dos diales con los valores correctos
    assert nivel.requeridos(s, 1) == {"dial_h2": s[1]["resp"]["H2_mol"], "dial_o2": s[1]["resp"]["O2_mol"]}
    # Sala 3: además de la balanza, hay que abrir la válvula de NaOH
    assert nivel.requeridos(s, 3) == {"balanza": s[3]["resp"]["nacl_g"]}
    assert nivel.activaciones(3) == ["valvula_naoh"]
    assert nivel.activaciones(1) == []
    assert [nivel.concepto(n) for n in range(1, 6)] == nivel.CONCEPTOS


def test_la_puerta_solo_abre_con_las_dos_palancas_en_menos_de_2s():
    assert nivel.palanca_ok(10.0, 11.5)       # 1.5 s de diferencia -> abre
    assert nivel.palanca_ok(10.0, 10.0)       # a la vez -> abre
    assert not nivel.palanca_ok(10.0, 12.5)   # 2.5 s -> no abre
    assert not nivel.palanca_ok(10.0, 100.0)  # uno solo bajó -> no abre
    assert nivel.palanca_ok(100.0, 98.6)      # el orden no importa


def test_la_semilla_hace_el_sorteo_reproducible(monkeypatch):
    """El hook NIVEL_SEMILLA (probar_build) fija el sorteo: con la misma semilla,
    dos partidas tienen los mismos números, y coinciden con nivel.sortear(Random)."""
    import server  # noqa: E402
    monkeypatch.setattr(server, "SEMILLA_NIVEL", "123")
    p1 = server.Partida()
    p2 = server.Partida()
    assert p1.sorteo == p2.sorteo                         # dos partidas, mismos números
    assert p1.sorteo == nivel.sortear(random.Random(123))  # el orquestador los puede calcular


def test_sin_semilla_el_sorteo_es_al_azar(monkeypatch):
    import server  # noqa: E402
    monkeypatch.setattr(server, "SEMILLA_NIVEL", None)
    # Muy improbable que 5 partidas sorteen todas lo mismo si es al azar.
    sorteos = [tuple(sorted((k, repr(v)) for k, v in server.Partida().sorteo[1].items())) for _ in range(5)]
    assert len(set(sorteos)) > 1
