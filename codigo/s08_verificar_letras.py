"""
Paso 8 — Auditoría de la regla de manejo de letras.

Busca en todos los archivos de datos/, resultados/, instrumentos/ y entregables/ cualquier
secuencia de 8 o más palabras consecutivas que aparezca en alguna letra. Si encuentra una,
falla: un entregable no puede contener texto de letras más allá de citas breves.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
from s02_variables_texto import normalizar

N = 8
CARPETAS = ["datos", "resultados", "registros", "instrumentos", "entregables", "datos_crudos", "documentacion"]
EXT_TEXTO = {".csv", ".md", ".txt", ".json", ".html", ".tex"}
# Los PDF se auditan a través de su HTML fuente, que contiene exactamente el mismo texto.


def ngramas(texto: str) -> set[tuple]:
    t = normalizar(texto).split()
    return {tuple(t[i:i + N]) for i in range(len(t) - N + 1)}


def texto_de(ruta: Path) -> str:
    if ruta.suffix in EXT_TEXTO:
        return ruta.read_text(encoding="utf-8", errors="ignore")
    if ruta.suffix in {".xlsx", ".docx", ".pptx"}:   # documentos Office: XML dentro de un zip
        with zipfile.ZipFile(ruta) as z:
            return " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
    return ""


def main():
    huellas = set()
    for f in sorted(cfg.DIR_LETRAS.glob("C*.txt")):
        huellas |= ngramas(f.read_text(encoding="utf-8"))
    hallazgos = []
    for carpeta in CARPETAS:
        for ruta in (cfg.RAIZ / carpeta).rglob("*"):
            if ruta.is_file():
                comunes = ngramas(texto_de(ruta)) & huellas
                if comunes:
                    hallazgos.append((ruta.relative_to(cfg.RAIZ), len(comunes)))
    if hallazgos:
        for r, n in hallazgos:
            print(f"FALLA: {r} contiene {n} secuencias de {N} palabras tomadas de letras")
        raise SystemExit(1)
    print(f"Auditoría superada: ningún archivo contiene {N} o más palabras seguidas de una letra.")


if __name__ == "__main__":
    main()
