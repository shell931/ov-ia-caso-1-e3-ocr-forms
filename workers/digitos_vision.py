#!/usr/bin/env python3
"""Lectura dedicada de digitos: numero_documento y telefonos sobre recortes.

Parte 10: misma Qwen2.5-VL-7B (no hay VRAM libre para un segundo modelo;
GPU0 ~89 GB / GPU1 ~40 GB reservados). En vez de cuantizar, se recorta la
caja de cédula (casillas) y la de celular/fijo, se amplía y se pide SOLO
digitos a temperatura 0.

El resultado entra al voto numerico del NLP junto con las lecturas de pagina
completa (VOTE_NUMERIC).
"""
from __future__ import annotations

import base64
import io
import os
import re

from PIL import Image

REGIONES = {
    # Fila de casillas NÚMERO DE DOCUMENTO (10 cuadritos).
    # Calibrado 6000000004: escala 2 > 4 (x4 confunde 7/6). Caja un poco
    # más baja/ancha que el label; no llega a FECHA DE EXPEDICIÓN.
    "numero_documento": (
        float(os.getenv("CED_X0", "0.02")),
        float(os.getenv("CED_Y0", "0.330")),
        float(os.getenv("CED_X1", "0.55")),
        float(os.getenv("CED_Y1", "0.410")),
    ),
    "telefono_movil": (
        float(os.getenv("MOVIL_X0", "0.70")),
        float(os.getenv("MOVIL_Y0", "0.600")),
        float(os.getenv("MOVIL_X1", "0.995")),
        float(os.getenv("MOVIL_Y1", "0.662")),
    ),
    "telefono_fijo": (
        float(os.getenv("FIJO_X0", "0.70")),
        float(os.getenv("FIJO_Y0", "0.668")),
        float(os.getenv("FIJO_X1", "0.995")),
        float(os.getenv("FIJO_Y1", "0.728")),
    ),
}

ESCALA = int(os.getenv("DIGITOS_ESCALA", "2"))
CAMPOS = ("numero_documento", "telefono_movil", "telefono_fijo")

_PROMPT = {
    "numero_documento": """Esta imagen es SOLO la fila de casillas
"NÚMERO DE DOCUMENTO" (cédula) de un formulario E3 colombiano.

Lee DÍGITO POR DÍGITO, de izquierda a derecha, lo escrito en cada cuadrito.
- Responde SOLO dígitos, sin espacios.
- Casillas vacías al final: no inventes ceros.
- Ojo: 0/O, 1/l, 5/S, 6/8, 7 con raya.
- Si toda la fila está vacía responde exactamente: VACIO

Respuesta: solo dígitos (o VACIO).
""",
    "telefono_movil": """Esta imagen es SOLO la caja "TELÉFONO MÓVIL" de un E3.

Lee DÍGITO POR DÍGITO el número manuscrito.
- Responde SOLO dígitos, sin espacios.
- NO completes a 10 dígitos. NO inventes.
- Si la caja está vacía o solo rayas: VACIO

Respuesta: solo dígitos (o VACIO).
""",
    "telefono_fijo": """Esta imagen es SOLO la caja "TELÉFONO FIJO" de un E3.

Lee DÍGITO POR DÍGITO el número manuscrito.
- Responde SOLO dígitos, sin espacios.
- NO completes. NO inventes.
- Si la caja está vacía o solo rayas: VACIO

Respuesta: solo dígitos (o VACIO).
""",
}


def _digs(s: str) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _limpiar(raw: str) -> str:
    s = (raw or "").strip().strip('"').strip("'")
    s = s.splitlines()[0].strip() if s else ""
    if re.fullmatch(r"(?i)vacio|vacío|none|n/a|-", s or ""):
        return ""
    return _digs(s)


def _crop_b64(ruta: str, box: tuple[float, float, float, float]) -> str:
    with Image.open(ruta) as im:
        im = im.convert("L")
        W, H = im.size
        x0, y0, x1, y1 = box
        rec = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
        if ESCALA != 1:
            rec = rec.resize((rec.width * ESCALA, rec.height * ESCALA), Image.LANCZOS)
        buf = io.BytesIO()
        rec.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()


def _leer_uno(client, modelo: str, ruta: str, campo: str) -> dict:
    out = {"valor": "", "evidencia": False, "raw": ""}
    try:
        b64 = _crop_b64(ruta, REGIONES[campo])
    except Exception:
        return out
    try:
        r = client.chat.completions.create(
            model=modelo,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT[campo]},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            max_tokens=48,
            temperature=0.0,
        )
        raw = r.choices[0].message.content or ""
    except Exception:
        return out
    valor = _limpiar(raw)
    out.update({"valor": valor, "evidencia": bool(raw.strip()), "raw": raw.strip()[:80]})
    return out


def leer_digitos(ruta_imagen: str, client, modelo: str) -> dict:
    """Devuelve {campo: {valor, evidencia, raw}} para cédula y teléfonos."""
    return {c: _leer_uno(client, modelo, ruta_imagen, c) for c in CAMPOS}


def aplicar_digitos(campos: list, lectura: dict | None) -> list:
    """Pisa numero_documento / telefonos si el recorte trajo digitos utiles.

    Reglas (conservadoras):
    - Si el recorte no tiene evidencia o valor vacio, no toca.
    - Si NLP vacio y recorte tiene digitos, usa recorte.
    - Si ambos tienen valor y el recorte es claramente mas plausible
      (movil 10 digitos empezando por 3; cedula 6-10 digitos) y NLP no,
      usa recorte.
    - Si son iguales tras quitar no-digitos, solo marca fuente.
    """
    lectura = lectura or {}
    for campo in CAMPOS:
        info = lectura.get(campo) or {}
        if not info.get("evidencia"):
            continue
        vision = _digs(info.get("valor"))
        if not vision:
            continue
        dest = next((c for c in campos if c.get("etiqueta") == campo), None)
        nlp = _digs(dest.get("valor") if dest else "")

        if nlp == vision:
            if dest is not None:
                dest["fuente"] = dest.get("fuente") or "nlp"
            continue

        usar = False
        if campo == "telefono_movil":
            # Solo 10 digitos que empiezan por 3. Nunca acortar ni pisar
            # otro movil bien formado (voto ya decidio).
            v_ok = len(vision) == 10 and vision.startswith("3")
            if not v_ok:
                continue
            n_ok = len(nlp) == 10 and nlp.startswith("3")
            if not nlp:
                usar = True
            elif not n_ok:
                usar = True
            elif vision.startswith(nlp) and len(vision) > len(nlp):
                usar = True
        elif campo == "numero_documento":
            # 6-10 digitos; no acortar lo que NLP ya tiene.
            if not (6 <= len(vision) <= 10):
                continue
            if not nlp:
                usar = True
            elif not (6 <= len(nlp) <= 10):
                usar = True
            elif vision.startswith(nlp) and len(vision) > len(nlp):
                usar = True
        elif campo == "telefono_fijo":
            # Muy conservador: solo rellena si NLP vino vacio y hay >=7 digitos.
            # Completar gold incompleto de fijo suele bajar conf_real vs gold.
            if not nlp and len(vision) >= 7:
                usar = True

        if not usar:
            continue

        nuevo = {
            "etiqueta": campo,
            "valor": vision,
            "confianza": 93,
            "fuente": "digitos_visual",
        }
        if dest is None:
            campos.append(nuevo)
        else:
            dest.update(nuevo)
    return campos
