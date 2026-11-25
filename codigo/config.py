"""Parámetros del proyecto. Cambiar aquí, nunca dentro de los scripts."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Semillas de los procedimientos aleatorios
SEMILLA = 20261022              # sorteo del estrato 2, bootstrap, permutaciones y figuras
SEMILLA_VALIDACION = 20261024   # sorteo de la submuestra de validación y orden de las plantillas

# Fuente del marco muestral (tabla copiada manualmente de Wikipedia)
FUENTE_MARCO = RAIZ / "datos_crudos" / "wikipedia_2011_2025.docx"
URL_FUENTE_MARCO = "https://en.wikipedia.org/wiki/Billboard_Hot_Latin_Songs_Year-End_Chart"
FECHA_CONSULTA_MARCO = "2026-10-22"

# Instrumento de clasificación de género musical (versionado)
CLASIFICACION_GENERO = RAIZ / "instrumentos" / "clasificacion_genero_v1.1.csv"
METADATOS_INTERPRETES = RAIZ / "instrumentos" / "metadatos_interpretes_v1.1.csv"

# Estrato 2: canciones que llegaron al número uno semanal (Hot Latin Songs o Latin Airplay)
# sin entrar al top 10 anual. Listas de Wikipedia transcritas a texto plano.
FUENTE_ESTRATO2 = RAIZ / "datos_crudos" / "numeros_uno_2011_2025.txt"
URL_FUENTE_ESTRATO2 = ("https://en.wikipedia.org/wiki/"
                       "List_of_Billboard_Hot_Latin_Songs_and_Latin_Airplay_number_ones_of_<año>")
FECHA_CONSULTA_ESTRATO2 = "2026-10-24"
N_ESTRATO2 = 112        # tamaño de la muestra aleatoria del estrato 2 (sección 3 del informe)

# No respuesta: canciones sorteadas cuya letra no se pudo obtener. Salen del corpus analizable
# y el peso de su periodo se recalcula con las canciones que sí tienen letra (N_h / n_h efectivo).
SIN_LETRA = {"C193": "El equipo no encontró la letra en la fuente de consulta"}

# Estratos temporales (inclusive)
PERIODOS = {
    "P1_2011_2015": (2011, 2015),
    "P2_2016_2020": (2016, 2020),
    "P3_2021_2025": (2021, 2025),
}

# Carpeta local de letras: NUNCA se versiona ni se entrega
DIR_LETRAS = RAIZ / "letras"

# Registros: entradas producidas fuera del flujo automático y que este NO regenera
#   codificacion_llm.csv        salida del instrumento (LLM + prompt v1.0), registrada antes de la validación
#   analisis_discrepancias.md   análisis cualitativo de las discrepancias (sección 6.2 del informe)
DIR_REGISTROS = RAIZ / "registros"
LISTA_LETRAS = RAIZ / "datos_crudos" / "lista_letras_diligenciada.xlsx"

DIR_DATOS = RAIZ / "datos"
DIR_RESULTADOS = RAIZ / "resultados"
