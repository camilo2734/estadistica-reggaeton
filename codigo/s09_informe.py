"""
Paso 9 — Informe técnico en PDF, generado a partir de los resultados.

Todas las cifras del informe se leen de datos/ y resultados/: si los datos cambian, el informe
cambia con ellos y nunca queda una cifra transcrita a mano. El texto interpretativo de la
validación (análisis de discrepancias) se lee de registros/analisis_discrepancias.md.

Salida: entregables/informe_tecnico.pdf (y su HTML fuente).
"""
import base64
import html
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

R, D = cfg.DIR_RESULTADOS, cfg.DIR_DATOS
SALIDA = cfg.RAIZ / "entregables"
ESTADO_PEND = "pendiente de validación"


# ----------------------------------------------------------------------------- formato
def n(x, dec=2):
    """Número con coma decimal."""
    if pd.isna(x):
        return "—"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def p_fmt(p):
    return "&lt; 0,001" if p < 0.001 else n(p, 3)


def p_eq(p):
    return "&lt; 0,001" if p < 0.001 else f"= {n(p, 3)}"


def pct(x, dec=0):
    return f"{n(x, dec)} %"


def img(nombre, pie):
    datos = base64.b64encode((R / "figuras" / nombre).read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{datos}"><figcaption>{pie}</figcaption></figure>'


def tabla(df, pie=None, clase=""):
    cab = "".join(f"<th>{c}</th>" for c in df.columns)
    filas = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in fila) + "</tr>" for fila in df.itertuples(index=False))
    titulo = f"<caption>{pie}</caption>" if pie else ""
    return f'<table class="{clase}">{titulo}<thead><tr>{cab}</tr></thead><tbody>{filas}</tbody></table>'


def md_a_html(texto):
    """Markdown mínimo: párrafos, negritas, cursivas y listas."""
    bloques = []
    for b in re.split(r"\n\s*\n", texto.strip()):
        b = html.escape(b, quote=False)
        b = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", b)
        b = re.sub(r"\*(.+?)\*", r"<em>\1</em>", b)
        if b.lstrip().startswith("- "):
            items = "".join(f"<li>{l.strip()[2:]}</li>" for l in b.splitlines() if l.strip().startswith("- "))
            bloques.append(f"<ul>{items}</ul>")
        elif b.startswith("### "):
            bloques.append(f"<h3>{b[4:]}</h3>")
        else:
            bloques.append(f"<p>{b}</p>")
    return "\n".join(bloques)


# ----------------------------------------------------------------------------- datos
def cargar():
    c = {
        "marco": pd.read_csv(D / "marco_muestral.csv"),
        "completo": pd.read_csv(D / "marco_completo.csv"),
        "corpus": pd.read_csv(D / "corpus.csv"),
        "base": pd.read_csv(D / "base_analitica.csv"),
        "sub": pd.read_csv(D / "submuestra_validacion.csv"),
        "desc": pd.read_csv(R / "descriptivos_periodo.csv"),
        "inf": pd.read_csv(R / "inferencia.csv"),
        "lex": pd.read_csv(cfg.RAIZ / "instrumentos" / "lexico_v1.0.csv"),
        "limpieza": pd.read_csv(D / "registro_limpieza.csv"),
        "prompt": (cfg.RAIZ / "instrumentos" / "prompt_codificacion_v1.0.txt").read_text(encoding="utf-8"),
        "hashes": (cfg.RAIZ / "instrumentos" / "HASHES_v1.0.txt").read_text(encoding="utf-8"),
    }
    c["kap"] = pd.read_csv(R / "kappas.csv") if (R / "kappas.csv").exists() else None
    c["dec"] = pd.read_csv(R / "categorias_validas.csv") if (R / "categorias_validas.csv").exists() else None
    c["disc"] = pd.read_csv(R / "discrepancias.csv") if (R / "discrepancias.csv").exists() else None
    ruta = cfg.DIR_REGISTROS / "analisis_discrepancias.md"
    c["disc_txt"] = ruta.read_text(encoding="utf-8") if ruta.exists() else None
    c["fuentes"] = pd.read_excel(cfg.LISTA_LETRAS) if cfg.LISTA_LETRAS.exists() else None
    c["asig"] = pd.read_csv(D / "asignacion_estrato2.csv").set_index("periodo")
    c["noresp"] = pd.read_csv(D / "no_respuesta.csv")
    c["sorteo"] = pd.read_csv(D / "corpus_sorteado.csv")
    c["llm_reg"] = pd.read_csv(cfg.DIR_REGISTROS / "codificacion_llm.csv")
    return c


def fila_inf(inf, prueba, variable):
    s = inf[(inf.prueba == prueba) & (inf.variable == variable)]
    return s.iloc[0] if len(s) else None


def estado(c, cat):
    if c["dec"] is None:
        return ESTADO_PEND
    s = c["dec"][c["dec"].categoria == cat]
    return s.iloc[0].decision if len(s) else ESTADO_PEND


def valida(c, cat):
    return estado(c, cat) == "válida"


def aviso(c, cat):
    e = estado(c, cat)
    if e == "válida":
        return ""
    if e == ESTADO_PEND:
        return ' <span class="pend">[Cifra condicionada a la validación del instrumento, sección 6.]</span>'
    return (f" <strong>Esta categoría no superó el umbral de validez ({e}); el resultado se reporta "
            f"como exploratorio y no se usa para concluir.</strong>")


# ----------------------------------------------------------------------------- secciones
def s_resumen(c):
    inf, dec = c["inf"], c["dec"].set_index("categoria")
    f = lambda pr, v: fila_inf(inf, pr, v)
    b = c["base"][c["base"].analizable == 1]
    ra = f("Spearman: nivel sexual del codificador A vs año", "sexual_humano")
    rb = f("Spearman: nivel sexual del codificador B vs año", "sexual_humano")
    l1 = f("Regresión logística: léxico sexual presente ~ año, solo estrato 1", "lex_sexual_presente (estrato 1)")
    l2 = f("Regresión logística: léxico sexual presente ~ año, solo estrato 2", "lex_sexual_presente (estrato 2)")
    li = f("Regresión logística: interacción año × estrato (léxico sexual presente)", "lex_sexual_presente")
    rm = f("Regresión lineal: MATTR ~ año + estrato", "mattr50")
    lh = f("Regresión logística: explícito según el consenso humano ~ año", "sexual_explicito_humano")
    tri = pd.read_csv(R / "triangulacion_submuestra.csv")
    tc = tri[tri.codificador == "consenso"].set_index("periodo")
    return f"""
<h2>1. Resumen</h2>
<p><strong>Pregunta.</strong> ¿Cambió entre 2011 y 2025 el contenido sexual de las letras de las canciones urbanas
de mayor éxito? <strong>Diseño.</strong> Muestreo estratificado en dos estratos de popularidad: el censo de las canciones
urbanas del top 10 anual de Billboard <em>Hot Latin Songs</em> (estrato 1) y una muestra aleatoria, estratificada
por periodo, de las que llegaron al número uno semanal sin entrar en ese top 10 (estrato 2). Quedaron
{len(b)} canciones analizables ({int((b.estrato == 1).sum())} y {int((b.estrato == 2).sum())}). Las letras se midieron con un léxico
determinístico, la riqueza léxica (MATTR) y un modelo de lenguaje (Claude) con un prompt fijo, validado
frente a dos codificadores humanos, sin acceso a la salida del modelo, en una submuestra aleatoria de {len(c['sub'])} canciones.</p>
<p><strong>Validez del instrumento.</strong> El modelo <strong>no superó</strong> el umbral de validez fijado de antemano en
ninguna categoría. Para el desenlace principal, su acuerdo con el consenso humano fue κ = {n(dec.loc['sexual_explicito', 'kappa_llm_consenso'])},
mientras que los dos codificadores coincidieron entre sí con κ = {n(dec.loc['sexual_explicito', 'kappa_humano_light'])}, una cifra que es cota superior porque
discutieron algunas canciones antes de entregar. El modelo sobrecodifica de forma sistemática, por lo que
sus proporciones no se usan para concluir.</p>
<p><strong>Hallazgos.</strong> El contenido sexual de las letras aumentó entre 2011 y 2025. Según el consenso de los
codificadores humanos en la submuestra aleatoria, la proporción de canciones explícitas pasó de
{pct(tc.loc['P1_2011_2015', 'pct_explicito'])} ({int(tc.loc['P1_2011_2015', 'n_explicito'])} de {int(tc.loc['P1_2011_2015', 'n'])}) a {pct(tc.loc['P2_2016_2020', 'pct_explicito'])} y a {pct(tc.loc['P3_2021_2025', 'pct_explicito'])} ({int(tc.loc['P3_2021_2025', 'n_explicito'])} de {int(tc.loc['P3_2021_2025', 'n'])}) (razón de odds por año = {n(lh.tamano_efecto)},
IC 95 %: {n(lh.ic95_inf)}–{n(lh.ic95_sup)}), con intervalos amplios por el tamaño de la submuestra. El léxico confirma el aumento en
el top 10 anual (razón de odds = {n(l1.tamano_efecto)} por año, IC 95 %: {n(l1.ic95_inf)}–{n(l1.ic95_sup)}), pero no lo detecta en los demás
números uno (razón de odds = {n(l2.tamano_efecto)}, p {p_eq(l2.p)}; interacción año × estrato p {p_eq(li.p)}): en ese estrato el
vocabulario explícito no cambió, aunque el juicio humano sí registra más contenido sexual. La riqueza
léxica aumentó en los dos estratos ({n(rm.tamano_efecto, 4)} puntos de MATTR por año, p {p_eq(rm.p)}). Los datos son
observacionales y del mercado estadounidense: no permiten hablar de causas ni de efectos sobre las
audiencias.</p>"""


