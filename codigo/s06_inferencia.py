"""
Paso 6 — Base analítica (entregable 1) y análisis inferencial.

Preguntas (informe, sección 1):
  P  ¿Cambió entre 2011 y 2025 la proporción de canciones con contenido sexual explícito?
  S1 ¿Difiere la referencia al cuerpo de la mujer (y la agencia femenina) según participe o no
     una intérprete mujer?
  S2 ¿Cambió la riqueza léxica (MATTR) en el tiempo?
  Contexto: ¿creció la participación de la música urbana en el top 10 anual?

Diseño: estrato 1 = censo del top 10 anual; estrato 2 = muestra aleatoria de los números uno
semanales que no entraron al top 10. Las pruebas se aplican al corpus analizable completo y, como
sensibilidad, dentro de cada estrato; los modelos incluyen el estrato como covariable y los
descriptivos poblacionales se ponderan con el peso de diseño (N_h / n_h).

Alcance: solo canciones analizables (no excluidas por idioma). Las categorías codificadas por
el LLM se marcan según la decisión de validación del paso 5: las conclusiones del informe se
limitan a las que resulten válidas.

Salidas: datos/base_analitica.csv · resultados/descriptivos_periodo.csv · resultados/inferencia.csv
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pymannkendall as mk
import statsmodels.formula.api as smf
from scipy import stats
from scipy.stats.contingency import odds_ratio
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

N_PERM = 10_000
RES: list[dict] = []


def registrar(pregunta, prueba, variable, estadistico, p, efecto=None, medida=None,
              ic=(np.nan, np.nan), n=None, gl=None, nota="", estado=""):
    RES.append({"pregunta": pregunta, "prueba": prueba, "variable": variable,
                "estadistico": estadistico, "gl": gl, "p": p, "tamano_efecto": efecto,
                "medida_efecto": medida, "ic95_inf": ic[0], "ic95_sup": ic[1], "n": n,
                "estado_instrumento": estado, "nota": nota})


def construir_base() -> pd.DataFrame:
    corpus = pd.read_csv(cfg.DIR_DATOS / "corpus.csv")
    texto = pd.read_csv(cfg.DIR_DATOS / "variables_texto.csv")
    llm = pd.read_csv(cfg.DIR_REGISTROS / "codificacion_llm.csv")[
        ["codigo", "sexual", "cuerpo", "agencia", "duda"]].rename(
        columns={"sexual": "llm_sexual", "cuerpo": "llm_cuerpo", "agencia": "llm_agencia", "duda": "llm_duda"})
    sub = pd.read_csv(cfg.DIR_DATOS / "submuestra_validacion.csv")[["codigo"]].assign(en_validacion=1)
    base = corpus.merge(texto, on="codigo").merge(llm, on="codigo", how="left").merge(sub, on="codigo", how="left")
    base["en_validacion"] = base.en_validacion.fillna(0).astype(int)
    base["llm_sexual_explicito"] = (base.llm_sexual == 2).astype("Int64").where(base.llm_sexual.notna())
    base["analizable"] = (base.excluida_idioma == 0).astype(int)
    base = base.drop(columns=["clave"])
    base.to_csv(cfg.DIR_DATOS / "base_analitica.csv", index=False)
    return base


def estado_categorias() -> dict:
    ruta = cfg.DIR_RESULTADOS / "categorias_validas.csv"
    if not ruta.exists():
        return {c: "pendiente de validación" for c in ["sexual", "sexual_explicito", "cuerpo", "agencia"]}
    d = pd.read_csv(ruta)
    return dict(zip(d.categoria, d.decision))


def chi2_con_permutacion(x: pd.Series, y: pd.Series, semilla: int):
    tabla = pd.crosstab(x, y)
    chi2, p, gl, esperadas = stats.chi2_contingency(tabla, correction=False)
    rng = np.random.default_rng(semilla)
    yv = y.to_numpy()
    mayores = sum(
        stats.chi2_contingency(pd.crosstab(x.to_numpy(), rng.permutation(yv)), correction=False)[0] >= chi2 - 1e-12
        for _ in range(N_PERM))
    p_perm = (mayores + 1) / (N_PERM + 1)
    n = tabla.to_numpy().sum()
    v = np.sqrt(chi2 / (n * (min(tabla.shape) - 1)))
    return chi2, gl, p, p_perm, v, esperadas.min()


def kruskal_epsilon(valores: pd.Series, grupos: pd.Series):
    muestras = [valores[grupos == g].dropna() for g in sorted(grupos.unique())]
    h, p = stats.kruskal(*muestras)
    n = sum(len(m) for m in muestras)
    return h, p, h / (n - 1), len(muestras) - 1


def logistica_anio(df: pd.DataFrame, y: str):
    d = df[[y, "anio_lista"]].dropna().astype(float).assign(anio_c=lambda t: t.anio_lista - 2018)
    m = smf.logit(f"{y} ~ anio_c", d).fit(disp=0)
    orr = np.exp(m.params["anio_c"])
    li, ls = np.exp(m.conf_int().loc["anio_c"])
    return orr, li, ls, m.pvalues["anio_c"], m.llr, m.llr_pvalue, len(d)


def odds_ratio_fisher(df, fila, col):
    t = pd.crosstab(df[fila], df[col]).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
    res = odds_ratio(t.to_numpy(), kind="conditional")
    ci = res.confidence_interval(0.95)
    _, p = stats.fisher_exact(t.to_numpy())
    return res.statistic, (ci.low, ci.high), p, t


def descriptivos(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for per, g in list(df.groupby("periodo")) + [("Total", df)]:
        f = {"periodo": per, "n": len(g)}
        for v in ["llm_sexual_explicito", "llm_cuerpo", "llm_agencia"]:
            k = int(g[v].sum())
            li, ls = proportion_confint(k, len(g), method="wilson")
            f[f"{v}_pct"], f[f"{v}_ic_inf"], f[f"{v}_ic_sup"] = 100 * k / len(g), 100 * li, 100 * ls
        f["llm_sexual_media"] = g.llm_sexual.mean()
        f["mattr50_mediana"], f["n_palabras_mediana"] = g.mattr50.median(), g.n_palabras.median()
        f["lex_sexual_x100_mediana"] = g.lex_sexual_x100.median()
        f["participa_mujer_pct"] = 100 * g.participa_mujer.mean()
        f["lex_sexual_presente_pct"] = 100 * g.lex_sexual_presente.mean()
        f["lex_sexual_presente_pct_ponderado"] = 100 * np.average(g.lex_sexual_presente, weights=g.peso)
        f["mattr50_media_ponderada"] = np.average(g.mattr50, weights=g.peso)
        f["n_estrato1"], f["n_estrato2"] = int((g.estrato == 1).sum()), int((g.estrato == 2).sum())
        f["poblacion_estimada"] = g.peso.sum()
        filas.append(f)
    return pd.DataFrame(filas)


def analisis_principal(df, etiqueta, estado):
    """P: contenido sexual explícito en el tiempo."""
    chi2, gl, p, p_perm, v, e_min = chi2_con_permutacion(df.periodo, df.llm_sexual_explicito, cfg.SEMILLA)
    registrar("P", "Chi-cuadrado de independencia (periodo × explícito)", f"sexual_explicito{etiqueta}",
              chi2, p_perm, v, "V de Cramér", n=len(df), gl=gl, estado=estado["sexual_explicito"],
              nota=f"p asintótica={p:.4f}; frecuencia esperada mínima={e_min:.2f}; se reporta p por "
                   f"permutación ({N_PERM} réplicas) porque hay esperadas < 5" if e_min < 5 else f"p asintótica={p:.4f}")
    orr, li, ls, p_w, llr, p_lr, n = logistica_anio(df, "llm_sexual_explicito")
    registrar("P", "Regresión logística: explícito ~ año", f"sexual_explicito{etiqueta}", llr, p_lr, orr,
              "Razón de odds por año", (li, ls), n, 1, estado=estado["sexual_explicito"],
              nota=f"estadístico = razón de verosimilitud; p de Wald={p_w:.4f}; año centrado en 2018")
    anual = df.groupby("anio_lista").llm_sexual_explicito.mean()
    r = mk.original_test(anual.to_numpy())
    registrar("P", "Mann-Kendall (proporción anual de explícitas)", f"sexual_explicito{etiqueta}", r.s, r.p,
              r.Tau, "Tau de Kendall", n=len(anual), estado=estado["sexual_explicito"],
              nota=f"pendiente de Sen={r.slope:.4f} por año; 15 puntos anuales")
    h, p, eps, gl = kruskal_epsilon(df.llm_sexual, df.periodo)
    registrar("P", "Kruskal-Wallis (nivel sexual 0-2 por periodo)", f"sexual_ordinal{etiqueta}", h, p, eps,
              "Épsilon cuadrado", n=len(df), gl=gl, estado=estado["sexual"])
    rho, p = stats.spearmanr(df.llm_sexual, df.anio_lista)
    registrar("P", "Correlación de Spearman (nivel sexual vs año)", f"sexual_ordinal{etiqueta}", rho, p, rho,
              "Rho de Spearman", n=len(df), estado=estado["sexual"])


def main():
    base = construir_base()
    df = base[base.analizable == 1].copy()
    if df.llm_sexual.isna().any():
        print("Aviso: canciones sin codificación LLM:", df.loc[df.llm_sexual.isna(), "codigo"].tolist())
        df = df[df.llm_sexual.notna()]
    estado = estado_categorias()
    descriptivos(df).round(2).to_csv(cfg.DIR_RESULTADOS / "descriptivos_periodo.csv", index=False)

    # ---- P: pregunta principal (corpus completo y sensibilidad sin híbridos)
    analisis_principal(df, "", estado)
    analisis_principal(df[df.clase == "urbano"], " (sensibilidad: sin híbridos)", estado)

    # Validez convergente: léxico determinístico vs nivel sexual del LLM
    rho, p = stats.spearmanr(df.lex_sexual_x100, df.llm_sexual)
    registrar("P", "Spearman: densidad del léxico sexual vs nivel sexual LLM", "validez_convergente", rho, p,
              rho, "Rho de Spearman", n=len(df), estado="instrumento léxico (determinístico)",
              nota="Dos instrumentos independientes que deberían covariar si ambos miden lo mismo")
    h, p, eps, gl = kruskal_epsilon(df.lex_sexual_x100, df.periodo)
    registrar("P", "Kruskal-Wallis (léxico sexual por 100 palabras, por periodo)", "lex_sexual_x100", h, p, eps,
              "Épsilon cuadrado", n=len(df), gl=gl, estado="instrumento léxico (determinístico)")
    anual = df.groupby("anio_lista").lex_sexual_x100.median()
    r = mk.original_test(anual.to_numpy())
    registrar("P", "Mann-Kendall (mediana anual del léxico sexual)", "lex_sexual_x100", r.s, r.p, r.Tau,
              "Tau de Kendall", n=len(anual), estado="instrumento léxico (determinístico)",
              nota=f"pendiente de Sen={r.slope:.4f}")
    d = df[["lex_sexual_presente", "anio_lista", "estrato"]].astype(float).assign(anio_c=lambda t: t.anio_lista - 2018)
    m = smf.logit("lex_sexual_presente ~ anio_c + C(estrato)", d).fit(disp=0)
    li, ls = np.exp(m.conf_int().loc["anio_c"])
    registrar("P", "Regresión logística: léxico sexual presente ~ año + estrato", "lex_sexual_presente",
              m.params["anio_c"] / m.bse["anio_c"], m.pvalues["anio_c"], np.exp(m.params["anio_c"]),
              "Razón de odds por año", (li, ls), len(d), 1, estado="instrumento léxico (determinístico)",
              nota=f"estadístico = z de Wald del año; OR del estrato 2 frente al 1="
                   f"{np.exp(m.params['C(estrato)[T.2.0]']):.3f} (p={m.pvalues['C(estrato)[T.2.0]']:.4f})")
    mi = smf.logit("lex_sexual_presente ~ anio_c * C(estrato)", d).fit(disp=0)
    k = "anio_c:C(estrato)[T.2.0]"
    li, ls = np.exp(mi.conf_int().loc[k])
    registrar("P", "Regresión logística: interacción año × estrato (léxico sexual presente)", "lex_sexual_presente",
              mi.params[k] / mi.bse[k], mi.pvalues[k], np.exp(mi.params[k]), "Cociente de razones de odds por año",
              (li, ls), len(d), 1, estado="instrumento léxico (determinístico)",
              nota="prueba si la tendencia anual difiere entre el top 10 anual y los otros números uno")
    for e, g in df.groupby("estrato"):
        h, p, eps, gl = kruskal_epsilon(g.lex_sexual_x100, g.periodo)
        registrar("P", f"Kruskal-Wallis (léxico sexual por periodo), solo estrato {e}",
                  f"lex_sexual_x100 (estrato {e})", h, p, eps, "Épsilon cuadrado", n=len(g), gl=gl,
                  estado="instrumento léxico (determinístico)", nota="sensibilidad por estrato")
        orr, li, ls, p_w, llr, p_lr, n_ = logistica_anio(g, "lex_sexual_presente")
        registrar("P", f"Regresión logística: léxico sexual presente ~ año, solo estrato {e}",
                  f"lex_sexual_presente (estrato {e})", llr, p_lr, orr, "Razón de odds por año", (li, ls), n_, 1,
                  estado="instrumento léxico (determinístico)", nota="sensibilidad por estrato")
        rho, p = stats.spearmanr(g.lex_sexual_x100, g.anio_lista)
        registrar("P", f"Spearman (léxico sexual vs año), solo estrato {e}", f"lex_sexual_x100 (estrato {e})",
                  rho, p, rho, "Rho de Spearman", n=len(g), estado="instrumento léxico (determinístico)",
                  nota="sensibilidad por estrato")

    # ---- Triangulación con la codificación humana (submuestra aleatoria de validación)
    ruta_val = cfg.DIR_RESULTADOS / "tabla_validacion.xlsx"
    if ruta_val.exists():
        val = pd.read_excel(ruta_val, sheet_name="Submuestra").merge(
            base[["codigo", "anio_lista", "lex_sexual_x100"]], on="codigo")
        letras_cod = sorted(c[-1] for c in val.columns if re.fullmatch(r"sexual_[A-C]", c))
        val["sexual_humanos_media"] = val[[f"sexual_{l}" for l in letras_cod]].mean(axis=1)
        for l in letras_cod:
            rho, p = stats.spearmanr(val[f"sexual_{l}"], val.anio_lista)
            registrar("P", f"Spearman: nivel sexual del codificador {l} vs año", "sexual_humano", rho, p, rho,
                      "Rho de Spearman", n=len(val), estado="codificación humana (submuestra aleatoria)")
            h, p, eps, gl = kruskal_epsilon(val[f"sexual_{l}"], val.periodo)
            registrar("P", f"Kruskal-Wallis: nivel sexual del codificador {l} por periodo", "sexual_humano", h, p,
                      eps, "Épsilon cuadrado", n=len(val), gl=gl, estado="codificación humana (submuestra aleatoria)")
        val = val.merge(base[["codigo", "estrato"]], on="codigo")
        for l in letras_cod:
            for e, g in val.groupby("estrato"):
                rho, p = stats.spearmanr(g[f"sexual_{l}"], g.anio_lista)
                registrar("P", f"Spearman: nivel sexual del codificador {l} vs año, solo estrato {e}",
                          f"sexual_humano (estrato {e})", rho, p, rho, "Rho de Spearman", n=len(g),
                          estado="codificación humana (submuestra aleatoria)", nota="sensibilidad por estrato")
        ce = val[val.sexual_consenso.notna()].assign(
            expl=lambda t: (t.sexual_consenso == 2).astype(float), anio_c=lambda t: t.anio_lista - 2018)
        m = smf.logit("expl ~ anio_c", ce).fit(disp=0)
        li, ls = np.exp(m.conf_int().loc["anio_c"])
        registrar("P", "Regresión logística: explícito según el consenso humano ~ año", "sexual_explicito_humano",
                  m.llr, m.llr_pvalue, np.exp(m.params["anio_c"]), "Razón de odds por año", (li, ls), len(ce), 1,
                  estado="codificación humana (submuestra aleatoria)",
                  nota="consenso = canciones con acuerdo de A y B; estadístico = razón de verosimilitud")
        rho, p = stats.spearmanr(val.lex_sexual_x100, val.sexual_humanos_media)
        registrar("P", "Spearman: léxico sexual vs promedio de codificadores humanos", "validez_criterio_lexico",
                  rho, p, rho, "Rho de Spearman", n=len(val), estado="instrumento léxico (determinístico)",
                  nota="Validez del léxico frente al juicio humano")
        rho, p = stats.spearmanr(val.sexual_LLM, val.sexual_humanos_media)
        registrar("P", "Spearman: nivel sexual LLM vs promedio de codificadores humanos", "orden_llm",
                  rho, p, rho, "Rho de Spearman", n=len(val), estado=estado["sexual"],
                  nota="Mide si el modelo ordena las canciones como las personas, aunque su nivel difiera")
        resumen = []
        for quien in letras_cod + ["LLM"]:
            col = f"sexual_{quien}"
            for per, g in val.groupby("periodo"):
                resumen.append({"codificador": quien, "periodo": per, "n": len(g),
                                "n_explicito": int((g[col] == 2).sum()),
                                "pct_explicito": 100 * (g[col] == 2).mean(),
                                "pct_alguno": 100 * (g[col] >= 1).mean(), "media_nivel": g[col].mean()})
        for per, g in val[val.sexual_consenso.notna()].groupby("periodo"):
            k = int((g.sexual_consenso == 2).sum())
            li, ls = proportion_confint(k, len(g), method="wilson")
            resumen.append({"codificador": "consenso", "periodo": per, "n": len(g), "n_explicito": k,
                            "pct_explicito": 100 * k / len(g), "pct_alguno": 100 * (g.sexual_consenso >= 1).mean(),
                            "media_nivel": g.sexual_consenso.mean(), "ic_inf": 100 * li, "ic_sup": 100 * ls})
        pd.DataFrame(resumen).round(2).to_csv(cfg.DIR_RESULTADOS / "triangulacion_submuestra.csv", index=False)

    # ---- S1: cuerpo y agencia según participación femenina
    for v, cat in [("llm_cuerpo", "cuerpo"), ("llm_agencia", "agencia")]:
        orr, ic, p, t = odds_ratio_fisher(df, "participa_mujer", v)
        registrar("S1", f"Prueba exacta de Fisher ({cat} × participa mujer)", cat, orr, p, orr,
                  "Razón de odds (condicional)", ic, len(df), 1, estado=estado[cat],
                  nota="tabla [sin mujer, con mujer] × [0, 1] = " + str(t.to_numpy().tolist()))
    orr, ic, p, t = odds_ratio_fisher(df, "participa_mujer", "lex_cuerpo_presente")
    registrar("S1", "Prueba exacta de Fisher (léxico de cuerpo × participa mujer)", "lex_cuerpo_presente", orr, p,
              orr, "Razón de odds (condicional)", ic, len(df), 1, estado="instrumento léxico (determinístico)",
              nota="triangulación; tabla [sin mujer, con mujer] × [0, 1] = " + str(t.to_numpy().tolist()))
    orr, li, ls, p_w, llr, p_lr, n = logistica_anio(df, "llm_cuerpo")
    registrar("S1", "Regresión logística: cuerpo ~ año", "cuerpo", llr, p_lr, orr, "Razón de odds por año",
              (li, ls), n, 1, estado=estado["cuerpo"])
    orr, li, ls, p_w, llr, p_lr, n = logistica_anio(df, "llm_agencia")
    registrar("S1", "Regresión logística: agencia ~ año", "agencia", llr, p_lr, orr, "Razón de odds por año",
              (li, ls), n, 1, estado=estado["agencia"])

    # ---- S2: riqueza léxica
    w, p_norm = stats.shapiro(df.mattr50)
    h, p, eps, gl = kruskal_epsilon(df.mattr50, df.periodo)
    registrar("S2", "Kruskal-Wallis (MATTR por periodo)", "mattr50", h, p, eps, "Épsilon cuadrado", n=len(df),
              gl=gl, estado="medida determinística",
              nota=f"Shapiro-Wilk W={w:.3f}, p={p_norm:.4f}: prueba no paramétrica por estratos pequeños y desbalanceados")
    anual = df.groupby("anio_lista").mattr50.median()
    r = mk.original_test(anual.to_numpy())
    registrar("S2", "Mann-Kendall (mediana anual de MATTR)", "mattr50", r.s, r.p, r.Tau, "Tau de Kendall",
              n=len(anual), estado="medida determinística", nota=f"pendiente de Sen={r.slope:.5f} por año")
    rho, p = stats.spearmanr(df.mattr50, df.anio_lista)
    registrar("S2", "Correlación de Spearman (MATTR vs año)", "mattr50", rho, p, rho, "Rho de Spearman",
              n=len(df), estado="medida determinística")
    for e, g in df.groupby("estrato"):
        rho, p = stats.spearmanr(g.mattr50, g.anio_lista)
        registrar("S2", f"Spearman (MATTR vs año), solo estrato {e}", f"mattr50 (estrato {e})", rho, p, rho,
                  "Rho de Spearman", n=len(g), estado="medida determinística", nota="sensibilidad por estrato")
    m = smf.ols("mattr50 ~ I(anio_lista - 2018) + C(estrato)", df).fit()
    b, (li, ls) = m.params.iloc[2], m.conf_int().iloc[2]
    registrar("S2", "Regresión lineal: MATTR ~ año + estrato", "mattr50", m.tvalues.iloc[2], m.pvalues.iloc[2], b,
              "Cambio de MATTR por año", (li, ls), len(df), int(m.df_resid), estado="medida determinística",
              nota="estadístico = t del año; el estrato controla la diferencia entre marcos")

    # ---- Contexto: peso de la música urbana en el top 10 anual (marco completo, 150 entradas)
    marco = pd.read_csv(cfg.DIR_DATOS / "marco_completo.csv").merge(
        pd.read_csv(cfg.CLASIFICACION_GENERO)[["clave", "clase"]], on="clave")
    marco["urbana"] = marco.clase.isin(["urbano", "hibrido"]).astype(int)
    anual = marco.groupby("anio_lista").urbana.mean()
    anual.rename("prop_urbana").to_csv(cfg.DIR_RESULTADOS / "proporcion_urbana_anual.csv")
    r = mk.original_test(anual.to_numpy())
    registrar("Contexto", "Mann-Kendall (proporción anual de canciones urbanas en el top 10)", "urbana",
              r.s, r.p, r.Tau, "Tau de Kendall", n=len(anual), estado="clasificación de género (instrumento v1.0)",
              nota=f"pendiente de Sen={r.slope:.4f} por año; marco de 150 entradas")

    res = pd.DataFrame(RES)
    sec = res.pregunta.isin(["S1", "S2"]) & ~res.nota.str.contains("sensibilidad")
    res.loc[sec, "p_holm"] = multipletests(res.loc[sec, "p"], method="holm")[1]
    res.to_csv(cfg.DIR_RESULTADOS / "inferencia.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        print(res[["pregunta", "prueba", "variable", "estadistico", "p", "tamano_efecto", "medida_efecto",
                   "ic95_inf", "ic95_sup", "n"]].round(4).to_string(index=False))
    return res


if __name__ == "__main__":
    main()
