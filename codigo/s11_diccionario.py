"""
Paso 11 — Diccionario de variables de las dos bases de datos en CSV.

Fuente: documentacion/diccionario_variables.csv (redactado a mano). El paso verifica que el
diccionario describa exactamente las columnas de datos/base_analitica.csv y de
instrumentos/lexico_v1.0.csv, y genera documentacion/diccionario_variables.xlsx y .pdf.
"""
import html
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

DOC = cfg.RAIZ / "documentacion"
BASES = {"base_analitica": cfg.DIR_DATOS / "base_analitica.csv",
         "lexico": cfg.RAIZ / "instrumentos" / "lexico_v1.0.csv"}
TITULOS = {"base_analitica": "base_analitica.csv — una fila por canción del corpus",
           "lexico": "lexico_v1.0.csv — una fila por patrón del léxico"}


def main():
    dic = pd.read_csv(DOC / "diccionario_variables.csv", sep="|", dtype=str).fillna("")
    for base, ruta in BASES.items():
        cols = list(pd.read_csv(ruta, nrows=0).columns)
        doc = dic.loc[dic.base == base, "variable"].tolist()
        assert doc == cols, f"Diccionario desactualizado para {base}: faltan {set(cols) - set(doc)}, sobran {set(doc) - set(cols)}"

    wb = Workbook()
    wb.remove(wb.active)
    for base in BASES:
        ws = wb.create_sheet(base)
        d = dic[dic.base == base].drop(columns="base")
        ws.append(["Variable", "Significado", "Tipo", "Valores", "Origen"])
        for fila in d.itertuples(index=False):
            ws.append(list(fila))
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
        for col, ancho in zip("ABCDE", [26, 70, 14, 45, 32]):
            ws.column_dimensions[col].width = ancho
        for fila in ws.iter_rows(min_row=2):
            for c in fila:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2"
    wb.save(DOC / "diccionario_variables.xlsx")

    bloques = []
    for base in BASES:
        d = dic[dic.base == base]
        filas = "".join(f"<tr><td><code>{html.escape(r.variable)}</code></td><td>{html.escape(r.significado)}</td>"
                        f"<td>{html.escape(r.tipo)}</td><td>{html.escape(r.valores)}</td><td>{html.escape(r.origen)}</td></tr>"
                        for r in d.itertuples())
        bloques.append(f"<h2>{TITULOS[base]} ({len(d)} variables)</h2><table><thead><tr><th>Variable</th><th>Significado</th>"
                       f"<th>Tipo</th><th>Valores</th><th>Origen</th></tr></thead><tbody>{filas}</tbody></table>")
    css = ("@page{size:A4 landscape;margin:12mm}body{font-family:'DejaVu Sans',sans-serif;font-size:7.6pt;line-height:1.3}"
           "h1{font-size:14pt;color:#1f3a5f;margin:0 0 1mm}h2{font-size:10.5pt;color:#1f3a5f;margin:5mm 0 2mm}"
           "p{font-size:8.4pt;margin:0 0 2mm}table{border-collapse:collapse;width:100%}"
           "th{background:#1f3a5f;color:#fff;text-align:left;padding:1.2mm 1.5mm}td{border-bottom:.5px solid #bbb;"
           "padding:1mm 1.5mm;vertical-align:top}td:first-child{width:38mm}td:nth-child(3){width:20mm}"
           "tr{page-break-inside:avoid}code{font-size:7.4pt}")
    doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Diccionario de variables</title>'
           f'<style>{css}</style></head><body><h1>Diccionario de variables</h1>'
           '<p><em>Estadística del reggaetón · Estadística Industrial · Universidad del Magdalena · 2026-II.</em> '
           'Describe cada columna de las dos bases de datos en CSV del proyecto. Las letras de las canciones no '
           'forman parte de ninguna base. Las variables con prefijo <code>llm_</code> provienen de un instrumento '
           'que no superó la validación y solo se usan de forma exploratoria.</p>' + "".join(bloques) + "</body></html>")
    ruta_html = DOC / "diccionario_variables.html"
    ruta_html.write_text(doc, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page()
        pag.goto(ruta_html.as_uri())
        pag.pdf(path=str(DOC / "diccionario_variables.pdf"), prefer_css_page_size=True, print_background=True)
        nav.close()
    print(f"Diccionario: {len(dic)} variables documentadas →", DOC / "diccionario_variables.pdf")


if __name__ == "__main__":
    main()