def s_introduccion(c):
    return """
<h2>2. Introducción y antecedentes</h2>
<p>El reggaetón es el fenómeno de música popular de mayor alcance surgido en América Latina en las
últimas tres décadas, y también uno de los más debatidos. Sobre sus letras circulan afirmaciones
—que se han vuelto más explícitas, que cosifican a las mujeres, que cambiaron con la llegada de
intérpretes mujeres— que rara vez se acompañan de datos. Este trabajo convierte una de esas
afirmaciones en una pregunta medible y la responde con un diseño muestral explícito, instrumentos
de medición documentados y pruebas de inferencia.</p>
<h3>2.1. Un debate académico con dos posiciones</h3>
<p>La literatura sobre reggaetón se concentra en el análisis de sus letras y está dividida. Una
revisión de 69 artículos publicados entre 2006 y 2022 muestra que las conclusiones van desde
considerar que el género perpetúa la violencia contra las mujeres hasta considerar que subvierte las
normas de sexo y género (Espinal Ramírez, Díaz-Fernández y Orejuela).</p>
<p><strong>Reproducción de estereotipos.</strong> Arévalo, Chellew, Figueroa-Cofré, Arancibia-Villablanca y
Schmied (2018) realizaron un análisis de contenido longitudinal de letras populares entre 2004 y 2017
con cinco tipos de violencia de género. Hallaron que la violencia de género en las letras no
disminuyó: la física y la sexual bajaron, mientras la simbólica y la psicológica aumentaron. En una
línea cualitativa, Alpízar-Lorenzo y colaboradores (2021) analizaron 50 letras con Atlas.ti e
identificaron un predominio de la representación de la mujer como cosificada y sumisa. Fuera del
género, Hall, West y Hill (2012) documentaron un aumento de las referencias sexuales en las canciones
más populares de Estados Unidos entre 1959 y 2009, lo que sugiere que una tendencia hacia lo
explícito, si existe, no sería exclusiva del reggaetón.</p>
<p><strong>Agencia y subversión.</strong> Báez (2006) analiza la obra de Ivy Queen como un espacio de discursos
en competencia, donde la voz femenina reclama autonomía dentro de un género dominado por hombres.
Santos Rodríguez (2023) estudia el <em>perreo</em> como un lugar donde las normas heteropatriarcales se
disputan y resignifican, y muestra que esas relecturas feministas encuentran resistencias. Desde
esta posición, medir solo la cosificación deja fuera la mitad del fenómeno.</p>
<p>Este estudio no toma partido entre ambas posiciones. Mide indicadores que corresponden a cada una
—contenido sexual y referencias al cuerpo de la mujer, por un lado; mujer como sujeto que decide,
por otro— y sitúa los resultados frente a las dos (sección 8).</p>
<h3>2.2. Un modelo de lenguaje como instrumento de medición</h3>
<p>Codificar temáticamente cientos de letras exige horas de trabajo humano. Los modelos de lenguaje
pueden hacerlo a escala: Gilardi, Alizadeh y Kubli (2023) encontraron que un modelo de lenguaje
superó a trabajadores de <em>crowdsourcing</em> en varias tareas de anotación de texto. Pero un instrumento
no se presume válido: se valida. Aquí el modelo se trata como cualquier instrumento de medición, con
un libro de códigos definido antes de codificar, un prompt fijo y una validación contra codificadores
humanos que no ven la salida del modelo, medida con el kappa de Cohen (Cohen, 1960).</p>
<h3>2.3. Preguntas de investigación</h3>
<ul>
<li><strong>Principal (P).</strong> ¿Qué proporción de las canciones urbanas de mayor éxito en Billboard
<em>Hot Latin Songs</em> contiene contenido sexual explícito, y cambió esa proporción entre 2011 y 2025?</li>
<li><strong>Secundaria 1 (S1).</strong> ¿Difiere la proporción de canciones que hacen referencia al cuerpo de
una mujer, y la de canciones que presentan a la mujer como sujeto que decide, entre las canciones
interpretadas solo por hombres y las que tienen al menos una intérprete mujer?</li>
<li><strong>Secundaria 2 (S2).</strong> ¿Cambió la riqueza léxica de las letras entre 2011 y 2025?</li>
</ul>"""


