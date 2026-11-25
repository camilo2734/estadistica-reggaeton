"""
Script maestro: reproduce todo el análisis desde cero, sin intervención manual.

    python ejecutar_todo.py

Requiere: la carpeta letras/ con C001.txt … C196.txt (local, NO incluida en el repositorio)
las plantillas diligenciadas de los codificadores en datos/codificacion_humana/ y los registros
de registros/ (codificación del LLM y análisis cualitativo de discrepancias). Todo lo demás
(datos/, resultados/, entregables/) se regenera.
"""
import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "codigo"))

PASOS = [
    ("s01_marco_muestral", "Marco muestral y corpus"),
    ("s02_variables_texto", "Limpieza de letras y variables de texto"),
    ("s03_submuestra_validacion", "Submuestra de validación (semilla fija) y plantillas"),
    ("s04_codificar_llm", "Verificación de la codificación LLM (prompt v1.0)"),
    ("s05_validacion", "Kappas, matrices de confusión y discrepancias"),
    ("s06_inferencia", "Base analítica e inferencia"),
    ("s07_graficos", "Figuras"),
    ("s09_informe", "Informe técnico en PDF"),
    ("s10_divulgacion", "Producto divulgativo (carrusel)"),
    ("s11_diccionario", "Diccionario de variables de las bases CSV"),
    ("s08_verificar_letras", "Auditoría: ningún archivo contiene texto de letras"),
]

if __name__ == "__main__":
    inicio = time.time()
    for modulo, nombre in PASOS:
        print(f"\n{'=' * 70}\n{nombre}  [{modulo}]\n{'=' * 70}")
        m = importlib.import_module(modulo)
        m.modo_validar() if modulo == "s04_codificar_llm" else m.main()
    print(f"\nListo en {time.time() - inicio:.0f} s.")
