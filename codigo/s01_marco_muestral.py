"""
Paso 1 — Marcos muestrales y corpus (diseño de dos estratos).

Entradas: datos_crudos/wikipedia_2011_2025.docx   top 10 anual de Billboard Hot Latin Songs
          datos_crudos/numeros_uno_2011_2025.txt  números uno semanales (Hot Latin Songs / Latin Airplay)
          instrumentos/clasificacion_genero_v1.1.csv
Salidas : datos/marco_completo.csv      150 entradas del top 10 anual (año × posición)
          datos/marco_muestral.csv      canciones únicas de ambos marcos, con clase de género y estrato
          datos/corpus.csv              estrato 1 (censo) + estrato 2 (muestra aleatoria), código C###
          datos/lista_letras.xlsx       lista de trabajo para descargar letras

Reglas (documentadas en el informe, sección 3):
  1. Una canción que aparece en varios años se cuenta una sola vez, en su primer año.
  2. Se incluyen las clases 'urbano' e 'hibrido'; 'no_urbano' se excluye.
  3. Estrato 1: todas las canciones urbanas o híbridas del top 10 anual (censo).
     Estrato 2: canciones que fueron número uno semanal sin entrar al top 10 anual; se sortean
     N_ESTRATO2 con semilla fija, estratificando por periodo con asignación proporcional.
  4. Periodos de cinco años definidos en config.PERIODOS. Peso de diseño = N_h / n_h.
"""
import sys
from pathlib import Path

import docx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
import utilidades as u


# Canciones cuya entrada en el top 10 acredita una remezcla: la letra debe ser la de esa versión,
# para que lo medido coincida con lo que se midió como popular.
REMEZCLAS = {
    "despacito|luis fonsi", "mi gente|j balvin", "reggaeton lento|cnco", "te bote|casper magico",
    "el farsante|ozuna", "con calma|daddy yankee", "calma|pedro capo", "ella quiere beber|anuel aa",
    "hawai|maluma", "la bebe|yng lvcas", "el perdedor|maluma", "subeme la radio|enrique iglesias",
    # estrato 2
    "tattoo remix|rauw alejandro", "calypso|luis fonsi", "mi cama|karol g", "relacion|sech",
    "loco|justin quiles", "porfa|feid", "caramelo|ozuna",
}


def leer_fuente() -> pd.DataFrame:
    tabla = docx.Document(cfg.FUENTE_MARCO).tables[0]
    filas = []
    for fila in tabla.rows:
        anio, pos, titulo, artistas = [c.text.strip() for c in fila.cells]
        filas.append({
            "anio_lista": int(anio),
            "posicion": int(pos),
            "titulo": u.limpiar_titulo(titulo),
            "artistas": artistas,
            "numero_uno_anual": "‡" in titulo,
        })
    df = pd.DataFrame(filas)
    df["clave"] = [u.clave_cancion(t, a) for t, a in zip(df.titulo, df.artistas)]
    assert len(df) == 150, f"Se esperaban 150 entradas, hay {len(df)}"
    return df