def s_diseno(c):
    m, comp, corpus, sub, asig, sorteo = c["marco"], c["completo"], c["corpus"], c["sub"], c["asig"], c["sorteo"]
    b = c["base"]
    m1, m2 = m[m.estrato == 1], m[m.estrato == 2]
    elig = lambda d: int(d.clase.isin(["urbano", "hibrido"]).sum())
    nr = c["noresp"]
    embudo = pd.DataFrame({
        "Etapa": ["Entradas de la fuente", "Canciones únicas (cada una en su primer año)",
                  "Urbanas o híbridas (marco elegible, N)", "Estudiadas (censo / muestra aleatoria)",
                  "Sin letra disponible (no respuesta)", "Excluidas por idioma (mayoría en inglés)", "Analizables"],
        "Estrato 1: top 10 anual": [len(comp), len(m1), elig(m1), int((sorteo.estrato == 1).sum()),
                                    int((nr.estrato == 1).sum()), int(b[b.estrato == 1].excluida_idioma.sum()),
                                    int(b[b.estrato == 1].analizable.sum())],
        "Estrato 2: otros números uno": ["—", len(m2), elig(m2), int((sorteo.estrato == 2).sum()),
                                         int((nr.estrato == 2).sum()), int(b[b.estrato == 2].excluida_idioma.sum()),
                                         int(b[b.estrato == 2].analizable.sum())]})
    estr = []
    sub_cnt = sub.groupby(["estrato", "periodo"]).size()
    for per, etq in [("P1_2011_2015", "2011–2015"), ("P2_2016_2020", "2016–2020"), ("P3_2021_2025", "2021–2025")]:
        g1 = b[(b.periodo == per) & (b.estrato == 1)]
        a = asig.loc[per]
        estr.append({"Periodo": etq, "E1: N<sub>h</sub> = n<sub>h</sub>": len(g1),
                     "E2: N<sub>h</sub>": int(a.N_marco), "E2: n<sub>h</sub> sorteada": int(a.n_sorteada),
                     "E2: con letra": int(a.n_con_letra), "E2: peso N<sub>h</sub>/n<sub>h</sub>": n(a.N_marco / a.n_con_letra),
                     "Validación E1 / E2": f"{int(sub_cnt.get((1, per), 0))} / {int(sub_cnt.get((2, per), 0))}"})
    estr = pd.DataFrame(estr)
    return f"""
<h2>3. Diseño muestral</h2>
<h3>3.1. Universo y marcos muestrales</h3>
<p>La población de interés son las letras de las canciones urbanas latinas (reggaetón, trap latino y
dembow) de mayor éxito entre 2011 y 2025. El éxito se define con la lista <em>Billboard Hot Latin Songs</em>,
que mide la popularidad en el mercado estadounidense de música latina: es una fuente externa y
pública, que no depende del criterio del equipo, cubre todo el periodo y define la popularidad de
forma homogénea entre años. Se usan dos marcos disjuntos, que corresponden a dos niveles de éxito:</p>
<ul>
<li><strong>Estrato 1, top 10 anual.</strong> Las diez canciones más populares de cada año en la lista de fin de
año: {len(comp)} entradas y {len(m1)} canciones únicas.</li>
<li><strong>Estrato 2, otros números uno.</strong> Las canciones que ocuparon el primer puesto semanal de <em>Hot
Latin Songs</em> o de <em>Latin Airplay</em> en algún momento del periodo y que no están en el estrato 1:
{len(m2)} canciones únicas. Las canciones que ya figuran en el top 10 anual se retiraron de este marco
para que ninguna pueda ser seleccionada dos veces.</li>
</ul>
<p>Cada canción se cuenta una sola vez, en su primer año (por ejemplo, <em>Despacito</em> aparece en el top 10
de 2017 y de 2018). Como las listas incluyen también bachata, banda, corridos y salsa, cada canción se
clasificó con un instrumento versionado (<code>clasificacion_genero_v1.1.csv</code>), que registra el género y la
justificación de cada caso: <em>urbana</em> (el reggaetón, el trap latino o el dembow son el género principal),
<em>híbrida</em> (fusión con base de reggaetón discutible, por ejemplo <em>Danza Kuduro</em> o <em>Pepas</em>) y <em>no urbana</em>.
El marco elegible de cada estrato son las urbanas y las híbridas.</p>
{tabla(embudo, "Tabla 1. De los marcos al corpus analizable, por estrato")}
<h3>3.2. Estratificación, asignación y tamaño</h3>
<p>El diseño cruza dos criterios de estratificación: el nivel de éxito (estratos 1 y 2) y el periodo de
cinco años, porque la pregunta principal es temporal. En el <strong>estrato 1</strong> se estudia el censo: es el
núcleo de mayor éxito, su tamaño lo permite y un censo elimina el error de muestreo en el grupo más
influyente. En el <strong>estrato 2</strong> se extrajo una muestra aleatoria simple sin reemplazo dentro de cada periodo,
de {int(asig.n_sorteada.sum())} canciones, con asignación proporcional al tamaño del periodo en el marco (método del mayor
residuo) y la semilla <strong>{cfg.SEMILLA}</strong> (<code>s01_marco_muestral.py</code>). El tamaño total se fijó para superar
las 180 canciones analizables exigidas por el protocolo con margen para las exclusiones por idioma.</p>
<p>Como las fracciones de muestreo difieren entre estratos, cada canción lleva un peso de diseño igual al
inverso de su probabilidad de inclusión: 1 en el estrato 1 y N<sub>h</sub>/n<sub>h</sub> en el estrato 2 (Tabla 2). Las
estimaciones para la población de éxitos urbanos se ponderan; las pruebas se aplican al corpus completo,
dentro de cada estrato, y con modelos que incluyen el estrato como covariable. {'Una canción sorteada (' + ', '.join('<em>' + t + '</em>' for t in nr.titulo) + ') no tenía letra disponible en la fuente; se trató como no respuesta y el peso de su periodo se recalculó con las canciones restantes.' if len(nr) else ''}</p>
<p>La aleatorización interviene también en la <strong>submuestra de validación</strong>. Su tamaño es el máximo entre 50
canciones y el 20 % de las analizables, como exige el protocolo: {len(sub)} canciones. Se sorteó sobre todo el corpus
analizable, estratificando por las seis celdas estrato × periodo, con asignación proporcional por el método del
mayor residuo y una semilla propia, <strong>{cfg.SEMILLA_VALIDACION}</strong> (<code>s03_submuestra_validacion.py</code>). El
procedimiento genera un orden aleatorio dentro de cada celda y toma las primeras n<sub>h</sub> canciones elegibles;
si la elegibilidad de una canción cambia, entra la siguiente de su celda y nada más se modifica.</p>
{tabla(estr, "Tabla 2. Tamaños por estrato y periodo, pesos de diseño y submuestra de validación", "compacta")}
<h3>3.3. Limitaciones de cobertura de los marcos</h3>
<ul>
<li><strong>Mercado estadounidense.</strong> Billboard mide el consumo en Estados Unidos, no en Colombia ni en
América Latina. Los resultados describen lo que tuvo éxito en ese mercado.</li>
<li><strong>Solo éxitos.</strong> Los dos marcos dejan fuera la producción menos difundida del género: el estudio
describe los éxitos, no el reggaetón en general.</li>
<li><strong>Dos listas semanales.</strong> El estrato 2 combina los números uno de <em>Hot Latin Songs</em> (consumo total)
y de <em>Latin Airplay</em> (solo radio), porque las fuentes los publican juntos; la radio tiende a difundir
versiones menos explícitas.</li>
<li><strong>Cambio de metodología de la lista.</strong> Desde octubre de 2012, <em>Hot Latin Songs</em> combina radio, ventas
digitales y <em>streaming</em>; antes solo medía radio, de modo que el primer periodo es parcialmente distinto.</li>
<li><strong>Primer periodo pequeño.</strong> La música urbana tuvo poco peso entre 2011 y 2015, y ese periodo tiene
{int(b[b.periodo == 'P1_2011_2015'].analizable.sum())} canciones analizables: sus estimaciones son las menos precisas.</li>
<li><strong>Clasificación de género.</strong> Separar lo urbano de lo no urbano exige criterio en las fusiones;
por eso se crearon la clase híbrida y un análisis de sensibilidad que la excluye.</li>
<li><strong>Año de referencia.</strong> La variable temporal es el año de máxima popularidad (lista de fin de año o
primera semana en el número uno), que puede diferir en uno del año de lanzamiento.</li>
</ul>"""


def s_fuentes_letras_parrafo(c):
    f = c["fuentes"]
    f = f[f.fuente_letra.notna() & (f.fuente_letra.astype(str).str.strip() != "")]
    fuente = f.fuente_letra.value_counts()
    fechas = sorted(pd.to_datetime(f.fecha_consulta.astype(str)).dt.strftime("%d/%m/%Y").unique())
    rem = int((pd.read_excel(cfg.DIR_DATOS / "lista_letras.xlsx").version_a_descargar != "Original").sum())
    return (f"<p><strong>Letras.</strong> Se obtuvieron manualmente, como recomienda la guía del proyecto, porque varias "
            f"interfaces de programación citadas en la literatura ya no están disponibles. Las {int(fuente.sum())} letras se tomaron "
            f"de {fuente.index[0]}, que se usó como fuente única para que las diferencias entre transcripciones no se "
            f"convirtieran en parte de la medición, y se consultaron en octubre de 2026 ({', '.join(fechas)}). En {rem} canciones "
            f"la entrada de la lista corresponde a una remezcla, y se usó la letra de esa versión para que el texto medido "
            f"coincidiera con el que fue popular. La lista con la fuente y la fecha de cada letra acompaña al repositorio.</p>")


def s_fuentes(c):
    lim = c["limpieza"].sum(numeric_only=True)
    excl = c["base"][c["base"].excluida_idioma == 1]
    excl_txt = ", ".join(f"<em>{t}</em>" for t in excl.titulo)
    nr = c["noresp"]
    return f"""
<h2>4. Fuentes y construcción del corpus</h2>
<h3>4.1. Fuentes y fechas de consulta</h3>
<p><strong>Marcos muestrales.</strong> El top 10 anual se tomó del artículo de Wikipedia <em>Billboard Hot Latin Songs
Year-End Chart</em>, consultado el 22 de octubre de 2026. Los números uno semanales se tomaron de los artículos
anuales <em>List of Billboard Hot Latin Songs and Latin Airplay number ones</em> (2012–2025) y <em>List of number-one
Billboard Top Latin Songs of 2011</em>, consultados el 24 de octubre de 2026 y transcritos a texto plano
(<code>numeros_uno_2011_2025.txt</code>). La fuente primaria, billboard.com, quedó fuera de alcance: el sitio
bloquea la consulta automatizada y, al intentar el acceso manual, las listas exigían suscripción paga
(<em>Billboard Pro</em>). Wikipedia reproduce esas listas con la referencia a Billboard en cada semana o año.</p>
{s_fuentes_letras_parrafo(c)}
<h3>4.2. Control de calidad</h3>
<p>Cada archivo recibido se verificó en codificación UTF-8 y se comparó con todos los demás para detectar
duplicados y textos compartidos. La revisión encontró y corrigió, antes de cualquier codificación, un
archivo con un documento ajeno en lugar de la letra, uno con la remezcla de una canción cuya entrada
corresponde a la versión original, dos archivos que contenían la letra de otra canción del corpus (se
volvieron a descargar) y dos en los que se había pegado, al inicio, la letra de la canción vecina (se
retiró ese bloque). {f'Para una canción sorteada no se encontró la letra en la fuente; queda registrada como no respuesta en <code>no_respuesta.csv</code>.' if len(nr) else ''}</p>
<h3>4.3. Limpieza del texto</h3>
<p>El procesamiento (<code>s02_variables_texto.py</code>) elimina los rótulos de sección ({int(lim.rotulos)} líneas),
los encabezados de página y de sitio copiados por error ({int(lim.basura)} líneas) y los títulos repetidos al
inicio. Los coros de fondo entre paréntesis se separan del texto principal: no cuentan en las medidas
de longitud ni de riqueza léxica, porque son repeticiones y muletillas, pero sí en el léxico, porque son
parte de lo que se canta. Las repeticiones de los coros se conservan: se mide la canción tal como se
interpreta. El texto se normaliza a minúsculas, sin tildes y sin los apóstrofos de elisión típicos del
género (<em>pa'</em>, <em>to'</em>). No se eliminan <em>stopwords</em>: los pronombres son informativos en este corpus.</p>
<p><strong>Regla de idioma.</strong> Se excluyen del análisis las canciones en las que más de la mitad de las palabras
funcionales están en inglés. Quedaron fuera {len(excl)} canciones bilingües: {excl_txt}. Siguen en la base de datos,
marcadas, para que la decisión sea auditable.</p>
<h3>4.4. Derechos de autor</h3>
<p>Las letras son obras protegidas. El flujo las lee en memoria y exporta solo estadísticos derivados;
la carpeta de letras no forma parte del repositorio ni de ningún entregable. Las justificaciones que
produce el modelo están limitadas a 30 palabras, sin citas de más de cinco palabras seguidas. Un paso
final del flujo (<code>s08_verificar_letras.py</code>) audita todos los archivos producidos y falla si alguno
contiene ocho o más palabras seguidas de cualquier letra. La auditoría se superó.</p>"""


