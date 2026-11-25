"""
Paso 7 — Gráficos autoexplicativos para el informe (PNG, 200 dpi).

Cada figura lleva título, subtítulo con n y fuente, ejes rotulados y unidades. Paleta: tres
primeros tonos de la paleta categórica validada (azul, naranja, aguamarina), texto en tinta
neutra, cuadrícula tenue.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

AZUL, NARANJA, AGUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
FUENTE = "Fuente: Billboard Hot Latin Songs 2011–2025 (top 10 anual y números uno semanales, vía Wikipedia)."
DIR_FIG = cfg.DIR_RESULTADOS / "figuras"
ETQ_PER = {"P1_2011_2015": "2011–2015", "P2_2016_2020": "2016–2020", "P3_2021_2025": "2021–2025"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def encabezado(fig, titulo, subtitulo, fuente=FUENTE):
    fig.text(0.02, 0.97, titulo, fontsize=12.5, fontweight="bold", color=TINTA, va="top")
    fig.text(0.02, 0.905, subtitulo, fontsize=9.5, color=TINTA2, va="top")
    fig.text(0.02, 0.015, fuente, fontsize=7.5, color=TINTA2)


def guardar(fig, nombre):
    fig.savefig(DIR_FIG / nombre, dpi=200, facecolor="white")
    plt.close(fig)


def fig_explicito_periodo(df):
    fig, ax = plt.subplots(figsize=(7, 4.4))
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.11, right=0.97)
    filas = []
    for per, g in df.groupby("periodo"):
        k, n = int(g.llm_sexual_explicito.sum()), len(g)
        li, ls = proportion_confint(k, n, method="wilson")
        filas.append((ETQ_PER[per], 100 * k / n, 100 * li, 100 * ls, k, n))
    x = np.arange(len(filas))
    p = [f[1] for f in filas]
    ax.bar(x, p, width=0.55, color=AZUL, zorder=2)
    ax.errorbar(x, p, yerr=[[f[1] - f[2] for f in filas], [f[3] - f[1] for f in filas]],
                fmt="none", ecolor=TINTA, elinewidth=1.2, capsize=5, zorder=3)
    for xi, f in zip(x, filas):
        ax.text(xi, f[3] + 3, f"{f[1]:.0f} %\n({f[4]} de {f[5]})", ha="center", va="bottom", fontsize=9, color=TINTA)
    ax.set_xticks(x, [f[0] for f in filas])
    ax.set_ylim(0, 115)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_ylabel("Canciones con contenido sexual explícito")
    encabezado(fig, "Canciones con contenido sexual explícito, por periodo",
               f"Proporción e IC 95 % (Wilson) · n = {len(df)} canciones urbanas analizables")
    guardar(fig, "fig1_explicito_por_periodo.png")


def fig_anual(df, prop_urbana):
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.10, right=0.97)
    anual = df.groupby("anio_lista").agg(p=("llm_sexual_explicito", "mean"), n=("codigo", "size"))
    ax.plot(prop_urbana.index, 100 * prop_urbana.values, color=NARANJA, lw=2, marker="o", ms=6, zorder=2)
    ax.plot(anual.index, 100 * anual.p, color=AZUL, lw=2, marker="o", ms=6, zorder=3)
    ax.set_xticks(range(2011, 2026, 2))
    ax.set_ylim(-3, 105)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_xlabel("Año de la lista de fin de año")
    ax.set_ylabel("Porcentaje")
    ax.legend(["Urbanas en el top 10 (de 10)", "Explícitas entre las urbanas"], frameon=False,
              loc="upper left", fontsize=8.5)
    encabezado(fig, "Música urbana en el top 10 y contenido explícito, por año",
               "Cada punto anual de la serie azul resume entre 2 y 10 canciones: leer la tendencia, no un año suelto")
    guardar(fig, "fig2_serie_anual.png")


def fig_mujer(df):
    fig, ax = plt.subplots(figsize=(7, 4.4))
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.11, right=0.97)
    grupos = [(0, "Solo intérpretes hombres", AZUL), (1, "Con al menos una intérprete mujer", NARANJA)]
    cats = [("llm_cuerpo", "Referencia al cuerpo\nde una mujer"), ("llm_agencia", "Mujer como sujeto\nque decide (agencia)")]
    ancho = 0.36
    for j, (g, etq, color) in enumerate(grupos):
        sub = df[df.participa_mujer == g]
        for i, (v, _) in enumerate(cats):
            k, n = int(sub[v].sum()), len(sub)
            li, ls = proportion_confint(k, n, method="wilson")
            xi = i + (j - 0.5) * ancho
            ax.bar(xi, 100 * k / n, width=ancho - 0.02, color=color, label=etq if i == 0 else None, zorder=2)
            ax.errorbar(xi, 100 * k / n, yerr=[[100 * (k / n - li)], [100 * (ls - k / n)]], fmt="none",
                        ecolor=TINTA, elinewidth=1.1, capsize=4, zorder=3)
            ax.text(xi, 100 * ls + 2.5, f"{100 * k / n:.0f} %", ha="center", fontsize=8.5, color=TINTA)
    ax.set_xticks(range(len(cats)), [c[1] for c in cats])
    ax.set_ylim(0, 115)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_ylabel("Porcentaje de canciones")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    n0, n1 = (df.participa_mujer == 0).sum(), (df.participa_mujer == 1).sum()
    encabezado(fig, "Cuerpo y agencia femenina según quién interpreta",
               f"Proporción e IC 95 % (Wilson) · solo hombres n = {n0} · con mujer n = {n1}")
    guardar(fig, "fig3_mujer_interprete.png")


def fig_mattr(df):
    fig, ax = plt.subplots(figsize=(7, 4.4))
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.12, right=0.97)
    pers = sorted(df.periodo.unique())
    datos = [df.loc[df.periodo == p, "mattr50"] for p in pers]
    bp = ax.boxplot(datos, widths=0.45, patch_artist=True, showfliers=False,
                    medianprops={"color": TINTA, "lw": 2}, whiskerprops={"color": TINTA2},
                    capprops={"color": TINTA2}, boxprops={"color": TINTA2})
    for caja in bp["boxes"]:
        caja.set_facecolor("#cfe0f6")
    rng = np.random.default_rng(cfg.SEMILLA)
    for i, p in enumerate(pers, 1):
        for e, color, etq in [(1, AZUL, "Top 10 anual"), (2, NARANJA, "Otros números uno")]:
            d = df.loc[(df.periodo == p) & (df.estrato == e), "mattr50"]
            ax.scatter(i + rng.uniform(-0.14, 0.14, len(d)), d, s=20, color=color, edgecolor="white", lw=0.7,
                       zorder=3, label=etq if i == 1 else None)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_xticks(range(1, len(pers) + 1), [f"{ETQ_PER[p]}\n(n = {len(d)})" for p, d in zip(pers, datos)])
    ax.set_ylabel("MATTR (ventana de 50 palabras)")
    ax.yaxis.set_major_formatter(COMA)
    encabezado(fig, "Riqueza léxica de las letras, por periodo",
               "MATTR: promedio de palabras distintas por ventana de 50 · más alto = vocabulario más variado",
               "Fuente: letras procesadas en memoria; medida determinística (no depende del LLM).")
    guardar(fig, "fig4_riqueza_lexica.png")


def fig_kappas():
    ruta = cfg.DIR_RESULTADOS / "kappas.csv"
    if not ruta.exists():
        return
    k = pd.read_csv(ruta)
    nombres = {"sexual": "Nivel sexual (0–2, κ ponderado)", "sexual_explicito": "Sexual explícito (sí/no)",
               "cuerpo": "Cuerpo de la mujer", "agencia": "Agencia femenina"}
    fig, ax = plt.subplots(figsize=(7.6, 4.9))
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.31, right=0.97)
    for x0, x1, etq in [(0.41, 0.60, "moderado"), (0.61, 0.80, "sustancial"), (0.81, 1.0, "casi perfecto")]:
        ax.axvspan(x0, x1, color="#f3f2ef", zorder=0)
        ax.text((x0 + x1) / 2, 3.55, etq, ha="center", fontsize=7.5, color=TINTA2)
    ax.axvline(0.61, color=TINTA2, lw=1, ls="--", zorder=1)
    ax.axvline(0, color=TINTA2, lw=0.8, zorder=1)
    for i, cat in enumerate(nombres):
        s = k[k.categoria == cat]
        hh = s[s.comparacion.str.startswith("humano")].iloc[0]
        lc = s[s.comparacion == "LLM vs consenso humano"].iloc[0]
        lh = s[s.comparacion.str.startswith("LLM vs humano")]
        y = 3 - i
        ax.errorbar(hh.kappa, y + 0.18, xerr=[[hh.kappa - hh.ic95_inf], [hh.ic95_sup - hh.kappa]], fmt="o",
                    color=NARANJA, ms=7, elinewidth=1.4, capsize=4, zorder=3,
                    label="Humano A vs humano B" if i == 0 else None)
        ax.errorbar(lc.kappa, y - 0.18, xerr=[[lc.kappa - lc.ic95_inf], [lc.ic95_sup - lc.kappa]], fmt="o",
                    color=AZUL, ms=7, elinewidth=1.4, capsize=4, zorder=3,
                    label="LLM vs consenso humano" if i == 0 else None)
        ax.scatter(lh.kappa, [y - 0.18] * len(lh), marker="D", s=26, facecolor="white", edgecolor=AZUL,
                   lw=1.3, zorder=4, label="LLM vs cada codificador" if i == 0 else None)
    ax.set_yticks([3, 2, 1, 0], list(nombres.values()))
    ax.set_ylim(-0.6, 3.8)
    ax.set_xlim(-0.3, 1.02)
    ax.set_xlabel("Kappa de Cohen (barras: IC 95 % bootstrap)")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.xaxis.set_major_formatter(COMA)
    encabezado(fig, "El modelo no alcanzó el umbral en ninguna categoría",
               "Línea discontinua: umbral fijado antes de codificar (κ ≥ 0,61) · submuestra aleatoria de 50 canciones",
               "Fuente: doble anotación humana (sin acceso al modelo) y codificación LLM (prompt v1.0). Escala de Landis y Koch (1977).")
    guardar(fig, "fig5_kappas.png")


def fig_triangulacion():
    ruta = cfg.DIR_RESULTADOS / "triangulacion_submuestra.csv"
    if not ruta.exists():
        return
    t = pd.read_csv(ruta)
    quienes = [("A", "Codificador humano A", NARANJA), ("B", "Codificador humano B", AGUA), ("LLM", "Modelo (LLM)", AZUL)]
    pers = sorted(t.periodo.unique())
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.11, right=0.97)
    ancho = 0.26
    for j, (q, etq, color) in enumerate(quienes):
        s = t[t.codificador == q].set_index("periodo").loc[pers]
        x = np.arange(len(pers)) + (j - 1) * ancho
        ax.bar(x, s.media_nivel, width=ancho - 0.03, color=color, label=etq, zorder=2)
        for xi, v in zip(x, s.media_nivel):
            ax.text(xi, v + 0.04, n_es(v), ha="center", fontsize=8, color=TINTA)
    ns = t[t.codificador == "LLM"].set_index("periodo").loc[pers, "n"]
    ax.set_xticks(range(len(pers)), [f"{ETQ_PER[p]}\n(n = {int(v)})" for p, v in zip(pers, ns)])
    ax.set_ylim(0, 2.15)
    ax.set_yticks([0, 0.5, 1, 1.5, 2], ["0\nninguno", "0,5", "1\ninsinuado", "1,5", "2\nexplícito"])
    ax.set_ylabel("Nivel medio de contenido sexual")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    encabezado(fig, "Las tres codificaciones ven un aumento; el modelo, un nivel más alto",
               "Nivel medio de contenido sexual (0–2) por periodo, en la submuestra aleatoria de validación",
               "Fuente: codificación humana (A y B, sin acceso al modelo) y codificación LLM (prompt v1.0) de las mismas 50 canciones.")
    guardar(fig, "fig1_triangulacion.png")


def fig_lexico(df):
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    fig.subplots_adjust(top=0.79, bottom=0.17, left=0.11, right=0.97)
    pers = sorted(df.periodo.unique())
    grupos = [(1, "Estrato 1: top 10 anual (censo)", AZUL), (2, "Estrato 2: otros números uno (muestra)", NARANJA)]
    ancho = 0.36
    for j, (e, etq, color) in enumerate(grupos):
        for i, per in enumerate(pers):
            g = df[(df.estrato == e) & (df.periodo == per)]
            k, m = int(g.lex_sexual_presente.sum()), len(g)
            li, ls = proportion_confint(k, m, method="wilson")
            xi = i + (j - 0.5) * ancho
            ax.bar(xi, 100 * k / m, width=ancho - 0.03, color=color, label=etq if i == 0 else None, zorder=2)
            ax.errorbar(xi, 100 * k / m, yerr=[[100 * (k / m - li)], [100 * (ls - k / m)]], fmt="none",
                        ecolor=TINTA, elinewidth=1.1, capsize=4, zorder=3)
            ax.text(xi, 100 * ls + 2.5, f"{100 * k / m:.0f} %\n{k}/{m}", ha="center", fontsize=7.5, color=TINTA)
    ax.set_xticks(range(len(pers)), [ETQ_PER[p] for p in pers])
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_ylabel("Canciones con algún término sexual")
    ax.legend(frameon=False, fontsize=8.2, loc="upper left", ncol=2)
    encabezado(fig, "El vocabulario sexual crece en el top 10 anual, no en los demás éxitos",
               f"Canciones con al menos un término del léxico sexual, IC 95 % (Wilson) · n = {len(df)} analizables",
               "Fuente: Billboard Hot Latin Songs 2011–2025 (vía Wikipedia); léxico determinístico v1.0, no depende del LLM.")
    guardar(fig, "fig2_lexico_sexual.png")


def fig_urbana(prop_urbana):
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    fig.subplots_adjust(top=0.79, bottom=0.18, left=0.10, right=0.97)
    ax.plot(prop_urbana.index, 100 * prop_urbana.values, color=AZUL, lw=2, marker="o", ms=6, zorder=3)
    for x, v in zip(prop_urbana.index, prop_urbana.values):
        ax.text(x, 100 * v + 4, f"{round(10 * v)}", ha="center", fontsize=7.5, color=TINTA2)
    ax.set_xticks(range(2011, 2026, 2))
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_xlabel("Año de la lista de fin de año")
    ax.set_ylabel("Canciones urbanas en el top 10")
    encabezado(fig, "Peso de la música urbana en el top 10 anual de Hot Latin Songs",
               "Porcentaje de canciones urbanas o híbridas en el top 10 de cada año (número sobre cada punto)",
               "Fuente: top 10 anual Billboard Hot Latin Songs 2011–2025 (vía Wikipedia); clasificación de género v1.0.")
    guardar(fig, "fig3_urbana_anual.png")


COMA = FuncFormatter(lambda v, _: f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",") if v % 1 else f"{v:.0f}")


def n_es(v):
    return f"{v:.2f}".replace(".", ",")


def main():
    DIR_FIG.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(cfg.DIR_DATOS / "base_analitica.csv")
    df = base[(base.analizable == 1) & base.llm_sexual.notna()]
    prop_urbana = pd.read_csv(cfg.DIR_RESULTADOS / "proporcion_urbana_anual.csv", index_col=0).prop_urbana
    for viejo in DIR_FIG.glob("*.png"):
        viejo.unlink()
    fig_triangulacion()
    fig_lexico(df)
    fig_urbana(prop_urbana)
    fig_mattr(df)
    fig_kappas()
    print("Figuras en", DIR_FIG)


if __name__ == "__main__":
    main()