def leer_numeros_uno() -> pd.DataFrame:
    """Números uno semanales; una fila por canción, con el año de su primera semana en el número uno."""
    filas = [l.rstrip("\n").split("|") for l in cfg.FUENTE_ESTRATO2.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    df = pd.DataFrame(filas, columns=["anio_pagina", "titulo", "artistas", "fecha_primer_numero_uno"])
    df["titulo"] = df.titulo.map(u.limpiar_titulo)
    df["clave"] = [u.clave_cancion(t, a) for t, a in zip(df.titulo, df.artistas)]
    df = df.sort_values("fecha_primer_numero_uno").drop_duplicates("clave", keep="first")
    df["anio_lista"] = df.fecha_primer_numero_uno.str[:4].astype(int)
    return df.drop(columns="anio_pagina").reset_index(drop=True)


def periodo_de(anio: int) -> str:
    for nombre, (ini, fin) in cfg.PERIODOS.items():
        if ini <= anio <= fin:
            return nombre
    raise ValueError(f"Año fuera de los periodos definidos: {anio}")


def variables_interpretes(df: pd.DataFrame) -> pd.DataFrame:
    """Género de los intérpretes y país del intérprete principal, desde el instrumento versionado."""
    meta = pd.read_csv(cfg.METADATOS_INTERPRETES).set_index("interprete")
    generos, paises = [], []
    for artistas in df.artistas:
        nombres = u.separar_artistas(artistas)
        faltan = [n for n in nombres if n not in meta.index]
        assert not faltan, f"Intérpretes sin metadatos: {faltan}"
        g = set(meta.loc[nombres, "genero"])
        generos.append("mixto" if len(g) > 1 else ("solo_mujeres" if g == {"mujer"} else "solo_hombres"))
        paises.append(meta.loc[nombres[0], "pais"])
    df = df.copy()
    df["genero_interpretes"] = generos
    df["participa_mujer"] = (df.genero_interpretes != "solo_hombres").astype(int)
    df["pais_principal"] = paises
    df["pais_grupo"] = df.pais_principal.where(df.pais_principal.isin(["Puerto Rico", "Colombia"]), "Otro")
    return df


def main() -> pd.DataFrame:
    cfg.DIR_DATOS.mkdir(exist_ok=True)
    completo = leer_fuente()
    completo.to_csv(cfg.DIR_DATOS / "marco_completo.csv", index=False)

    # Estrato 1. Regla 1: deduplicar conservando la primera aparición (orden año, posición)
    completo = completo.sort_values(["anio_lista", "posicion"])
    resumen = completo.groupby("clave").agg(
        anios_en_lista=("anio_lista", "nunique"),
        mejor_posicion=("posicion", "min"),
        fue_numero_uno_anual=("numero_uno_anual", "any"),
    )
    unicas = completo.drop_duplicates("clave", keep="first").set_index("clave")
    unicas = unicas.drop(columns=["numero_uno_anual"]).join(resumen).reset_index()
    unicas = unicas.rename(columns={"posicion": "posicion_primer_anio"})
    unicas["estrato"] = 1

    # Estrato 2: números uno semanales que no están en el top 10 anual (estratos disjuntos)
    uno = leer_numeros_uno()
    en_e1 = [any(u.misma_cancion(t, a, t1, a1) for t1, a1 in zip(unicas.titulo, unicas.artistas))
             for t, a in zip(uno.titulo, uno.artistas)]
    uno = uno[~np.array(en_e1)].copy()
    uno["estrato"] = 2
    print(f"Números uno únicos: {len(en_e1)} | ya en el top 10 anual: {sum(en_e1)} | marco del estrato 2: {len(uno)}")

    unicas = pd.concat([unicas, uno], ignore_index=True)
    clasif = pd.read_csv(cfg.CLASIFICACION_GENERO)
    faltan = set(unicas.clave) - set(clasif.clave)
    sobran = set(clasif.clave) - set(unicas.clave)
    assert not faltan and not sobran, f"Clasificación incompleta. Faltan: {faltan} Sobran: {sobran}"
    marco = unicas.merge(clasif, on="clave", how="left")
    marco["periodo"] = marco.anio_lista.map(periodo_de)
    marco["colaboracion"] = marco.artistas.str.contains(
        r"featuring|\bwith\b|\band\b|&|,|\bx\b", case=False, regex=True).astype(int)
    marco.to_csv(cfg.DIR_DATOS / "marco_muestral.csv", index=False)

    # Regla 2: solo urbano + híbrido
    elegible = marco[marco.clase.isin(["urbano", "hibrido"])]

    # Estrato 1: censo
    c1 = elegible[elegible.estrato == 1].sort_values(["anio_lista", "posicion_primer_anio"]).copy()
    c1["peso"] = 1.0

    # Estrato 2: muestra aleatoria estratificada por periodo (asignación proporcional, semilla fija)
    m2 = elegible[elegible.estrato == 2].sort_values(["fecha_primer_numero_uno", "clave"])
    N_h = m2.groupby("periodo").size()
    n_h = u.asignacion_proporcional(N_h, cfg.N_ESTRATO2)
    rng = np.random.default_rng(cfg.SEMILLA)
    partes = []
    for periodo, grupo in m2.groupby("periodo"):
        elegidas = grupo.iloc[np.sort(rng.choice(len(grupo), size=n_h[periodo], replace=False))].copy()
        elegidas["peso"] = N_h[periodo] / n_h[periodo]
        partes.append(elegidas)
    c2 = pd.concat(partes).sort_values(["fecha_primer_numero_uno", "clave"])

    sorteo = pd.concat([c1, c2], ignore_index=True)
    sorteo.insert(0, "codigo", [f"C{i:03d}" for i in range(1, len(sorteo) + 1)])
    sorteo = variables_interpretes(sorteo)
    sorteo.to_csv(cfg.DIR_DATOS / "corpus_sorteado.csv", index=False)

    # No respuesta: sin letra disponible. Se registra y el peso del periodo se ajusta.
    sin = sorteo[sorteo.codigo.isin(cfg.SIN_LETRA)].assign(motivo=lambda d: d.codigo.map(cfg.SIN_LETRA))
    sin[["codigo", "estrato", "periodo", "titulo", "artistas", "motivo"]].to_csv(
        cfg.DIR_DATOS / "no_respuesta.csv", index=False)
    corpus = sorteo[~sorteo.codigo.isin(cfg.SIN_LETRA)].copy()
    n_ef = corpus[corpus.estrato == 2].groupby("periodo").size()
    e2 = corpus.estrato == 2
    corpus.loc[e2, "peso"] = corpus.loc[e2, "periodo"].map(N_h / n_ef)
    corpus.to_csv(cfg.DIR_DATOS / "corpus.csv", index=False)
    pd.DataFrame({"N_marco": N_h, "n_sorteada": n_h, "n_con_letra": n_ef}).to_csv(
        cfg.DIR_DATOS / "asignacion_estrato2.csv")

    # Lista de trabajo para el equipo (sin letras: solo identificación)
    lista = sorteo[["codigo", "estrato", "anio_lista", "titulo", "artistas", "periodo", "clase"]].copy()
    lista["version_a_descargar"] = [
        "REMEZCLA con estos intérpretes" if clave in REMEZCLAS else "Original"
        for clave in sorteo.clave]
    lista["fuente_letra"] = ""
    lista["fecha_consulta"] = ""
    lista["observaciones"] = ""
    lista.to_excel(cfg.DIR_DATOS / "lista_letras.xlsx", index=False)

    print(f"Entradas del top 10 anual: {len(completo)} | canciones únicas en ambos marcos: {len(marco)}")
    print(pd.crosstab(marco.estrato, marco.clase, margins=True).to_string())
    print("\nAsignación del estrato 2:")
    print(pd.DataFrame({"N": N_h, "n": n_h}).to_string())
    print("No respuesta:", sin.codigo.tolist())
    print("\nCorpus por periodo y estrato:")
    print(pd.crosstab(corpus.periodo, corpus.estrato, margins=True).to_string())
    return corpus


if __name__ == "__main__":
    main()