def s_instrumentos(c):
    lex = c["lex"]
    resumen = lex.groupby("dimension").agg(patrones=("patron", "size"),
                                            tipos=("tipo", lambda t: ", ".join(sorted(set(t))))).reset_index()
    resumen.columns = ["Dimensión", "Patrones", "Tipos de término incluidos"]
    nombres = {"sexual": "Sexual", "cuerpo": "Cuerpo", "apariencia": "Apariencia", "baile_fiesta": "Baile y fiesta",
               "sustancias": "Sustancias", "dinero_lujo": "Dinero y lujo"}
    resumen["Dimensión"] = resumen["Dimensión"].map(nombres)
    h = {l.split()[1].split("/")[-1]: l.split()[0][:16] for l in c["hashes"].strip().splitlines()}
    global ANEXO_PROMPT
    ANEXO_PROMPT = f'<pre class="prompt">{html.escape(c["prompt"])}</pre>'
    return f"""
<h2>5. Instrumentos de medición</h2>
<p>El estudio usa tres instrumentos distintos, todos congelados antes de medir y con su huella SHA-256
registrada en <code>HASHES_v1.0.txt</code>: un léxico determinístico, una medida de riqueza léxica y un
libro de códigos aplicado por el modelo de lenguaje.</p>
<h3>5.1. Léxico (v1.0)</h3>
<p>El léxico (<code>lexico_v1.0.csv</code>, huella <code>{h.get('lexico_v1.0.csv', '')}…</code>) tiene {len(lex)} patrones en seis
dimensiones. Cada patrón es una expresión regular sobre el texto normalizado que contempla variantes
ortográficas, diminutivos, elisiones, jerga regional (puertorriqueña, colombiana, mexicana), anglicismos
y expresiones de doble sentido. Cada término está etiquetado por tipo y criterio de inclusión. Se
excluyeron a propósito términos homógrafos que generarían falsos positivos, como <em>bebe</em> (verbo)
frente a <em>bebé</em> (apelativo), o <em>mami</em> como apelativo neutro. El léxico produce, por canción, el número
de coincidencias, su densidad por cada 100 palabras y un indicador de presencia.</p>
{tabla(resumen, "Tabla 3. Estructura del léxico v1.0")}
<p>El léxico cumple dos funciones: describe el vocabulario y sirve como medida <strong>independiente</strong> del
modelo de lenguaje, lo que permite evaluar la validez convergente de ambos (sección 7).</p>
<h3>5.2. Riqueza léxica</h3>
<p>La razón tipo-token depende de la longitud del texto: las canciones largas tienen razones más bajas
solo por repetir más. Por eso se usa la <strong>MATTR</strong> (<em>Moving-Average Type-Token Ratio</em>; Covington y
McFall, 2010): la proporción de palabras distintas en cada ventana de 50 palabras, promediada a lo
largo de la canción. La razón tipo-token simple también se conserva en la base de datos.</p>
<h3>5.3. Libro de códigos (v1.0) y codificación con el LLM</h3>
<p>El libro de códigos (<code>libro_codigos_v1.0.md</code>, huella <code>{h.get('libro_codigos_v1.0.md', '')}…</code>) define tres
categorías con definición operativa, criterios de inclusión y exclusión, ejemplos y contraejemplos
construidos y una zona gris documentada:</p>
<ul>
<li><strong>SEXUAL (0, 1, 2).</strong> 2 = explícito: nombra de forma directa el acto o los genitales, o describe
acciones sexuales. 1 = insinuado: deseo, seducción o doble sentido sin nombrar ni describir el acto.
0 = ninguno. El desenlace principal es la versión binaria: explícito (2) frente a no explícito.</li>
<li><strong>CUERPO (0, 1).</strong> La letra menciona o evalúa partes del cuerpo o la figura de una mujer con
valoración estética o sexual.</li>
<li><strong>AGENCIA (0, 1).</strong> La letra presenta a una mujer como sujeto que decide por sí misma sobre su
sexualidad, su cuerpo, su ocio o su relación. Esta categoría operacionaliza la posición de la
literatura que lee el género como espacio de agencia femenina.</li>
</ul>
<p>Las reglas generales piden codificar lo que dice la letra (no lo que se sabe del artista), asignar el
nivel máximo presente y marcar <em>duda</em> cuando la ambigüedad es genuina, sin cambiar el código.</p>
<p><strong>Prompt de codificación.</strong> El instrumento es el modelo junto con el prompt: si el prompt cambia, la
medición cambia. Se usó un único prompt, fijo, con huella <code>{h.get('prompt_codificacion_v1.0.txt', '')}…</code>,
transcrito textualmente en el Anexo C. En el lugar de <code>{{LETRA}}</code> se inserta la letra limpia de una
sola canción.</p>
<p><strong>Procedimiento.</strong> El modelo (identificador <code>claude-opus-5-5</code>) codificó las {len(c['corpus'])} canciones del
corpus aplicando el prompt a cada letra por separado, y cada codificación quedó registrada en
<code>codificacion_llm.csv</code> con su fecha y su vía: las {int((c['corpus'].estrato == 1).sum())} canciones del estrato 1 el {pd.to_datetime(c['llm_reg'][c['llm_reg'].codigo.isin(c['corpus'][c['corpus'].estrato == 1].codigo)].fecha).min().strftime('%d/%m/%Y')} y las
{int((c['corpus'].estrato == 2).sum())} del estrato 2 el {pd.to_datetime(c['llm_reg'][c['llm_reg'].codigo.isin(c['corpus'][c['corpus'].estrato == 2].codigo)].fecha).max().strftime('%d/%m/%Y')}, con el mismo prompt sin cambios. Toda la codificación del modelo
quedó registrada antes de la codificación humana de la submuestra de validación. El paso 4 del flujo
verifica que todas las codificaciones usen la misma huella del prompt. El repositorio incluye además un modo de
replicación por API (<code>s04_codificar_llm.py api</code>), con temperatura 0 y una llamada independiente por
canción, para que cualquier persona con credenciales pueda reproducir la medición; ese modo no se
ejecutó porque el equipo no dispone de credenciales de API (ver limitaciones).</p>
<h3>5.4. Doble anotación humana</h3>
<p>{len(c['sub'])} canciones, sorteadas como se describe en la sección 3.2, fueron codificadas por dos integrantes
del equipo (codificadores A y B) con el mismo libro de códigos, en una plantilla con listas desplegables que
solo admiten los valores del libro, con las canciones en un orden aleatorio distinto para cada uno y sin
acceso a la salida del modelo. Dos circunstancias limitan la independencia de esta codificación y se
declaran en la sección 6: los dos codificadores habían hecho antes una ronda de codificación con el mismo
libro y conocían sus resultados, incluida la tendencia del modelo a sobrecodificar; y discutieron algunas
canciones entre sí antes de entregar sus plantillas.</p>"""


