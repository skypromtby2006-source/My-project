"""
El nivel es un dato. `servidor/niveles/laberinto_01.json` es la fuente de verdad
de la geometría (una grilla de texto por lado) y de los 5 puzzles. Este módulo lo
carga, **sortea los números de cada partida dentro de rangos que SIEMPRE dan
enteros** y valida las respuestas.

Por qué va acá y no mezclado en server.py: así se puede probar el diseño de los
5 puzzles sin levantar el servidor TCP ni abrir Unity (regla del Sprint 1: el
nivel se valida sin ver la pantalla). El cliente solo manda intenciones; el
servidor sortea y valida con lo de este módulo.

El análisis de por qué estos rangos y qué ajustes de §2 quedaron pendientes de
decisión del cliente está en docs/reportes/fase-s4-1.md.
"""
import json
import pathlib
import random

RUTA_NIVELES = pathlib.Path(__file__).resolve().parent / "niveles"

# Masas molares de secundaria (g/mol). Na y Cl dan .5 a propósito: es lo que se
# enseña (Cl = 35,5). El sorteo lo tolera porque n es par (ver más abajo).
MASA = {"H": 1.0, "C": 12.0, "N": 14.0, "O": 16.0, "Na": 23.0, "Cl": 35.5}

# Los 5 conceptos, en el orden en que se enseña estequiometría (SPRINT4 §2).
CONCEPTOS = ["balanceo", "mol", "masa", "limitante", "rendimiento"]

# n = mol de agua que fabrica la Sala 1 y que recorre TODO el encadenamiento.
# DEBE ser múltiplo de 6 para que las 5 salas den enteros a la vez:
#   - par        -> O2 (sala 1) y H2 (sala 2) enteros; gramos de sala 3 enteros
#   - múlt. de 3 -> NH3 (sala 4, reactivo limitante) entero
# 6 = mcm(2, 3). Ver el informe S4-1, sección "Que los números cierren".
BASE_N = [6, 12, 18, 24]
RENDIMIENTOS = [60, 70, 75, 80, 90]  # % que puede mostrar el horno de la Sala 5


def masa_molar(atomos: dict) -> float:
    """Masa molar a partir de los átomos, p. ej. {'Na': 1, 'Cl': 1} -> 58.5."""
    return round(sum(MASA[e] * k for e, k in atomos.items()), 1)


def cargar(nombre: str = "laberinto_01") -> dict:
    ruta = RUTA_NIVELES / f"{nombre}.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def sortear(rng: random.Random | None = None) -> dict:
    """Sortea los números de una partida.

    Devuelve un dict con, por sala, los datos que el servidor mete en `inicio`
    (lo visible) y la respuesta correcta en `resp` (lo que el servidor guarda
    para validar y que NUNCA viaja al cliente). `produce` es lo que baja por el
    montacargas a la sala siguiente: ese es el encadenamiento.
    """
    rng = rng or random.Random()
    n = rng.choice(BASE_N)          # mol de agua base
    p = rng.choice(RENDIMIENTOS)    # rendimiento de la sala 5

    h2_sala2 = n // 2               # subproducto de la sala 2 que limita la sala 4
    nh3 = (2 * h2_sala2) // 3       # limitante H2: NH3 = 2/3 * H2 = n/3
    ch4 = nh3                       # "combustible" que llega al horno (ver ajuste S4-1)
    co2_teorica_g = masa_molar({"C": 1, "O": 2}) * ch4    # 44 g/mol * mol
    real_g = round(co2_teorica_g * p / 100, 1)            # lo que muestra el horno

    return {
        "base_n": n,
        1: {"concepto": "balanceo",
            "pide_h2o_mol": n,
            "coeficientes": {"H2": 2, "O2": 1, "H2O": 2},
            "resp": {"H2_mol": n, "O2_mol": n // 2},
            "produce": {"agua_mol": n}},
        2: {"concepto": "mol",
            "agua_mol": n,
            "resp": {"Na_mol": n},
            "produce": {"naoh_mol": n, "h2_mol": h2_sala2}},
        3: {"concepto": "masa",
            "naoh_mol": n,
            "hcl_g": masa_molar({"H": 1, "Cl": 1}) * n,        # 36.5 * n
            "resp": {"nacl_g": masa_molar({"Na": 1, "Cl": 1}) * n},  # 58.5 * n
            "produce": {"nacl_mol": n}},
        4: {"concepto": "limitante",
            "h2_mol": h2_sala2,
            "resp": {"nh3_mol": nh3},
            "produce": {"nh3_mol": nh3}},
        5: {"concepto": "rendimiento",
            "ch4_mol": ch4,
            "teorica_g": co2_teorica_g,
            "real_g": real_g,
            "resp": {"rendimiento_pct": p}},
    }


def comparar(sorteo_sala: dict, clave: str, recibido) -> tuple[bool, object]:
    """Compara la respuesta de un jugador con la correcta. Devuelve (ok, esperado).
    El que llama arma el evento error_estequiometria con esperado/recibido."""
    esperado = sorteo_sala["resp"][clave]
    if isinstance(esperado, float):
        ok = abs(esperado - float(recibido)) < 1e-6
    else:
        ok = esperado == recibido
    return ok, esperado


def palanca_ok(t_wizard: float, t_player: float, ventana: float = 2.0) -> bool:
    """La puerta se abre solo si las dos palancas bajan con menos de `ventana`
    segundos de diferencia (SPRINT4 §1, "apertura conjunta"). Si la baja uno
    solo, el otro nunca llega y la diferencia crece: no abre."""
    return abs(t_wizard - t_player) < ventana
