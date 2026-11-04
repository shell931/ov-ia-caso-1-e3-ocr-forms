#!/usr/bin/env python3
"""Segunda lectura de PRIMER APELLIDO sobre el recorte ampliado de su caja.

El apellido hoy sale de una sola pasada (pagina completa + NLP). Los fallos
"casi" son una o dos letras (Casillo/Castillo, Herrea/Herrera).

Medido offline en los 100 (2026-09-23, Qwen2.5-VL-7B, recorte x4):
1 win y 16 losses si se pisa el NLP. No activar con este modelo.
Esta pasada no toca los demas campos.
"""
from __future__ import annotations

import base64
import io
import os
import re
import unicodedata

from PIL import Image

# Caja izquierda PRIMER APELLIDO, debajo del numero de documento.
# Calibrada en front/*.tif ~2500x2200: incluye la etiqueta impresa y la tinta.
REGION = (
    float(os.getenv("APE1_X0", "0.02")),
    float(os.getenv("APE1_Y0", "0.438")),
    float(os.getenv("APE1_X1", "0.49")),
    float(os.getenv("APE1_Y1", "0.505")),
)
ESCALA = int(os.getenv("APE1_ESCALA", "4"))

PROMPT = """Esta imagen es SOLO la caja manuscrita "PRIMER APELLIDO"
de un formulario E3 colombiano.

Transcribe el apellido EXACTO, tal como está escrito.
- Una sola línea. Conserva tildes, eñe y mayúsculas.
- NO completes, NO corrijas, NO agregues el segundo apellido ni el nombre.
- Ignora el texto impreso "PRIMER APELLIDO".
- Si la caja está vacía responde exactamente: VACIO

Respuesta: solo el apellido (o VACIO), sin comillas ni explicación.
"""


def _norm_cmp(s: str) -> str:
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().lower()


def limpiar(texto: str) -> str:
    s = (texto or "").strip().strip('"').strip("'")
    s = s.splitlines()[0].strip() if s else ""
    s = re.sub(
        r"(?i)^(primer apellido|apellido|respuesta)\s*:\s*", "", s
    ).strip()
    if _norm_cmp(s) in ("vacio", "vacío", "none", "n/a", "na", "-", ""):
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    return s


def recortar_b64(ruta_imagen: str) -> str:
    with Image.open(ruta_imagen) as im:
        im = im.convert("L")
        W, H = im.size
        x0, y0, x1, y1 = REGION
        rec = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
        if ESCALA != 1:
            rec = rec.resize((rec.width * ESCALA, rec.height * ESCALA), Image.LANCZOS)
        buf = io.BytesIO()
        rec.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()


def leer_primer_apellido(ruta_imagen: str, client, modelo: str) -> dict:
    """Devuelve {valor, evidencia, raw}."""
    out = {"valor": "", "evidencia": False, "raw": ""}
    try:
        b64 = recortar_b64(ruta_imagen)
    except Exception:
        return out
    try:
        r = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            max_tokens=40,
            temperature=0.0,
        )
        raw = r.choices[0].message.content or ""
    except Exception:
        return out
    valor = limpiar(raw)
    out.update({"valor": valor, "evidencia": bool(raw.strip()), "raw": raw.strip()[:200]})
    return out


def aplicar_primer_apellido(campos: list, lectura: dict | None) -> list:
    """Pisa solo primer_apellido si el recorte trajo un apellido."""
    lectura = lectura or {}
    if not lectura.get("evidencia"):
        return campos
    vision = (lectura.get("valor") or "").strip()
    if not vision:
        return campos
    dest = next((c for c in campos if c.get("etiqueta") == "primer_apellido"), None)
    nlp = (dest.get("valor") or "").strip() if dest else ""
    if _norm_cmp(vision) == _norm_cmp(nlp):
        if dest is not None:
            dest["fuente"] = dest.get("fuente") or "nlp"
        return campos
    nuevo = {
        "etiqueta": "primer_apellido",
        "valor": vision,
        "confianza": 92,
        "fuente": "apellido_visual",
    }
    if dest is None:
        campos.append(nuevo)
    else:
        dest.update(nuevo)
    return campos