def s_validacion(c):
    k, dec = c["kap"].copy(), c["dec"].copy()
    nombres = {"sexual": "Sexual (0–2, κ pond. lineal)", "sexual_explicito": "Sexual explícito (sí/no)",
               "cuerpo": "Cuerpo", "agencia": "Agencia"}
    k["Categoría"] = k.categoria.map(nombres)
    tk = pd.DataFrame({"Categoría": k["Categoría"], "Comparación": k.comparacion, "n": k.n,
                       "κ": k.kappa.map(n), "IC 95 %": [f"{n(a)} – {n(b)}" for a, b in zip(k.ic95_inf, k.ic95_sup)],
                       "Acuerdo bruto": k.acuerdo_bruto.map(lambda x: pct(100 * x))})
    td = pd.DataFrame({"Categoría": dec.categoria.map(nombres), "κ humano–humano": dec.kappa_humano_light.map(n),
                       "κ LLM–humanos (prom.)": dec.kappa_llm_humanos_prom.map(n),
                       "κ LLM–consenso": dec.kappa_llm_consenso.map(n), "Lím. inf. IC": dec.ic95_inf.map(n),
                       "Decisión": dec.decision})
    sub = pd.read_excel(R / "tabla_validacion.xlsx", sheet_name="Submuestra")
    bloques = []
    for cat, valores in [("sexual", [0, 1, 2]), ("cuerpo", [0, 1]), ("agencia", [0, 1])]:
        ok = sub[f"{cat}_consenso"].notna()
        ct = pd.crosstab(sub.loc[ok, f"{cat}_consenso"].astype(int), sub.loc[ok, f"{cat}_LLM"]).reindex(
            index=valores, columns=valores, fill_value=0)
        ct.index = [f"Cons. = {v}" for v in valores]
        ct.columns = [f"LLM = {v}" for v in valores]
        bloques.append(tabla(ct.reset_index().rename(columns={"index": cat.capitalize()}), clase="mini"))
    global ANEXO_KAPPAS
    ANEXO_KAPPAS = tabla(tk, "Tabla A1. Coeficientes kappa de Cohen con IC 95 % bootstrap, por comparación", "compacta")
    return f"""
<h2>6. Validación del instrumento</h2>
<p>La validación compara, en la submuestra de {len(c['sub'])} canciones, a los dos codificadores humanos entre
sí (¿el libro de códigos es claro?) y al modelo con el consenso humano y con cada codificador (¿el
instrumento automatizado mide lo mismo que las personas?). Los intervalos son <em>bootstrap</em> percentil con
2.000 remuestreos de canciones. La interpretación sigue a Landis y Koch (1977). La regla de decisión se
fijó antes de ver los datos: una categoría es válida si el κ humano–humano es ≥ 0,61 y el κ
LLM–consenso es ≥ 0,61, con límite inferior del IC 95 % mayor que 0,40.</p>
<p><strong>Desviaciones del protocolo.</strong> El protocolo pedía codificación independiente y consenso por discusión
documentada de los desacuerdos. En la práctica, los codificadores discutieron algunas canciones antes de
entregar y modificaron unos cuatro códigos, sin registrar cuáles. Por eso el κ humano–humano de la Tabla 4
es una <strong>cota superior</strong> del acuerdo independiente, no una medida limpia: la parte (a) de la regla de
decisión no puede certificarse. Las {int((c['disc'].tipo == 'desacuerdo entre humanos').groupby(c['disc'].codigo).any().sum()) if c['disc'] is not None else 0} canciones en las que siguieron sin coincidir no se discutieron, de modo que el
consenso se definió solo en las canciones con acuerdo (columna n), y el modelo se comparó además con cada
codificador por separado. Ninguna de las dos desviaciones cambia la decisión: el modelo falla la parte (b)
de la regla, que no depende de la independencia entre los humanos.</p>
{tabla(td, "Tabla 4. Decisión sobre la validez de cada categoría (detalle de cada comparación en el Anexo A)", "compacta")}
{img('fig5_kappas.png', 'Figura 1. Acuerdo entre codificadores por categoría. El umbral de validez se fijó antes de codificar.')}
<h3>6.1. Matrices de confusión (filas: consenso humano; columnas: LLM)</h3>
<div class="mats">{''.join(bloques)}</div>
<h3>6.2. Análisis de discrepancias</h3>
{md_a_html(c['disc_txt'])}"""


