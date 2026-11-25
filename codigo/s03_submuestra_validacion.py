"""
Paso 3 — Sorteo de la submuestra de validación y plantillas de codificación humana.

Tamaño: máx(50, 20 % de las canciones analizables del corpus)  (rúbrica, sección 5.1).
Marco del sorteo: el corpus completo (estratos 1 y 2), para que la validación represente a
todas las canciones sobre las que se concluye.
Diseño: estratificado por celda estrato × periodo (6 celdas), asignación proporcional al número
de canciones analizables de cada celda (método del mayor residuo).
Procedimiento: con la semilla fija se genera un orden aleatorio dentro de cada celda; se toman
las primeras n_h canciones elegibles (no excluidas por idioma). Así, si la elegibilidad de una
canción cambia, el reemplazo es la siguiente de su misma celda y nada más se mueve.

Salidas : datos/orden_aleatorio_validacion.csv
          datos/submuestra_validacion.csv
          resultados/plantilla_codificador_A.xlsx y _B.xlsx (cada una en orden distinto)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

CODIFICADORES = ["A", "B"]


def asignacion_proporcional(tamanos: pd.Series, n: int) -> pd.Series:
    exacto = tamanos / tamanos.sum() * n
    base = np.floor(exacto).astype(int)
    faltan = n - base.sum()
    orden = (exacto - base).sort_values(ascending=False).index[:faltan]
    base[orden] += 1
    return base


def plantilla(sub: pd.DataFrame, letra: str, semilla: int) -> None:
    datos = sub.sample(frac=1, random_state=semilla)[["codigo", "titulo", "artistas"]]
    wb = Workbook()
    ins = wb.active
    ins.title = "Instrucciones"
    texto = [
        f"PLANTILLA DEL CODIFICADOR {letra} — Validación del instrumento (libro de códigos v1.0)",
        "",
        "1. Trabaja SOLO. No compartas tus códigos ni preguntes a los demás hasta entregar esta plantilla.",
        "2. No mires la codificación de la IA (no se te ha entregado y no debes pedirla).",
        "3. Para cada canción, lee la letra COMPLETA en tu archivo C###.txt y aplica el libro de códigos v1.0.",
        "4. sexual: 0 = ninguno · 1 = insinuado · 2 = explícito",
        "5. cuerpo: 1 = menciona o evalúa partes del cuerpo o la figura de una mujer · 0 = no",
        "6. agencia: 1 = la mujer aparece como sujeto que decide por sí misma · 0 = no",
        "7. duda: 1 si dudaste de verdad en alguna categoría (no cambia el código).",
        "8. comentario: opcional, máximo una línea. No copies versos de la letra.",
        "9. El orden de las canciones es aleatorio y distinto para cada codificador: no lo cambies.",
        "",
        "10. Codifica solo con la letra y el libro de códigos. No intentes coincidir con la IA ni corregirla.",
        "11. Si una canción la codificaste en la ronda anterior, no mires tus códigos viejos: vuelve a leerla.",
        "",
        "Lee el libro de códigos completo antes de empezar. Tiempo estimado: 2 horas.",
    ]
    for i, t in enumerate(texto, 1):
        ins.cell(row=i, column=1, value=t).font = Font(bold=(i == 1))
    ins.column_dimensions["A"].width = 110

    ws = wb.create_sheet("Codificacion")
    cab = ["codigo", "titulo", "artistas", "sexual", "cuerpo", "agencia", "duda", "comentario"]
    ws.append(cab)
    for fila in datos.itertuples(index=False):
        ws.append(list(fila) + [None] * 5)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3A5F")
        c.alignment = Alignment(horizontal="center")
    for col, ancho in zip("ABCDEFGH", [8, 28, 45, 9, 9, 9, 7, 50]):
        ws.column_dimensions[col].width = ancho
    n = len(datos) + 1
    for rango, opciones in [(f"D2:D{n}", '"0,1,2"'), (f"E2:G{n}", '"0,1"')]:
        dv = DataValidation(type="list", formula1=opciones, allow_blank=True)
        dv.error, dv.showErrorMessage = "Valor no permitido por el libro de códigos", True
        ws.add_data_validation(dv)
        dv.add(rango)
    amarillo = PatternFill("solid", fgColor="FFF2CC")
    for fila in ws.iter_rows(min_row=2, min_col=4, max_col=7):
        for c in fila:
            c.fill = amarillo
            c.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "D2"
    wb.save(cfg.DIR_RESULTADOS / f"plantilla_codificador_{letra}.xlsx")


def main() -> pd.DataFrame:
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
    corpus = pd.read_csv(cfg.DIR_DATOS / "corpus.csv")
    texto = pd.read_csv(cfg.DIR_DATOS / "variables_texto.csv")[["codigo", "excluida_idioma"]]
    corpus = corpus.merge(texto, on="codigo")
    elegibles = corpus[corpus.excluida_idioma == 0]
    n_total = max(50, int(np.ceil(0.20 * len(elegibles))))
    celdas = ["estrato", "periodo"]
    n_h = asignacion_proporcional(elegibles.groupby(celdas).size(), n_total)

    rng = np.random.default_rng(cfg.SEMILLA_VALIDACION)
    orden = []
    for _, grupo in corpus.sort_values("codigo").groupby(celdas):
        perm = grupo.iloc[rng.permutation(len(grupo))].copy()
        perm["orden_en_estrato"] = range(1, len(perm) + 1)
        orden.append(perm)
    orden = pd.concat(orden)
    orden[["codigo", "estrato", "periodo", "orden_en_estrato", "excluida_idioma"]].to_csv(
        cfg.DIR_DATOS / "orden_aleatorio_validacion.csv", index=False)

    sub = pd.concat([
        orden[(orden.estrato == e) & (orden.periodo == p) & (orden.excluida_idioma == 0)].nsmallest(k, "orden_en_estrato")
        for (e, p), k in n_h.items()
    ]).sort_values("codigo")
    sub[["codigo", "titulo", "artistas", "estrato", "periodo", "orden_en_estrato"]].to_csv(
        cfg.DIR_DATOS / "submuestra_validacion.csv", index=False)

    for i, letra in enumerate(CODIFICADORES):
        plantilla(sub, letra, cfg.SEMILLA_VALIDACION + i + 1)

    print(f"Elegibles: {len(elegibles)} | submuestra: {len(sub)} ({len(sub) / len(elegibles):.0%})")
    print(pd.DataFrame({"N_h elegibles": elegibles.groupby(celdas).size(), "n_h": n_h}).to_string())
    return sub


if __name__ == "__main__":
    main()
