"""
Paso 4 — Codificación del corpus con el LLM (instrumento de medición).

El instrumento es: modelo + prompt v1.0 (instrumentos/prompt_codificacion_v1.0.txt, SHA-256 en
instrumentos/HASHES_v1.0.txt). Cada canción se envía sola, en una llamada independiente, con la
letra limpia por el mismo procedimiento del paso 2.

Dos modos:
  python s04_codificar_llm.py api     -> llama a la API de Anthropic (requiere ANTHROPIC_API_KEY).
                                         Guarda cada respuesta cruda en resultados/llm_crudo/C###.json
  python s04_codificar_llm.py validar -> (modo por defecto del script maestro) valida y consolida
                                         registros/codificacion_llm.csv sin volver a llamar al modelo.

La codificación usada en el informe se registró en registros/codificacion_llm.csv; la columna
'via' documenta cómo se obtuvo cada fila.
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
from s02_variables_texto import limpiar

PROMPT = cfg.RAIZ / "instrumentos" / "prompt_codificacion_v1.0.txt"
SALIDA = cfg.DIR_REGISTROS / "codificacion_llm.csv"
MODELO_API = "claude-opus-5-5"
VALORES = {"sexual": {0, 1, 2}, "cuerpo": {0, 1}, "agencia": {0, 1}, "duda": {0, 1}}


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def letra_limpia(codigo: str, titulo: str) -> str:
    """Letra limpia en memoria: texto principal + coros de fondo (no se guarda)."""
    crudo = (cfg.DIR_LETRAS / f"{codigo}.txt").read_text(encoding="utf-8")
    principal, coros, _ = limpiar(crudo, titulo)
    return principal.strip() + ("\n(coros de fondo: " + coros + ")" if coros.strip() else "")


def interpretar(texto: str) -> dict:
    datos = json.loads(re.search(r"\{.*\}", texto, re.S).group(0))
    for k, permitidos in VALORES.items():
        if int(datos[k]) not in permitidos:
            raise ValueError(f"Valor fuera del libro de códigos: {k}={datos[k]}")
        datos[k] = int(datos[k])
    return datos


def modo_api() -> None:
    import anthropic  # solo se requiere en este modo

    cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    plantilla = PROMPT.read_text(encoding="utf-8")
    corpus = pd.read_csv(cfg.DIR_DATOS / "corpus.csv")
    crudo_dir = cfg.DIR_RESULTADOS / "llm_crudo"
    crudo_dir.mkdir(parents=True, exist_ok=True)
    filas = []
    for c in corpus.itertuples():
        destino = crudo_dir / f"{c.codigo}.json"
        if not destino.exists():
            msg = cliente.messages.create(
                model=MODELO_API, max_tokens=300, temperature=0,
                messages=[{"role": "user",
                           "content": plantilla.replace("{LETRA}", letra_limpia(c.codigo, c.titulo))}])
            destino.write_text(json.dumps({"respuesta": msg.content[0].text}, ensure_ascii=False))
            time.sleep(1)
        d = interpretar(json.loads(destino.read_text())["respuesta"])
        filas.append({"codigo": c.codigo, **d, "modelo": MODELO_API, "via": "API, temperatura 0",
                      "fecha": date.today().isoformat()})
    df = pd.DataFrame(filas)
    df["prompt_version"], df["prompt_sha256"] = "1.0", sha256(PROMPT)
    df.to_csv(SALIDA, index=False)


def modo_validar() -> pd.DataFrame:
    df = pd.read_csv(SALIDA)
    corpus = pd.read_csv(cfg.DIR_DATOS / "corpus.csv")
    faltan = set(corpus.codigo) - set(df.codigo)
    assert not faltan, f"Canciones sin codificar por el LLM: {sorted(faltan)}"
    for k, permitidos in VALORES.items():
        assert df[k].isin(permitidos).all(), f"Valores inválidos en {k}"
    assert (df.prompt_sha256 == sha256(PROMPT)).all(), "El prompt cambió después de codificar"
    assert df.justificacion.str.split().str.len().max() <= 40, "Justificación demasiado larga"
    print(f"Codificación LLM válida: {len(df)} canciones | prompt v1.0 {sha256(PROMPT)[:12]}…")
    print(df[["sexual", "cuerpo", "agencia", "duda"]].apply(pd.Series.value_counts).fillna(0).astype(int))
    return df


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "validar"
    modo_api() if modo == "api" else modo_validar()