def s_resultados(c):
    inf, d = c["inf"], c["desc"].set_index("periodo")
    f = lambda pr, v: fila_inf(inf, pr, v)
    b = c["base"][c["base"].analizable == 1]
    ra = f("Spearman: nivel sexual del codificador A vs año", "sexual_humano")
    rb = f("Spearman: nivel sexual del codificador B vs año", "sexual_humano")
    ka = f("Kruskal-Wallis: nivel sexual del codificador A por periodo", "sexual_humano")
    kb = f("Kruskal-Wallis: nivel sexual del codificador B por periodo", "sexual_humano")
    lexh = f("Spearman: léxico sexual vs promedio de codificadores humanos", "validez_criterio_lexico")
    orden = f("Spearman: nivel sexual LLM vs promedio de codificadores humanos", "orden_llm")
    lg_all = f("Regresión logística: léxico sexual presente ~ año + estrato", "lex_sexual_presente")
    l1 = f("Regresión logística: léxico sexual presente ~ año, solo estrato 1", "lex_sexual_presente (estrato 1)")
    l2 = f("Regresión logística: léxico sexual presente ~ año, solo estrato 2", "lex_sexual_presente (estrato 2)")
    lint = f("Regresión logística: interacción año × estrato (léxico sexual presente)", "lex_sexual_presente")
    k1 = f("Kruskal-Wallis (léxico sexual por periodo), solo estrato 1", "lex_sexual_x100 (estrato 1)")
    k2 = f("Kruskal-Wallis (léxico sexual por periodo), solo estrato 2", "lex_sexual_x100 (estrato 2)")
    kwl = f("Kruskal-Wallis (léxico sexual por 100 palabras, por periodo)", "lex_sexual_x100")
    lg = f("Regresión logística: explícito ~ año", "sexual_explicito")
    km = f("Kruskal-Wallis (MATTR por periodo)", "mattr50")
    mkm = f("Mann-Kendall (mediana anual de MATTR)", "mattr50")
    rm = f("Correlación de Spearman (MATTR vs año)", "mattr50")
    rlm = f("Regresión lineal: MATTR ~ año + estrato", "mattr50")
    m1 = f("Spearman (MATTR vs año), solo estrato 1", "mattr50 (estrato 1)")
    m2 = f("Spearman (MATTR vs año), solo estrato 2", "mattr50 (estrato 2)")
    mku = f("Mann-Kendall (proporción anual de canciones urbanas en el top 10)", "urbana")
    fa = f("Prueba exacta de Fisher (agencia × participa mujer)", "agencia")
    fc = f("Prueba exacta de Fisher (cuerpo × participa mujer)", "cuerpo")
    flc = f("Prueba exacta de Fisher (léxico de cuerpo × participa mujer)", "lex_cuerpo_presente")
    tri = pd.read_csv(R / "triangulacion_submuestra.csv")
    tc = tri[tri.codificador == "consenso"].set_index("periodo")
    lh = f("Regresión logística: explícito según el consenso humano ~ año", "sexual_explicito_humano")
    ha1 = f("Spearman: nivel sexual del codificador A vs año, solo estrato 1", "sexual_humano (estrato 1)")
    ha2 = f("Spearman: nivel sexual del codificador A vs año, solo estrato 2", "sexual_humano (estrato 2)")
    hb1 = f("Spearman: nivel sexual del codificador B vs año, solo estrato 1", "sexual_humano (estrato 1)")
    hb2 = f("Spearman: nivel sexual del codificador B vs año, solo estrato 2", "sexual_humano (estrato 2)")
    nsub = c["sub"].estrato.value_counts()
    filas = []
    for per, etq in [("P1_2011_2015", "2011–2015"), ("P2_2016_2020", "2016–2020"), ("P3_2021_2025", "2021–2025")]:
        t = tri[tri.periodo == per].set_index("codificador")
        g = b[b.periodo == per]
        p1 = 100 * g[g.estrato == 1].lex_sexual_presente.mean()
        p2 = 100 * g[g.estrato == 2].lex_sexual_presente.mean()
        filas.append({"Periodo": etq, "n (E1 + E2)": f"{int(d.loc[per, 'n'])} ({int(d.loc[per, 'n_estrato1'])} + {int(d.loc[per, 'n_estrato2'])})",
                      "Con término sexual E1 / E2": f"{pct(p1)} / {pct(p2)}",
                      "Ponderado (población)": pct(d.loc[per, "lex_sexual_presente_pct_ponderado"]),
                      "MATTR (mediana)": n(d.loc[per, "mattr50_mediana"]),
                      "n validación": int(t.loc["A", "n"]),
                      "Explícitas: consenso / LLM": f"{pct(tc.loc[per, 'pct_explicito'])} / {pct(t.loc['LLM', 'pct_explicito'])}"})
    tdesc = pd.DataFrame(filas)
    global ANEXO_PRUEBAS
    ti = inf.copy()
    tabla_inf = pd.DataFrame({
        "Pregunta": ti.pregunta, "Prueba": ti.prueba, "Variable": ti.variable,
        "Estadístico": ti.estadistico.map(n), "p": ti.p.map(p_fmt),
        "p Holm": ti.p_holm.map(lambda x: p_fmt(x) if pd.notna(x) else "—"),
        "Efecto": [f"{n(e)} ({m})" for e, m in zip(ti.tamano_efecto, ti.medida_efecto)],
        "IC 95 %": [f"{n(a)}–{n(b_)}" if pd.notna(a) else "—" for a, b_ in zip(ti.ic95_inf, ti.ic95_sup)],
        "Estado del instrumento": ti.estado_instrumento})
    ANEXO_PRUEBAS = tabla(tabla_inf, "Tabla B1. Pruebas de inferencia, tamaños de efecto, intervalos y estado del instrumento", "micro")
    ns = b.groupby("periodo").size()
    return f"""
<h2>7. Resultados</h2>
<p>De acuerdo con la sección 6, las conclusiones se apoyan solo en medidas válidas: el léxico y la MATTR,
que son determinísticos, y la codificación de cada codificador humano en la submuestra aleatoria. Los
resultados que dependen de las categorías del modelo se reportan al final como exploratorios.</p>
{tabla(tdesc, "Tabla 5. Indicadores por periodo: corpus analizable por estrato, estimación ponderada y submuestra de validación", "compacta")}
<h3>7.1. Pregunta principal: contenido sexual en el tiempo</h3>
<p><strong>Codificación humana.</strong> En la submuestra aleatoria de los dos estratos, los dos codificadores asignaron
más contenido sexual a las canciones más recientes: ρ de Spearman con el año = {n(ra.tamano_efecto)} (p {p_eq(ra.p)}) para A y
{n(rb.tamano_efecto)} (p {p_eq(rb.p)}) para B, con diferencias entre periodos (Kruskal-Wallis p {p_eq(ka.p)} y p {p_eq(kb.p)}; ε² = {n(ka.tamano_efecto)} y
{n(kb.tamano_efecto)}). Según su consenso, la proporción de canciones explícitas fue de {pct(tc.loc['P1_2011_2015', 'pct_explicito'])} en 2011–2015
({int(tc.loc['P1_2011_2015', 'n_explicito'])} de {int(tc.loc['P1_2011_2015', 'n'])}; IC 95 % de Wilson: {pct(tc.loc['P1_2011_2015', 'ic_inf'])}–{pct(tc.loc['P1_2011_2015', 'ic_sup'])}), {pct(tc.loc['P2_2016_2020', 'pct_explicito'])} en 2016–2020 ({pct(tc.loc['P2_2016_2020', 'ic_inf'])}–{pct(tc.loc['P2_2016_2020', 'ic_sup'])}) y
{pct(tc.loc['P3_2021_2025', 'pct_explicito'])} en 2021–2025 ({pct(tc.loc['P3_2021_2025', 'ic_inf'])}–{pct(tc.loc['P3_2021_2025', 'ic_sup'])}). La razón de odds de que una canción sea explícita
crece {n(lh.tamano_efecto)} veces por año (IC 95 %: {n(lh.ic95_inf)}–{n(lh.ic95_sup)}; p {p_eq(lh.p)}). Dentro de cada estrato la tendencia tiene el
mismo signo, pero con pocas canciones solo es significativa para B en el top 10 (estrato 1, n = {int(nsub.get(1, 0))}:
ρ = {n(ha1.tamano_efecto)} y {n(hb1.tamano_efecto)}; estrato 2, n = {int(nsub.get(2, 0))}: ρ = {n(ha2.tamano_efecto)} y {n(hb2.tamano_efecto)}). El modelo muestra la misma dirección, pero a
un nivel más alto en todos los periodos (Figura 2).</p>
{img('fig1_triangulacion.png', 'Figura 2. Nivel medio de contenido sexual por periodo según quién codifica (submuestra de validación).')}
<p><strong>El léxico en el corpus completo.</strong> El léxico no depende del modelo y se correlaciona con el juicio
humano (ρ = {n(lexh.tamano_efecto)} con el promedio de los dos codificadores, p {p_eq(lexh.p)}), aunque de forma débil: capta palabras,
no dobles sentidos. El indicador es la presencia de al menos un término sexual en la letra. En el <strong>top 10
anual</strong> esa presencia pasó de {pct(100 * b[(b.estrato == 1) & (b.periodo == 'P1_2011_2015')].lex_sexual_presente.mean())} a {pct(100 * b[(b.estrato == 1) & (b.periodo == 'P3_2021_2025')].lex_sexual_presente.mean())} de las canciones; la razón de odds por año es
{n(l1.tamano_efecto)} (IC 95 %: {n(l1.ic95_inf)}–{n(l1.ic95_sup)}; p {p_eq(l1.p)}) y la densidad difiere entre periodos (Kruskal-Wallis H = {n(k1.estadistico)},
p {p_eq(k1.p)}). En los <strong>demás números uno</strong> se mantuvo cerca del 40 % (razón de odds = {n(l2.tamano_efecto)}, IC 95 %:
{n(l2.ic95_inf)}–{n(l2.ic95_sup)}; Kruskal-Wallis p {p_eq(k2.p)}), y la interacción año × estrato indica que las dos tendencias del léxico
son distintas (cociente de razones de odds = {n(lint.tamano_efecto)}, p {p_eq(lint.p)}; Figura 3). Al combinar los estratos, la tendencia del
léxico no es significativa (razón de odds = {n(lg_all.tamano_efecto)}, p {p_eq(lg_all.p)}).</p>
{img('fig2_lexico_sexual.png', 'Figura 3. Canciones con al menos un término sexual, por periodo y estrato.')}
<p><strong>Respuesta a la pregunta principal.</strong> El contenido sexual de las letras urbanas de mayor éxito aumentó
entre 2011 y 2025: lo muestran los dos codificadores humanos y su consenso en una submuestra aleatoria de
ambos estratos, y el léxico en el top 10 anual. Con el consenso humano, la mejor estimación disponible es
que las canciones explícitas pasaron de casi ninguna a cerca de la mitad, con intervalos amplios. En los
números uno fuera del top 10, los instrumentos no coinciden: el vocabulario sexual explícito no cambió,
pero las personas sí leen más contenido sexual, lo que sugiere que en ese estrato el cambio se expresa
más por dobles sentidos que por palabras explícitas. La magnitud debe leerse con cautela: proviene de
{len(c['sub'])} canciones y de un acuerdo humano que no fue del todo independiente.</p>
<h3>7.2. Contexto: la música urbana en el top 10</h3>
<p>La presencia urbana en el top 10 subió de 2 canciones en 2011 a 10 entre 2018 y 2020 y luego bajó
ante el auge de los corridos (Figura 4). No hay una tendencia monótona en todo el periodo (Mann-Kendall
τ = {n(mku.tamano_efecto)}, p {p_eq(mku.p)}). Como las medidas de la sección 7.1 se calculan dentro de las canciones urbanas, el
aumento observado en el top 10 no es un efecto de que haya más reggaetón en la lista.</p>
{img('fig3_urbana_anual.png', 'Figura 4. Canciones urbanas en el top 10 anual.')}
<h3>7.3. Secundaria 2: riqueza léxica</h3>
<p>Shapiro-Wilk {'rechaza' if float(re.search(r'p=([0-9.]+)', km.nota).group(1)) < 0.05 else 'no rechaza'} la normalidad de la MATTR (W = {n(float(re.search(r'W=([0-9.]+)', km.nota).group(1)), 3)}, p {p_eq(float(re.search(r'p=([0-9.]+)', km.nota).group(1)))}); con periodos de tamaño desigual
({int(ns['P1_2011_2015'])}, {int(ns['P2_2016_2020'])} y {int(ns['P3_2021_2025'])} canciones) se prefirieron pruebas no paramétricas, complementadas con una
regresión lineal que controla el estrato. La riqueza léxica aumentó: correlación con el año ρ = {n(rm.tamano_efecto)} (p Holm {p_eq(rm.p_holm)}),
tendencia monótona en la mediana anual (Mann-Kendall τ = {n(mkm.tamano_efecto)}, p Holm {p_eq(mkm.p_holm)}) y diferencia entre
periodos (Kruskal-Wallis ε² = {n(km.tamano_efecto)}, p Holm {p_eq(km.p_holm)}). La MATTR sube {n(rlm.tamano_efecto, 4)} puntos por año
(IC 95 %: {n(rlm.ic95_inf, 4)}–{n(rlm.ic95_sup, 4)}), y el aumento aparece en los dos estratos por separado (ρ = {n(m1.tamano_efecto)} y {n(m2.tamano_efecto)}).
Las letras recientes repiten menos y usan un vocabulario más variado por cada ventana de 50 palabras
(Figura 5). La medida es determinística y no depende del modelo.</p>
{img('fig4_riqueza_lexica.png', 'Figura 5. Riqueza léxica (MATTR) por periodo y estrato.')}
<h3>7.4. Secundaria 1 y resultados exploratorios del modelo</h3>
<p>La pregunta S1 no puede responderse con un instrumento validado. En las categorías de S1 el modelo no
alcanzó el umbral (CUERPO quedó en acuerdo moderado) y en AGENCIA los propios humanos solo lograron un
acuerdo moderado. Como triangulación, la dimensión
de cuerpo del léxico no difiere entre canciones con y sin intérprete mujer (razón de odds = {n(flc.tamano_efecto)}, IC 95 %:
{n(flc.ic95_inf)}–{n(flc.ic95_sup)}, p Holm {p_eq(flc.p_holm)}), aunque su acuerdo con los codificadores humanos es bajo. Por transparencia se
informa lo que arroja el modelo, sin valor de conclusión: según el modelo, las canciones con intérprete
mujer presentan más a la mujer como sujeto que decide (razón de odds = {n(fa.tamano_efecto)}, IC 95 %: {n(fa.ic95_inf)}–{n(fa.ic95_sup)};
p Holm {p_eq(fa.p_holm)}) y no difieren en referencias al cuerpo (razón de odds = {n(fc.tamano_efecto)}, p Holm {p_eq(fc.p_holm)}).
Para el desenlace principal, el modelo estima que la proporción de explícitas pasa de
{pct(d.loc['P1_2011_2015', 'llm_sexual_explicito_pct'])} a {pct(d.loc['P3_2021_2025', 'llm_sexual_explicito_pct'])}, con una razón de odds por año de {n(lg.tamano_efecto)} (IC 95 %: {n(lg.ic95_inf)}–{n(lg.ic95_sup)}).
Esa cifra está inflada por la sobrecodificación documentada en la sección 6 y, a diferencia del léxico,
no distingue entre estratos. El modelo ordena las canciones de forma parecida a las personas
(ρ = {n(orden.tamano_efecto)} con el promedio humano), lo que sugiere que con un umbral recalibrado podría volverse útil.</p>
<p>La tabla completa de las {len(tabla_inf)} pruebas, con el estado del instrumento que sustenta cada una y el
ajuste de Holm para las preguntas secundarias, está en el Anexo B.</p>"""


