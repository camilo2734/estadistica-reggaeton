"""
Paso 5 — Validación del LLM como instrumento de medición.

Entradas : datos/codificacion_humana/codificador_A.xlsx, codificador_B.xlsx (obligatorios)
           datos/codificacion_humana/codificador_C.xlsx (opcional: tercer codificador)
           datos/codificacion_humana/consenso.xlsx (solo si hay 2 codificadores: discrepancias
           resueltas por discusión documentada)
           registros/codificacion_llm.csv
Salidas  : resultados/tabla_validacion.xlsx  (entregable 4)
           resultados/kappas.csv
           resultados/discrepancias.csv
           resultados/categorias_validas.csv

Regla de decisión, fijada ANTES de ver los datos (informe, sección 6):
  Una categoría es válida para la inferencia si
    (a) κ humano–humano ≥ 0,61  (el libro de códigos es claro; con 3 codificadores se usa el
        promedio de los κ por pares, κ de Light), y
    (b) κ LLM–consenso   ≥ 0,61  y el límite inferior de su IC 95 % > 0,40.
  0,41–0,60 = acuerdo moderado: se reporta, pero no entra a la inferencia.
  Escala de Landis y Koch (1977). Para 'sexual' (ordinal) se usa κ ponderado lineal.

Consenso humano: con 3 codificadores, mayoría (mediana en 'sexual'); con 2, el valor común
o, si difieren, el registrado en consenso.xlsx tras discusión. Si no hubo discusión, el consenso
se define solo en las canciones con acuerdo y el LLM se compara además con cada codificador
por separado (desviación documentada en el informe).
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

DIR_HUM = cfg.DIR_DATOS / "codificacion_humana"
CATS = {"sexual": [0, 1, 2], "cuerpo": [0, 1], "agencia": [0, 1]}
PESOS = {"sexual": "linear", "cuerpo": None, "agencia": None}
UMBRAL, LIM_INF, N_BOOT = 0.61, 0.40, 2000


def leer_codificador(letra: str) -> pd.DataFrame | None:
    ruta = DIR_HUM / f"codificador_{letra}.xlsx"
    if not ruta.exists():
        return None
    df = pd.read_excel(ruta, sheet_name="Codificacion")
    df = df[["codigo"] + list(CATS) + ["duda"]].copy()
    df["duda"] = df["duda"].fillna(0)
    faltan = df[list(CATS)].isna().any(axis=1)
    if faltan.any():
        raise ValueError(f"Codificador {letra}: celdas vacías en {df.loc[faltan, 'codigo'].tolist()}")
    for c, valores in CATS.items():
        if not df[c].isin(valores).all():
            raise ValueError(f"Codificador {letra}: valores fuera del libro de códigos en {c}")
    return df.astype({c: int for c in list(CATS) + ["duda"]}).set_index("codigo")


def kappa(a, b, cat):
    return cohen_kappa_score(a, b, labels=CATS[cat], weights=PESOS[cat])


def kappa_ic(a, b, cat, semilla):
    """κ con IC 95 % bootstrap percentil (remuestreo de canciones)."""
    a, b = np.asarray(a), np.asarray(b)
    rng = np.random.default_rng(semilla)
    est = kappa(a, b, cat)
    boot = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(a), len(a))
        if len(set(a[i])) > 1 or len(set(b[i])) > 1:
            boot.append(kappa(a[i], b[i], cat))
    li, ls = np.nanpercentile(boot, [2.5, 97.5])
    return est, li, ls


def consenso(cod: dict[str, pd.DataFrame]) -> pd.DataFrame:
    letras = sorted(cod)
    cons = pd.DataFrame(index=cod[letras[0]].index)
    if len(letras) >= 3:
        for c in CATS:
            m = pd.concat([cod[l][c] for l in letras], axis=1)
            cons[c] = m.median(axis=1).round().astype(int) if c == "sexual" else m.mode(axis=1)[0].astype(int)
        cons["regla"] = "mayoría de 3 codificadores (mediana en sexual)"
        return cons
    a, b = cod[letras[0]], cod[letras[1]]
    ruta = DIR_HUM / "consenso.xlsx"
    resuelto = pd.read_excel(ruta).set_index("codigo") if ruta.exists() else None
    for c in CATS:
        cons[c] = a[c].where(a[c] == b[c])
        pend = cons[c].isna()
        if pend.any() and resuelto is not None:
            cons.loc[pend, c] = resuelto.loc[cons.index[pend], c]
    # Versión binaria del desenlace principal: hay consenso si ambos coinciden en explícito sí/no
    cons["sexual_explicito"] = (a.sexual == 2).astype(int).where((a.sexual == 2) == (b.sexual == 2))
    if resuelto is not None:   # con discusión, el desenlace binario se deriva del nivel acordado
        cons["sexual_explicito"] = (cons.sexual == 2).astype(int).where(cons.sexual.notna())
    cons["regla"] = ("acuerdo de 2 codificadores; desacuerdos resueltos por discusión" if resuelto is not None
                     else "acuerdo de 2 codificadores; desacuerdos sin resolver, excluidos del consenso")
    return cons


def tipo_discrepancia(fila) -> str:
    """Clasificación preliminar automática; la final se asigna en la revisión cualitativa."""
    if not fila.humanos_unanimes or fila.duda_humanos > 0:
        return "ambigüedad probable del texto"
    if fila.duda_llm == 1:
        return "límite del modelo (el modelo dudó)"
    return "error probable del modelo"


def main():
    cod = {l: d for l in "ABC" if (d := leer_codificador(l)) is not None}
    if not {"A", "B"} <= set(cod):
        print("Validación pendiente: faltan las plantillas de los codificadores A y B en", DIR_HUM)
        return None
    sub = pd.read_csv(cfg.DIR_DATOS / "submuestra_validacion.csv").set_index("codigo")
    for l, d in cod.items():
        if set(d.index) != set(sub.index):
            raise ValueError(f"El codificador {l} no codificó exactamente la submuestra sorteada")
        cod[l] = d.loc[sub.index]
    llm = pd.read_csv(cfg.DIR_REGISTROS / "codificacion_llm.csv").set_index("codigo").loc[sub.index]
    cons = consenso(cod)

    filas = []

    def agregar(cat, comp, x, y, pesos_cat):
        m = x.notna() & y.notna()
        k, li, ls = kappa_ic(x[m].astype(int), y[m].astype(int), pesos_cat, cfg.SEMILLA)
        filas.append({"categoria": cat, "comparacion": comp, "kappa": k, "ic95_inf": li, "ic95_sup": ls,
                      "acuerdo_bruto": (x[m] == y[m]).mean(), "n": int(m.sum())})

    for c in CATS:
        for x, y in combinations(sorted(cod), 2):
            agregar(c, f"humano {x} vs humano {y}", cod[x][c], cod[y][c], c)
        for l in sorted(cod):
            agregar(c, f"LLM vs humano {l}", llm[c], cod[l][c], c)
        agregar(c, "LLM vs consenso humano", llm[c], cons[c], c)
        if c == "sexual":  # versión binaria del desenlace principal: explícito (2) vs no
            bin_ = lambda s: (s == 2).astype(int)
            for x, y in combinations(sorted(cod), 2):
                agregar("sexual_explicito", f"humano {x} vs humano {y}", bin_(cod[x][c]), bin_(cod[y][c]), "cuerpo")
            for l in sorted(cod):
                agregar("sexual_explicito", f"LLM vs humano {l}", bin_(llm[c]), bin_(cod[l][c]), "cuerpo")
            agregar("sexual_explicito", "LLM vs consenso humano", bin_(llm[c]), cons["sexual_explicito"], "cuerpo")
    kap = pd.DataFrame(filas)
    kap["ponderacion"] = np.where(kap.categoria == "sexual", "lineal", "ninguna")

    decisiones = []
    for c in kap.categoria.unique():
        hh = kap[(kap.categoria == c) & kap.comparacion.str.startswith("humano")].kappa.mean()
        lc = kap[(kap.categoria == c) & (kap.comparacion == "LLM vs consenso humano")].iloc[0]
        lh = kap[(kap.categoria == c) & kap.comparacion.str.startswith("LLM vs humano")].kappa.mean()
        valida = hh >= UMBRAL and lc.kappa >= UMBRAL and lc.ic95_inf > LIM_INF
        nivel = ("válida" if valida else
                 "no válida: el libro de códigos no logra acuerdo humano" if hh < 0.41 else
                 "moderada: solo descriptiva" if min(hh, lc.kappa) > 0.40 else "no válida")
        decisiones.append({"categoria": c, "kappa_humano_light": hh, "kappa_llm_humanos_prom": lh,
                           "kappa_llm_consenso": lc.kappa, "ic95_inf": lc.ic95_inf, "n_consenso": lc.n,
                           "decision": nivel, "entra_a_inferencia": valida})
    dec = pd.DataFrame(decisiones)

    disc = []
    for c in CATS:
        for cod_c in sub.index:
            vals = {f"humano_{l}": int(cod[l].at[cod_c, c]) for l in sorted(cod)}
            unanimes = len(set(vals.values())) == 1
            if unanimes and llm.at[cod_c, c] == cons.at[cod_c, c]:
                continue
            disc.append({"codigo": cod_c, "titulo": sub.at[cod_c, "titulo"], "categoria": c,
                         "llm": int(llm.at[cod_c, c]), "consenso": cons.at[cod_c, c], **vals,
                         "humanos_unanimes": unanimes, "duda_llm": int(llm.at[cod_c, "duda"]),
                         "duda_humanos": int(sum(cod[l].at[cod_c, "duda"] for l in cod)),
                         "justificacion_llm": llm.at[cod_c, "justificacion"]})
    disc = pd.DataFrame(disc)
    if len(disc):
        disc["tipo"] = np.where(disc.humanos_unanimes, "LLM difiere del consenso", "desacuerdo entre humanos")
        disc["clasificacion_preliminar"] = disc.apply(tipo_discrepancia, axis=1)
        disc["direccion"] = np.select(
            [disc.humanos_unanimes & (disc.llm > disc.consenso.fillna(-1)), disc.humanos_unanimes],
            ["LLM sobrecodifica", "LLM subcodifica"], "—")

    detalle = sub[["titulo", "artistas", "periodo"]].copy()
    for l in sorted(cod):
        for c in CATS:
            detalle[f"{c}_{l}"] = cod[l][c]
    for c in CATS:
        detalle[f"{c}_consenso"] = cons[c]
        detalle[f"{c}_LLM"] = llm[c]
    detalle["regla_consenso"] = cons["regla"]

    with pd.ExcelWriter(cfg.DIR_RESULTADOS / "tabla_validacion.xlsx") as xw:
        detalle.reset_index().to_excel(xw, sheet_name="Submuestra", index=False)
        kap.round(3).to_excel(xw, sheet_name="Kappas", index=False)
        dec.round(3).to_excel(xw, sheet_name="Decision", index=False)
        fila = 0
        for c in CATS:
            ok = cons[c].notna()
            m = pd.DataFrame(confusion_matrix(cons[c][ok].astype(int), llm[c][ok], labels=CATS[c]),
                             index=[f"consenso={v}" for v in CATS[c]], columns=[f"LLM={v}" for v in CATS[c]])
            pd.DataFrame({c.upper(): []}).to_excel(xw, sheet_name="Matrices", startrow=fila, index=False)
            m.to_excel(xw, sheet_name="Matrices", startrow=fila + 1)
            fila += len(CATS[c]) + 4
        disc.to_excel(xw, sheet_name="Discrepancias", index=False)
    kap.to_csv(cfg.DIR_RESULTADOS / "kappas.csv", index=False)
    dec.to_csv(cfg.DIR_RESULTADOS / "categorias_validas.csv", index=False)
    disc.to_csv(cfg.DIR_RESULTADOS / "discrepancias.csv", index=False)
    print(kap.round(3).to_string(index=False))
    print(dec.round(3).to_string(index=False))
    return dec


if __name__ == "__main__":
    main()
