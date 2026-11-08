"""
Estadísticas del panel calculadas con pandas.

Por qué pandas y no un GROUP BY en SQL: es la evidencia concreta del uso de Python +
pandas para el "análisis de errores frecuentes" que justifica el perfil de
investigación (MDs/SPRINT3.md §1). Además funciona igual con y sin base de datos:
los datos se cargan en un DataFrame y desde ahí el cálculo es el mismo.
"""
import json

import pandas as pd


async def cargar(juego) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (errores, misiones) como DataFrames, vengan de PostgreSQL o de la memoria."""
    if juego.db is None:
        errores = [{**e["detalle"], "fecha": e["fecha"]} for e in juego.eventos_mem if e["tipo"] == "reaccion_fallida"]
        misiones = list(juego.misiones_mem)
    else:
        async with juego.db.acquire() as c:
            errores = [{**json.loads(f["detalle"]), "fecha": f["fecha"]} for f in await c.fetch(
                "SELECT detalle, fecha FROM eventos WHERE tipo = 'reaccion_fallida'")]
            misiones = [dict(f) for f in await c.fetch(
                "SELECT u.usuario, m.mision, m.duracion_s, m.errores, m.fecha "
                "FROM misiones_completadas m JOIN usuarios u ON u.id = m.usuario_id")]
    df_err = pd.DataFrame(errores, columns=["usuario", "recibido", "esperado", "fecha"])
    df_mis = pd.DataFrame(misiones, columns=["usuario", "mision", "duracion_s", "errores", "fecha"])
    return df_err, df_mis


def calcular(df_err: pd.DataFrame, df_mis: pd.DataFrame) -> dict:
    # 1. Errores por elemento: qué elemento se lleva mal al reactor con más frecuencia
    por_elemento = (df_err.groupby("recibido").size().sort_values(ascending=False)
                    .rename("veces").reset_index().rename(columns={"recibido": "elemento"}))
    total_err = int(len(df_err))
    por_elemento["porcentaje"] = (por_elemento["veces"] / max(total_err, 1) * 100).round(1)
    por_elemento["usuarios"] = por_elemento["elemento"].map(df_err.groupby("recibido")["usuario"].nunique())

    # 2. Confusiones: "llevó X cuando faltaba Y". explode() abre la lista de faltantes en filas
    conf = df_err.assign(faltaba=df_err["esperado"].apply(lambda l: sorted(set(l or [])))).explode("faltaba")
    conf = conf.dropna(subset=["faltaba"])
    confusiones = (conf.groupby(["recibido", "faltaba"]).size().sort_values(ascending=False).head(10)
                   .rename("veces").reset_index().rename(columns={"recibido": "llevo"}))

    # 3. Tiempo por misión
    por_mision = (df_mis.groupby("mision").agg(completadas=("duracion_s", "size"),
                                               promedio_s=("duracion_s", "mean"),
                                               mejor_s=("duracion_s", "min"),
                                               errores_promedio=("errores", "mean"))
                  .round(1).reset_index())

    # 4. Misiones completadas por día (últimos 14 días con datos)
    if len(df_mis):
        dias = pd.to_datetime(df_mis["fecha"], utc=True).dt.tz_convert(None).dt.strftime("%Y-%m-%d")
        por_dia = (df_mis.assign(dia=dias).groupby("dia")
                   .agg(completadas=("mision", "size"), usuarios=("usuario", "nunique"))
                   .sort_index().tail(14).reset_index())
    else:
        por_dia = pd.DataFrame(columns=["dia", "completadas", "usuarios"])

    # 5. Usuarios con más errores (para saber a quién reforzar)
    por_usuario = (df_err.groupby("usuario").size().sort_values(ascending=False).head(10)
                   .rename("errores").reset_index())

    def filas(df):
        # to_dict con tipos de Python: los int64/float64 de numpy no se pueden pasar a JSON
        return json.loads(df.to_json(orient="records"))

    return {
        "resumen": {"errores_totales": total_err, "misiones_completadas": int(len(df_mis)),
                    "usuarios_con_errores": int(df_err["usuario"].nunique()),
                    "usuarios_con_misiones": int(df_mis["usuario"].nunique())},
        "errores_por_elemento": filas(por_elemento),
        "confusiones": filas(confusiones),
        "por_mision": filas(por_mision),
        "por_dia": filas(por_dia),
        "usuarios_con_mas_errores": filas(por_usuario),
    }


async def obtener(juego) -> dict:
    df_err, df_mis = await cargar(juego)
    return calcular(df_err, df_mis)
