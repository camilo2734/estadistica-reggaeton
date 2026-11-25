"""
Paso 2 — Limpieza de letras y variables de texto derivadas.

Lee cada letras/C###.txt EN MEMORIA y exporta solo estadísticos. Ninguna línea de letra
se escribe en disco.

Salidas : datos/variables_texto.csv     una fila por canción (conteos, riqueza léxica, léxico, idioma)
          datos/registro_limpieza.csv   cuántas líneas se eliminaron y por qué regla (sin texto)

Decisiones de procesamiento (informe, sección 5):
  - Se eliminan: rótulos de sección (intro, coro, verse...), corchetes, encabezados de página
    copiados por error, títulos repetidos al inicio y líneas de lista de reproducción.
  - Los coros de fondo entre paréntesis se separan del texto principal: no cuentan en las
    medidas de longitud ni de riqueza, pero sí en el léxico (son parte de lo que se canta).
  - Las repeticiones de coros se conservan: se mide la canción tal como se canta.
  - Normalización: minúsculas, sin tildes, sin apóstrofos de elisión (pa', e', to'...).
  - No se eliminan stopwords: los pronombres son informativos en este corpus.
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
import utilidades as u

ROTULOS = re.compile(
    r"^\s*\[.*\]\s*$|"
    r"^\s*(intro|outro|verse|verso|chorus|coro|estribillo|pre-?estribillo|pre-?chorus|post-?chorus|"
    r"hook|bridge|puente|interludio|interlude|refr[aá]n|break|drop|parte \d+|vers[ií]culo|gancho)\b[^a-záéíóúñ]*"
    r"(\d+)?\s*(:.*)?$", re.I)
BASURA = re.compile(
    r"^\s*letra de (la canci[oó]n|.* de .*)\s*$|cat[aá]logo de canciones|p[aá]gina \d+\s*$|"
    r"^\s*observaci[oó]?n?e?s?\s*$|•\s*\d{4}|^\s*lyrics of |show performers|mostrar int[eé]rpretes|"
    r"^\s*otro\s*$|musixmatch|^\s*¿eres artista\?", re.I)

# Palabras funcionales del inglés. Se excluyen a propósito 'baby', 'yeah', 'oh', 'girl' y 'no':
# son muletillas comunes en letras en español y sesgarían la medida hacia el inglés.
STOP_EN = set("the you i me my your and to it is that this in on be what im dont can like "
              "got want with all for so just know we she he her him they get up "
              "when if let make way go do not are was down feel its thats ill youre".split())
STOP_ES = set("el la los las de que y a en un una es por con para no te me mi tu yo se lo le "
              "como más pero si ya está todo eso esta este ese esa nos quiero bien hay sé".split())


def limpiar(texto: str, titulo: str) -> tuple[str, str, dict]:
    """Devuelve (texto_principal, texto_coros_fondo, registro)."""
    reg = {"lineas_originales": 0, "rotulos": 0, "basura": 0, "titulo_encabezado": 0}
    t_titulo = u.sin_tildes(u.limpiar_titulo(titulo)).lower()
    t_titulo = re.sub(r"\s*\(.*?\)", "", t_titulo).strip()
    utiles = []
    for i, linea in enumerate(texto.splitlines()):
        if not linea.strip():
            continue
        reg["lineas_originales"] += 1
        if ROTULOS.match(linea):
            reg["rotulos"] += 1
            continue
        if BASURA.search(linea):
            reg["basura"] += 1
            continue
        normal = re.sub(r"\s*\(.*?\)", "", u.sin_tildes(linea).lower()).strip(" .…")
        if len(utiles) < 3 and normal == t_titulo and i < 6:
            reg["titulo_encabezado"] += 1
            continue
        utiles.append(linea)
    cuerpo = "\n".join(utiles)
    coros = " ".join(re.findall(r"\(([^)]*)\)", cuerpo))
    principal = re.sub(r"\([^)]*\)", " ", cuerpo)
    return principal, coros, reg


def normalizar(texto: str) -> str:
    t = u.sin_tildes(texto).lower()
    t = re.sub(r"['’`´]", "", t)               # elisiones: pa' -> pa, e' -> e
    t = re.sub(r"[^a-zñ0-9]+", " ", t.replace("ñ", "n"))
    return re.sub(r"\s+", " ", t).strip()


def tokens(texto_normal: str) -> list[str]:
    return [w for w in texto_normal.split() if not w.isdigit()]


def mattr(toks: list[str], ventana: int = 50) -> float:
    """Moving-Average Type-Token Ratio (Covington y McFall, 2010): no depende de la longitud."""
    if len(toks) < ventana:
        return len(set(toks)) / len(toks) if toks else float("nan")
    valores = [len(set(toks[i:i + ventana])) / ventana for i in range(len(toks) - ventana + 1)]
    return sum(valores) / len(valores)


def proporcion_ingles(toks: list[str]) -> float:
    en = sum(w in STOP_EN for w in toks)
    es = sum(w in STOP_ES for w in toks)
    return en / (en + es) if en + es else 0.0


def main() -> pd.DataFrame:
    corpus = pd.read_csv(cfg.DIR_DATOS / "corpus.csv")
    lexico = pd.read_csv(cfg.RAIZ / "instrumentos" / "lexico_v1.0.csv")
    lexico["regex"] = lexico.patron.map(re.compile)
    dimensiones = list(dict.fromkeys(lexico.dimension))

    faltan = [c for c in corpus.codigo if not (cfg.DIR_LETRAS / f"{c}.txt").exists()]
    if faltan:
        raise FileNotFoundError(f"Faltan letras: {faltan}")

    filas, registros = [], []
    for _, cancion in corpus.iterrows():
        crudo = (cfg.DIR_LETRAS / f"{cancion.codigo}.txt").read_text(encoding="utf-8")
        principal, coros, reg = limpiar(crudo, cancion.titulo)
        n_principal = normalizar(principal)
        n_completo = normalizar(principal + " " + coros)
        toks = tokens(n_principal)
        fila = {
            "codigo": cancion.codigo,
            "n_palabras": len(toks),
            "n_tipos": len(set(toks)),
            "ttr": len(set(toks)) / len(toks),
            "mattr50": mattr(toks),
            "n_palabras_coros_fondo": len(tokens(normalizar(coros))),
            "prop_ingles": proporcion_ingles(toks),
        }
        palabras_total = len(tokens(n_completo))
        for dim in dimensiones:
            n = sum(len(rx.findall(n_completo)) for rx in lexico.loc[lexico.dimension == dim, "regex"])
            fila[f"lex_{dim}_n"] = n
            fila[f"lex_{dim}_x100"] = 100 * n / palabras_total
            fila[f"lex_{dim}_presente"] = int(n > 0)
        filas.append(fila)
        registros.append({"codigo": cancion.codigo, **reg})

    df = pd.DataFrame(filas)
    # Regla de idioma: se excluye del análisis la canción con mayoría de palabras funcionales en inglés
    df["excluida_idioma"] = (df.prop_ingles > 0.5).astype(int)
    df.to_csv(cfg.DIR_DATOS / "variables_texto.csv", index=False)
    pd.DataFrame(registros).to_csv(cfg.DIR_DATOS / "registro_limpieza.csv", index=False)
    print(df.describe().T[["mean", "min", "max"]].round(2).to_string())
    print("Excluidas por idioma:", df.loc[df.excluida_idioma == 1, "codigo"].tolist())
    return df


if __name__ == "__main__":
    main()
