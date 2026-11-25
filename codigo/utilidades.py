"""Funciones de normalización compartidas por todos los scripts."""
import re
import unicodedata


def sin_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def limpiar_titulo(titulo: str) -> str:
    """Quita comillas, el símbolo ‡ de Wikipedia y espacios sobrantes."""
    t = titulo.replace("‡", "")
    t = re.sub(r"[\"“”'‘’]", "", t)
    return re.sub(r"\s+", " ", t).strip()


SEPARADORES = r"\s+featuring\s+|\s+with\s+|\s+and\s+|\s*&\s*|,|\s+x\s+"


def separar_artistas(artistas: str) -> list[str]:
    """Lista de intérpretes acreditados, en orden."""
    return [p.strip() for p in re.split(SEPARADORES, artistas, flags=re.I) if p.strip()]


def artista_principal(artistas: str) -> str:
    """Primer artista acreditado (antes de featuring, and, &, x o coma)."""
    return separar_artistas(artistas)[0]


def clave_cancion(titulo: str, artistas: str) -> str:
    """Clave estable para deduplicar: título + artista principal, sin tildes ni mayúsculas."""
    t = sin_tildes(limpiar_titulo(titulo)).lower()
    t = re.sub(r"\s*\(.*?\)", "", t)          # quita paréntesis: 'Ritmo (Bad Boys for Life)'
    t = re.sub(r"[^a-z0-9 ]", "", t).strip()
    a = sin_tildes(artista_principal(artistas)).lower()
    a = re.sub(r"^the\s+", "", a)              # 'The Black Eyed Peas' = 'Black Eyed Peas'
    a = re.sub(r"[^a-z0-9 ]", "", a).strip()
    return f"{t}|{a}"


def titulo_normalizado(titulo: str) -> str:
    t = sin_tildes(limpiar_titulo(titulo)).lower()
    t = re.sub(r"\s*\(.*?\)", "", t)
    return re.sub(r"[^a-z0-9 ]", "", t).strip()


def misma_cancion(t1: str, a1: str, t2: str, a2: str) -> bool:
    """Mismo título normalizado y al menos un intérprete en común (cubre créditos en otro orden)."""
    if titulo_normalizado(t1) != titulo_normalizado(t2):
        return False
    norm = lambda a: {re.sub(r"^the\s+", "", sin_tildes(x).lower()) for x in separar_artistas(a)}
    return bool(norm(a1) & norm(a2))


def asignacion_proporcional(tamanos, n: int):
    """Asignación proporcional por el método del mayor residuo (enteros que suman n)."""
    import numpy as np
    exacto = tamanos / tamanos.sum() * n
    base = np.floor(exacto).astype(int)
    faltan = int(n - base.sum())
    orden = (exacto - base).sort_values(ascending=False).index[:faltan]
    base[orden] += 1
    return base
