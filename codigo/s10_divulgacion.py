"""
Paso 10 — Producto divulgativo: carrusel de Instagram (8 láminas, 1080 × 1350 px).

Público declarado: estudiantes universitarios (18 a 25 años) de la Universidad del Magdalena que
escuchan reggaetón. Toda cifra se lee de resultados/ para que el carrusel no pueda afirmar nada
distinto de lo que sustenta el informe (regla de oro de la divulgación).

Salidas: entregables/divulgacion/lamina_1.png … lamina_8.png y carrusel.pdf
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

R = cfg.DIR_RESULTADOS
SALIDA = cfg.RAIZ / "entregables" / "divulgacion"
FONDO, TINTA, TINTA2, ACENTO = "#f6f2ea", "#141414", "#5a5650", "#d6336c"
AZUL, NARANJA, AGUA = "#2a78d6", "#eb6834", "#1baf7a"
TOTAL = 8


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def datos():
    tri = pd.read_csv(R / "triangulacion_submuestra.csv")
    dec = pd.read_csv(R / "categorias_validas.csv").set_index("categoria")
    desc = pd.read_csv(R / "descriptivos_periodo.csv").set_index("periodo")
    disc = pd.read_csv(R / "discrepancias.csv")
    base = pd.read_csv(cfg.DIR_DATOS / "base_analitica.csv")
    an = base[base.analizable == 1]
    pres = an.groupby(["estrato", "periodo"]).lex_sexual_presente.mean().mul(100)
    return {
        "pres": pres, "n1": int((an.estrato == 1).sum()), "n2": int((an.estrato == 2).sum()),
        "cons": tri[tri.codificador == "consenso"].set_index("periodo"),
        "tri": tri, "dec": dec, "desc": desc,
        "n": int(base.analizable.sum()), "n_val": int(tri[tri.codificador == "A"].n.sum()),
        "agencia_desacuerdo": int(((disc.categoria == "agencia") & (disc.tipo == "desacuerdo entre humanos")).sum()),
        "sobre": int(((disc.categoria == "sexual") & (disc.direccion == "LLM sobrecodifica")).sum()),
        "dif": int(((disc.categoria == "sexual") & (disc.tipo == "LLM difiere del consenso")).sum()),
    }


def grafico_barras(tri) -> str:
    """SVG: nivel medio de contenido sexual por periodo, A / B / IA."""
    pers = [("P1_2011_2015", "2011–2015"), ("P2_2016_2020", "2016–2020"), ("P3_2021_2025", "2021–2025")]
    quien = [("A", NARANJA, "Persona 1"), ("B", AGUA, "Persona 2"), ("LLM", AZUL, "IA")]
    W, H, base_y, alto = 900, 520, 430, 360
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">']
    for v, etq in [(0, "nada"), (1, "insinuado"), (2, "explícito")]:
        y = base_y - alto * v / 2
        out.append(f'<line x1="170" x2="{W - 10}" y1="{y}" y2="{y}" stroke="#d9d4ca" stroke-width="2"/>')
        out.append(f'<text x="158" y="{y + 9}" text-anchor="end" font-size="26" fill="{TINTA2}">{etq}</text>')
    for i, (per, etq) in enumerate(pers):
        x0 = 195 + i * 240
        for j, (q, color, _) in enumerate(quien):
            v = float(tri[(tri.codificador == q) & (tri.periodo == per)].media_nivel.iloc[0])
            h = alto * v / 2
            x = x0 + j * 72
            out.append(f'<rect x="{x}" y="{base_y - h}" width="62" height="{h}" rx="6" fill="{color}"/>')
            out.append(f'<text x="{x + 31}" y="{base_y - h - 12}" text-anchor="middle" font-size="24" '
                       f'font-weight="700" fill="{TINTA}">{coma(v)}</text>')
        out.append(f'<text x="{x0 + 98}" y="{base_y + 48}" text-anchor="middle" font-size="30" '
                   f'font-weight="600" fill="{TINTA}">{etq}</text>')
    out.append("</svg>")
    leyenda = "".join(f'<span class="ley"><i style="background:{c}"></i>{t}</span>' for _, c, t in quien)
    return "".join(out) + f'<div class="leyenda">{leyenda}</div>'


def grafico_estratos(pres) -> str:
    """SVG: % de canciones con vocabulario sexual por periodo, top 10 anual vs otros números uno."""
    pers = [("P1_2011_2015", "2011–2015"), ("P2_2016_2020", "2016–2020"), ("P3_2021_2025", "2021–2025")]
    grupos = [(1, AZUL, "Top 10 del año"), (2, NARANJA, "Otros números uno")]
    W, H, base_y, alto = 900, 470, 390, 330
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">']
    for v in [0, 50, 100]:
        y = base_y - alto * v / 100
        out.append(f'<line x1="110" x2="{W - 10}" y1="{y}" y2="{y}" stroke="#d9d4ca" stroke-width="2"/>')
        out.append(f'<text x="98" y="{y + 9}" text-anchor="end" font-size="26" fill="{TINTA2}">{v} %</text>')
    for i, (per, etq) in enumerate(pers):
        x0 = 150 + i * 250
        for j, (e, color, _) in enumerate(grupos):
            v = float(pres.loc[(e, per)])
            h = alto * v / 100
            x = x0 + j * 100
            out.append(f'<rect x="{x}" y="{base_y - h}" width="88" height="{h}" rx="6" fill="{color}"/>')
            out.append(f'<text x="{x + 44}" y="{base_y - h - 12}" text-anchor="middle" font-size="28" '
                       f'font-weight="700" fill="{TINTA}">{v:.0f} %</text>')
        out.append(f'<text x="{x0 + 94}" y="{base_y + 48}" text-anchor="middle" font-size="30" '
                   f'font-weight="600" fill="{TINTA}">{etq}</text>')
    out.append("</svg>")
    leyenda = "".join(f'<span class="ley"><i style="background:{c}"></i>{t}</span>' for _, c, t in grupos)
    return "".join(out) + f'<div class="leyenda">{leyenda}</div>'


def laminas(d):
    dec = d["dec"]
    k_exp = coma(dec.loc["sexual_explicito", "kappa_llm_consenso"], 2)
    k_hh = coma(dec.loc["sexual_explicito", "kappa_humano_light"], 2)
    lex = d["desc"]["lex_sexual_x100_mediana"]
    mattr = d["desc"]["mattr50_mediana"]
    return [
        # 1 — portada
        f"""<div class="kicker">Estadística del reggaetón</div>
        <h1>¿Las letras del reggaetón se volvieron más explícitas?</h1>
        <p class="grande">No lo opinamos: <b>lo medimos</b> en las canciones urbanas más escuchadas de 2011 a 2025.</p>
        <p class="pista">Desliza →</p>""",
        # 2 — qué hicimos
        f"""<div class="kicker">Cómo lo hicimos</div>
        <h2>{d['n']} canciones, tres formas de medir</h2>
        <p>Tomamos de Billboard Hot Latin Songs (2011–2025) las canciones urbanas del <b>top 10 de cada año</b> ({d['n1']}) y una muestra al azar de las que fueron <b>número uno</b> alguna semana ({d['n2']}). Medimos sus letras de tres maneras:</p>
        <div class="tres"><div><span>📖</span><p><b>Un diccionario</b> de palabras sexuales, con jerga y dobles sentidos</p></div>
        <div><span>👀</span><p><b>Dos personas</b> leyendo {d['n_val']} letras elegidas al azar, sin ver lo que decía la IA</p></div>
        <div><span>🤖</span><p><b>Una IA</b> leyendo las {d['n']} letras con las mismas instrucciones</p></div></div>""",
        # 3 — hallazgo
        f"""<div class="kicker">Lo que encontramos</div>
        <h2>Sí: hay más contenido sexual en las canciones recientes</h2>
        <p>Las dos personas leyeron {d['n_val']} letras elegidas al azar. Las que consideraron <b>explícitas</b> pasaron de <b>{d['cons'].loc['P1_2011_2015', 'n_explicito']:.0f} de {d['cons'].loc['P1_2011_2015', 'n']:.0f}</b> (2011–2015) a <b>{d['cons'].loc['P3_2021_2025', 'n_explicito']:.0f} de {d['cons'].loc['P3_2021_2025', 'n']:.0f}</b> (2021–2025). La IA vio la misma subida, pero <b>siempre ve más</b>.</p>
        {grafico_barras(d['tri'])}
        <p class="nota">Nivel medio de contenido sexual (0 = nada, 1 = insinuado, 2 = explícito) en las mismas {d['n_val']} canciones. Con tan pocas canciones, las cifras son aproximadas.</p>""",
        # 4 — el diccionario
        f"""<div class="kicker">Pero ojo</div>
        <h2>Las palabras explícitas crecieron solo en el top 10</h2>
        <p>En el <b>top 10 del año</b>, las letras con palabras sexuales pasaron de {d['pres'].loc[(1, 'P1_2011_2015')]:.0f} % a {d['pres'].loc[(1, 'P3_2021_2025')]:.0f} %. En los <b>demás números uno</b> se quedaron cerca del 40 %, aunque las personas sí leyeron más contenido sexual: ahí el cambio va más por <b>dobles sentidos</b> que por palabras directas.</p>
        {grafico_estratos(d['pres'])}
        <p class="nota">Canciones con al menos una palabra del diccionario sexual, en las {d['n']} canciones.</p>""",
        # 5 — la IA no pasó la prueba
        f"""<div class="kicker">La IA bajo la lupa</div>
        <h2>La IA no pasó la prueba</h2>
        <p>Antes de mirar los datos fijamos una meta: para confiar en la IA, su acuerdo con las personas debía ser de al menos <b>0,61</b> en una escala de 0 a 1.</p>
        <div class="medidor"><div class="barra"><i style="width:{max(float(dec.loc['sexual_explicito', 'kappa_llm_consenso']), 0) * 100}%"></i><em style="left:61%"></em></div>
        <div class="medidor-txt"><span>Acuerdo de la IA: <b>{k_exp}</b></span><span>Meta: <b>0,61</b></span></div></div>
        <p>No fue que la IA se equivocara al azar: <b>exageró casi siempre en la misma dirección</b> ({d['sobre']} de sus {d['dif']} diferencias con las personas). Por eso no usamos sus porcentajes para concluir.</p>""",
        # 6 — lo que no pudimos medir
        f"""<div class="kicker">Lo que quedó abierto</div>
        <h2>¿Las letras dan más voz a las mujeres? No lo sabemos</h2>
        <p>Algunos estudios dicen que el reggaetón cosifica a las mujeres. Otros, que también les da espacio para decidir sobre su cuerpo y su vida.</p>
        <p>Quisimos medir esa segunda idea y fue lo más difícil: <b>las dos personas no coincidieron en {d['agencia_desacuerdo']} de {d['n_val']} canciones</b>, y la IA tampoco pasó la prueba aquí. Sin un acuerdo firme, no hay un dato confiable que mostrar.</p>
        <p class="nota">Que algo sea difícil de medir también es un resultado.</p>""",
        # 7 — vocabulario
        f"""<div class="kicker">Un dato más</div>
        <h2>Las letras recientes repiten menos</h2>
        <p>Medimos qué tan variado es el vocabulario: cuántas palabras distintas aparecen en cada tramo de 50 palabras.</p>
        <div class="cifras"><div><b>{coma(mattr['P1_2011_2015'], 2)}</b><span>2011–2015</span></div><div class="flecha">→</div><div><b>{coma(mattr['P3_2021_2025'], 2)}</b><span>2021–2025</span></div></div>
        <p>Pasa en el top 10 y en los demás números uno. Ojo: esto mide variedad de palabras, no calidad. No dice que las canciones nuevas sean mejores.</p>""",
        # 8 — límites
        f"""<div class="kicker">Antes de compartir</div>
        <h2>Lo que este estudio <u>no</u> dice</h2>
        <ul><li>No dice <b>por qué</b> cambiaron las letras.</li>
        <li>No dice que escuchar reggaetón <b>cause</b> nada en quien lo escucha.</li>
        <li>Habla de los <b>grandes éxitos en Estados Unidos</b>, no de todo el reggaetón ni de Colombia.</li></ul>
        <div class="ficha"><b>Ficha técnica:</b> {d['n']} canciones urbanas de Billboard Hot Latin Songs, 2011–2025: {d['n1']} del top 10 anual (todas) y {d['n2']} de los números uno semanales (muestra aleatoria) ·
        validación con 2 personas en {d['n_val']} canciones · informe técnico completo disponible con el equipo.<br>
        Proyecto de Estadística Industrial · Universidad del Magdalena · 2026-II</div>""",
    ]


CSS = f"""
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1080px; height: 1350px; background: {FONDO}; font-family: Inter, 'DejaVu Sans', sans-serif;
  color: {TINTA}; padding: 90px 90px 150px; position: relative; overflow: hidden;
  display: flex; flex-direction: column; justify-content: center; }}