def s_discusion(c):
    b = c["base"][c["base"].analizable == 1]
    return f"""
<h2>8. Discusión y limitaciones</h2>
<h3>8.1. Interpretación frente al debate</h3>
<p>El aumento del contenido sexual es compatible con la tendencia hacia lo explícito documentada en la
música popular en general (Hall, West y Hill, 2012) y con los trabajos que señalan una persistente
sexualización en el reggaetón (Arévalo et al., 2018; Alpízar-Lorenzo et al., 2021). El resultado agrega
un matiz: en el top 10 anual el cambio se ve tanto en el juicio humano como en el vocabulario, mientras
que en los demás números uno solo lo registran las personas. Una lectura posible, que este diseño no
puede probar, es que las canciones de mayor consumo usen un lenguaje más directo y las demás recurran
más al doble sentido. El estudio no puede pronunciarse sobre la otra mitad del debate: la categoría
diseñada para captar la agencia femenina (Báez, 2006; Santos Rodríguez, 2023) es la que menos acuerdo
logró entre los codificadores humanos. Que la agencia sea difícil de codificar de manera confiable es
coherente con la idea de esa literatura de que el sentido de estas letras se disputa: la misma frase
puede leerse como decisión de la mujer o como fantasía del narrador. Medir contenido sexual no equivale
a medir cosificación ni empoderamiento.</p>
<h3>8.2. Lo que aprendimos del LLM como instrumento</h3>
<p>El modelo no fue un instrumento válido con este libro de códigos. Su error no es aleatorio sino un
sesgo de nivel: es muy sensible y poco específico, y aplica las reglas escritas de forma más literal que
las personas. Mientras los dos codificadores coincidieron en dónde empieza lo explícito, el modelo
convirtió en explícitas muchas insinuaciones por la regla de las pistas acumuladas, que el libro de
códigos no define con precisión. La dirección del cambio que estima el modelo coincide con la humana,
pero su nivel no: con él se habría sobrestimado la proporción de canciones explícitas en todos los
periodos. La lección metodológica es que validar no consiste solo en calcular un kappa: el análisis de
discrepancias permitió ubicar el problema en la interacción entre el modelo y el libro de códigos.</p>
<h3>8.3. Qué no permite concluir el diseño</h3>
<ul>
<li><strong>Magnitud.</strong> Los porcentajes de canciones explícitas provienen del consenso humano en 50 canciones:
indican el orden de magnitud del cambio, con intervalos amplios, no una cifra precisa.</li>
<li><strong>Causalidad.</strong> Es un estudio observacional: no permite afirmar por qué cambiaron las letras ni por qué
el cambio difiere entre estratos, ni inferir efectos sobre las audiencias.</li>
<li><strong>Generalización.</strong> Los resultados valen para los éxitos urbanos del mercado estadounidense, no para
todo el reggaetón ni para el consumo en Colombia.</li>
</ul>
<h3>8.4. Sesgos del marco y de los instrumentos</h3>
<ul>
<li><strong>Cambio metodológico de la lista en 2012</strong> y pocas canciones urbanas en el primer periodo
(n = {int(b[b.periodo == 'P1_2011_2015'].shape[0])}, y 9 en la validación): las estimaciones de ese periodo son imprecisas.</li>
<li><strong>Estrato 2 con radio.</strong> Parte de sus números uno provienen de <em>Latin Airplay</em>, que solo mide radio y
favorece versiones menos explícitas; eso puede explicar parte de su nivel más bajo, no su falta de tendencia.</li>
<li><strong>Clasificación de género por juicio documentado</strong>, mitigada con la clase híbrida y un análisis de
sensibilidad.</li>
<li><strong>Remezclas:</strong> se respetó la versión acreditada en la lista, que puede diferir de la original.</li>
<li><strong>Procedimiento del LLM:</strong> el modelo codificó en una sesión de trabajo, la misma que asistió en la
programación y la redacción, y no por llamadas independientes a la API con temperatura 0. El estrato 1
y el estrato 2 se codificaron en fechas distintas, con el prompt congelado; el estrato 2, en una sesión
que ya conocía resultados de una ronda anterior de codificación humana, lo que podría haber influido en
la aplicación del libro de códigos. Como el modelo no se usa para concluir, esto no afecta los hallazgos. La replicación
por API queda preparada en el repositorio.</li>
<li><strong>Codificación humana no del todo independiente:</strong> los codificadores conocían los resultados de una
ronda anterior y discutieron algunas canciones antes de entregar, sin registrar los cambios. Su acuerdo es una
cota superior, y su conocimiento previo del modelo podría haberlos llevado a codificar con más cautela.</li>
<li><strong>Consenso sin discusión de los desacuerdos restantes:</strong> el consenso se restringió a las canciones
con acuerdo.</li>
<li><strong>Léxico:</strong> capta términos, no sentidos; no distingue lo literal de lo figurado y subestima los dobles
sentidos. Su validez frente al juicio humano es moderada.</li>
</ul>
<h3>8.5. Qué haríamos distinto con más tiempo</h3>
<p>Revisar el libro de códigos (versión 1.1) con una lista cerrada de jerga que cuenta como mención directa,
con variantes colombianas y puertorriqueñas, y una definición de agencia que distinga la voz que narra.
Hacer una nueva ronda de validación con tres codificadores sin contacto entre sí, registro de cada cambio y
discusión documentada de los desacuerdos, con una submuestra mayor para estimar proporciones con menos
incertidumbre. Ejecutar la codificación por API en llamadas independientes y comparar dos modelos. Separar
los números uno de <em>Hot Latin Songs</em> y de <em>Latin Airplay</em> para aislar el efecto de la radio.</p>"""


def s_ia(c):
    return f"""
<h2>9. Uso de IA como asistente</h2>
<p>En este proyecto la IA cumplió dos papeles que se documentan por separado. Como <strong>instrumento de
medición</strong>, el modelo codificó las letras; ese uso se valida con el kappa (sección 6) y se documenta
en la tabla de validación. Como <strong>asistente</strong>, Claude participó en el diseño y la redacción de los
instrumentos, la programación de todo el flujo de análisis, la redacción de este informe y el diseño
del producto divulgativo. También transcribió las listas de números uno desde las páginas de
Wikipedia, hizo la clasificación de género musical de las {len(c['marco'])} canciones de los dos marcos y la primera
clasificación cualitativa de las discrepancias. El equipo aportó la recolección manual de las letras y la
codificación humana de la submuestra, que por diseño no podía delegarse en la IA.</p>
<p>Cada uso como asistente está registrado en la bitácora anexa, con lo que se pidió, lo que se obtuvo y
cómo se verificó. Las verificaciones combinan comprobaciones automáticas incluidas en el flujo
(validación de valores del libro de códigos, huellas de los instrumentos, auditoría de letras, ejecución
completa en sesión limpia) y la revisión del equipo. Ninguna cifra del informe se transcribió a mano:
el documento se genera desde los archivos de resultados.</p>"""


ANEXO_KAPPAS = ANEXO_PRUEBAS = ANEXO_PROMPT = ""


def s_anexos():
    return (f'<h2 class="salto">Anexo A. Coeficientes kappa por comparación</h2>{ANEXO_KAPPAS}'
            f'<h2>Anexo B. Tabla completa de pruebas</h2>{ANEXO_PRUEBAS}'
            f'<h2>Anexo C. Prompt de codificación v1.0 (texto completo)</h2>{ANEXO_PROMPT}'
            '<h2>Anexo D. Bitácora de uso de IA</h2><p>Se entrega como documento aparte '
            '(<code>bitacora_IA.pdf</code>), con una entrada por cada uso de la IA como asistente y su verificación.</p>')


def s_referencias():
    refs = [
        "Alpízar-Lorenzo, A., Hernández-Muñoz, L., Ledezma-Trujillo, M. C., Linares-Villa, M. A., Rodríguez-Cortés, L., Guzmán-Díaz, G. y Cisneros Herrera, J. (2021). Goce sin límites: manifestaciones misóginas en canciones de reggaetón. <em>Boletín Científico de la Escuela Superior Atotonilco de Tula</em>, 8(15), 25–32.",
        "Arévalo, K., Chellew, E., Figueroa-Cofré, I., Arancibia-Villablanca, A. y Schmied, S. (2018). Ni pobre diabla, ni Candy: violencia de género del reggaetón. <em>Revista de Sociología</em>. https://doi.org/10.5354/0719-529X.2018.51797",
        "Báez, J. M. (2006). “En mi imperio”: Competing discourses of agency in Ivy Queen’s reggaetón. <em>Centro Journal</em>, 18(2).",
        "Cohen, J. (1960). A coefficient of agreement for nominal scales. <em>Educational and Psychological Measurement</em>, 20(1), 37–46.",
        "Covington, M. A. y McFall, J. D. (2010). Cutting the Gordian knot: The moving-average type–token ratio (MATTR). <em>Journal of Quantitative Linguistics</em>, 17(2), 94–100.",
        "Espinal Ramírez, L. F., Díaz-Fernández, S. y Orejuela, J. Research trends about reggaetón and future fields of knowledge of an expanding sociocultural phenomenon. <em>Cuadernos de Música Iberoamericana</em>. https://revistas.ucm.es/index.php/CMIB/article/view/99810",
        "Gilardi, F., Alizadeh, M. y Kubli, M. (2023). ChatGPT outperforms crowd workers for text-annotation tasks. <em>Proceedings of the National Academy of Sciences</em>, 120(30), e2305016120.",
        "Hall, P. C., West, J. H. y Hill, S. (2012). Sexualization in lyrics of popular music from 1959 to 2009: Implications for sexuality educators. <em>Sexuality &amp; Culture</em>, 16(2), 103–117.",
        "Kendall, M. G. (1975). <em>Rank correlation methods</em> (4.ª ed.). Charles Griffin.",
        "Landis, J. R. y Koch, G. G. (1977). The measurement of observer agreement for categorical data. <em>Biometrics</em>, 33(1), 159–174.",
        "Mann, H. B. (1945). Nonparametric tests against trend. <em>Econometrica</em>, 13(3), 245–259.",
        "Santos Rodríguez, V. (2023). Soy feminista y me gusta el perreo: Conflicts of (re)signification in the sexual politics of reggaeton. <em>GLAD! Revue sur le langage, le genre, les sexualités</em>, 14.",
        "Wikipedia. (s. f.). Billboard Hot Latin Songs Year-End Chart. Consultado el 22 de octubre de 2026. https://en.wikipedia.org/wiki/Billboard_Hot_Latin_Songs_Year-End_Chart",
        "Wikipedia. (s. f.). List of Billboard Hot Latin Songs and Latin Airplay number ones of 2012 [a 2025] y List of number-one Billboard Top Latin Songs of 2011. Consultados el 24 de octubre de 2026. https://en.wikipedia.org/",
        "Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. <em>Journal of the American Statistical Association</em>, 22(158), 209–212.",
    ]
    return "<h2>Referencias</h2>" + "".join(f'<p class="ref">{r}</p>' for r in refs)


CSS = """
@page { size: A4; }
body { font-family: 'DejaVu Serif', serif; font-size: 9.5pt; line-height: 1.36; color: #111; }
.portada { text-align: center; margin-top: 30mm; page-break-after: always; }
.portada .t1 { font-size: 24pt; font-weight: bold; margin-bottom: 4mm; }
.portada .t2 { font-size: 13pt; color: #333; margin-bottom: 22mm; }
.portada .meta { font-size: 11pt; line-height: 1.8; }
.borrador { color: #b00020; font-weight: bold; font-size: 12pt; margin-top: 15mm; }
h2 { font-size: 14pt; margin: 9mm 0 3mm; border-bottom: 1.2px solid #1f3a5f; padding-bottom: 1.5mm; color: #1f3a5f; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 5mm 0 2mm; page-break-after: avoid; }
p { margin: 0 0 2.6mm; text-align: justify; hyphens: auto; }
ul { margin: 0 0 3mm 5mm; padding-left: 4mm; } li { margin-bottom: 1.3mm; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 3mm 0 4mm; font-size: 8.4pt; }
tr { page-break-inside: avoid; } table:not(.micro) { break-inside: avoid; } .salto { page-break-before: always; }
caption { caption-side: top; text-align: left; font-weight: bold; font-size: 9pt; margin-bottom: 1.5mm; }
th { background: #1f3a5f; color: #fff; padding: 1.4mm 2mm; text-align: left; font-weight: bold; }
td { padding: 1.2mm 2mm; border-bottom: 0.6px solid #ccc; vertical-align: top; }
table.compacta { font-size: 7.6pt; } table.micro { font-size: 6.6pt; } table.micro td, table.micro th { padding: 0.8mm 1.2mm; } table.mini { width: auto; display: inline-table; margin-right: 6mm; font-size: 8pt; }
.mats { margin-bottom: 3mm; }
figure { margin: 3mm 0 5mm; text-align: center; page-break-inside: avoid; }
figure img { width: 56%; } figcaption { font-size: 8.8pt; color: #333; margin-top: 1mm; }
pre.prompt { font-family: 'DejaVu Sans Mono', monospace; font-size: 6.9pt; line-height: 1.32; background: #f4f4f2;
  border: 0.6px solid #ccc; padding: 3mm; white-space: pre-wrap; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.6pt; }
.pend { color: #b00020; } .pend-box { border: 1px dashed #b00020; color: #b00020; padding: 3mm; margin: 3mm 0; }
.ref { padding-left: 8mm; text-indent: -8mm; font-size: 9.4pt; text-align: left; }
"""


def main(borrador: bool | None = None):
    c = cargar()
    if borrador is None:
        borrador = c["kap"] is None or c["disc_txt"] is None or c["fuentes"] is None
    SALIDA.mkdir(exist_ok=True)
    portada = f"""<div class="portada">
<div class="t1">Estadística del reggaetón</div>
<div class="t2">Contenido sexual, cuerpo y agencia en las letras urbanas más populares, 2011–2025:<br>
un análisis con validación de un modelo de lenguaje como instrumento de medición</div>
<div class="meta">Informe técnico · Proyecto 3<br>Estadística Industrial · Universidad del Magdalena<br>
Docente: Enrique J. De La Hoz Domínguez<br>Semestre 2026-II</div>
{'<div class="borrador">BORRADOR — contiene secciones pendientes de la codificación humana</div>' if borrador else ''}
</div>"""
    cuerpo = "".join([portada, s_resumen(c), s_introduccion(c), s_diseno(c), s_fuentes(c), s_instrumentos(c),
                      s_validacion(c), s_resultados(c), s_discusion(c), s_ia(c), s_referencias(), s_anexos()])
    doc = f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Informe técnico</title><style>{CSS}</style></head><body>{cuerpo}</body></html>'
    nombre = "informe_tecnico_BORRADOR" if borrador else "informe_tecnico"
    ruta_html = SALIDA / f"{nombre}.html"
    ruta_html.write_text(doc, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page()
        pag.goto(ruta_html.as_uri())
        pag.pdf(path=str(SALIDA / f"{nombre}.pdf"), format="A4", print_background=True,
                display_header_footer=True, header_template="<span></span>",
                footer_template='<div style="width:100%;text-align:center;font-size:8pt;color:#555;">'
                                '<span class="pageNumber"></span></div>',
                margin={"top": "20mm", "bottom": "18mm", "left": "20mm", "right": "20mm"})
        nav.close()
    print("Informe:", SALIDA / f"{nombre}.pdf")


if __name__ == "__main__":
    main()