.kicker {{ font-size: 30px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: {ACENTO}; margin-bottom: 30px; }}
h1 {{ font-family: 'Inter Display', Inter, sans-serif; font-size: 112px; line-height: 1.02; font-weight: 800; letter-spacing: -2px; margin-bottom: 60px; }}
h2 {{ font-family: 'Inter Display', Inter, sans-serif; font-size: 66px; line-height: 1.06; font-weight: 800; letter-spacing: -1px; margin-bottom: 40px; }}
p {{ font-size: 36px; line-height: 1.38; margin-bottom: 28px; color: #26241f; }}
p.grande {{ font-size: 46px; line-height: 1.3; }}
p.pista {{ position: absolute; bottom: 150px; right: 90px; font-size: 34px; font-weight: 700; color: {ACENTO}; }}
p.nota {{ font-size: 28px; color: {TINTA2}; }}
.tres {{ display: grid; gap: 26px; margin-top: 20px; }}
.tres div {{ background: #fff; border-radius: 22px; padding: 30px 34px; font-size: 34px; line-height: 1.3; display: flex; gap: 26px; align-items: center; }}
.tres span {{ font-size: 60px; }} .tres p {{ margin: 0; font-size: 34px; }}
svg {{ display: block; margin: 10px auto 0; }}
.leyenda {{ display: flex; gap: 40px; justify-content: center; font-size: 28px; margin: 10px 0 18px; }}
.ley i {{ display: inline-block; width: 26px; height: 26px; border-radius: 6px; margin-right: 10px; vertical-align: -4px; }}
.caso {{ background: #fff; border-left: 10px solid {ACENTO}; border-radius: 14px; padding: 28px 34px; font-size: 34px; line-height: 1.35; margin: 10px 0 34px; }}
.medidor {{ margin: 20px 0 46px; }}
.barra {{ height: 56px; background: #e5dfd4; border-radius: 28px; position: relative; }}
.barra i {{ position: absolute; left: 0; top: 0; bottom: 0; background: {AZUL}; border-radius: 28px; }}
.barra em {{ position: absolute; top: -14px; bottom: -14px; width: 6px; background: {TINTA}; }}
.medidor-txt {{ display: flex; justify-content: space-between; font-size: 32px; margin-top: 18px; }}
.cifras {{ display: flex; align-items: center; justify-content: center; gap: 50px; margin: 30px 0 50px; }}
.cifras div {{ text-align: center; }} .cifras b {{ display: block; font-size: 120px; font-weight: 800; color: {AZUL}; }}
.cifras span {{ font-size: 32px; color: {TINTA2}; }} .cifras .flecha {{ font-size: 90px; color: {TINTA2}; }}
ul {{ padding-left: 44px; margin-bottom: 40px; }} li {{ font-size: 38px; line-height: 1.35; margin-bottom: 20px; }}
.ficha {{ background: #fff; border-radius: 18px; padding: 28px 32px; font-size: 26px; line-height: 1.4; color: #2a2722; }}
.pie {{ position: absolute; left: 90px; right: 90px; bottom: 52px; display: flex; justify-content: space-between;
  font-size: 24px; color: {TINTA2}; border-top: 2px solid #d9d4ca; padding-top: 18px; }}
"""


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    d = datos()
    from playwright.sync_api import sync_playwright
    rutas = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page(viewport={"width": 1080, "height": 1350})
        for i, cuerpo in enumerate(laminas(d), 1):
            html = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
                    f'{cuerpo}<div class="pie"><span>Estadística del reggaetón · U. del Magdalena</span>'
                    f'<span>{i}/{TOTAL}</span></div></body></html>')
            pag.set_content(html)
            pag.wait_for_timeout(150)
            ruta = SALIDA / f"lamina_{i}.png"
            pag.screenshot(path=str(ruta), full_page=False)
            rutas.append(ruta)
        nav.close()
    from PIL import Image
    imgs = [Image.open(r).convert("RGB") for r in rutas]
    imgs[0].save(SALIDA / "carrusel.pdf", save_all=True, append_images=imgs[1:], resolution=150)
    print("Carrusel:", SALIDA)


if __name__ == "__main__":
    main()
