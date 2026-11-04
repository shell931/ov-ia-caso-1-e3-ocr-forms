#!/usr/bin/env python3
"""Lectura del campo manuscrito A QUE COMUNIDAD DE LA ETNIA PERTENECE del E3.

El NLP no lo pide y el texto corrido de la página lo mezcla con las casillas
de etnia; se lee aparte sobre la caja recortada y ampliada, igual que
direccion_vision. Se transcribe tal cual (Ninguna, No aplica, N/A, Wayuu…):
el gold lo trae literal.
"""
from __future__ import annotations

import base64
import io
import os
import re
import unicodedata

from PIL import Image

REGION = (
    float(os.getenv("COM_X0", "0.715")),
    float(os.getenv("COM_Y0", "0.72")),
    float(os.getenv("COM_X1", "0.975")),
    float(os.getenv("COM_Y1", "0.84")),
)
ESCALA = int(os.getenv("COM_ESCALA", "2"))

PROMPT = """Imagen: recorte de un formulario. Arriba está impreso el título
"A QUE COMUNIDAD DE LA ETNIA PERTENECE" (no lo copies). Debajo, a mano,
la persona escribió una respuesta corta (por ejemplo Ninguna, No aplica, N/A,
o el nombre de una comunidad).

¿Qué escribió a mano? Copia el texto manuscrito tal cual, en una línea.
Solo si debajo del título no hay ningún trazo de tinta responde: VACIO
"""


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().lower()


def limpiar(texto: str) -> str:
    s = (texto or "").strip().strip('"').strip("'")
    s = s.splitlines()[0].strip() if s else ""
    s = re.sub(r"(?i)^(respuesta|comunidad)\s*:\s*", "", s).strip()
    if _norm(s) in ("vacio", "none", "-", ""):
        return ""
    if "a que comunidad" in _norm(s):
        return ""
    # El VL suele cerrar con un punto que no está en la caja ("Ninguna.").
    s = re.sub(r"[.,;:]+$", "", s).strip()
    return re.sub(r"\s+", " ", s).strip()


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


def leer_comunidad(ruta_imagen: str, client, modelo: str) -> dict:
    """Devuelve {valor, evidencia, raw}."""
    out = {"valor": "", "evidencia": False, "raw": ""}
    try:
        b64 = recortar_b64(ruta_imagen)
        r = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            max_tokens=40,
            temperature=0.0,
        )
        raw = r.choices[0].message.content or ""
    except Exception:
        return out
    out.update({"valor": limpiar(raw), "evidencia": bool(raw.strip()), "raw": raw.strip()[:120]})
    return out


def aplicar_comunidad(campos: list, lectura: dict | None) -> list:
    """Agrega (o reemplaza) el campo comunidad_etnia con la lectura visual."""
    lectura = lectura or {}
    campos = [c for c in campos if c.get("etiqueta") != "comunidad_etnia"]
    valor = (lectura.get("valor") or "").strip()
    confianza = (90 if valor else 85) if lectura.get("evidencia") else 0
    campos.append({
        "etiqueta": "comunidad_etnia",
        "valor": valor,
        "confianza": confianza,
        "fuente": "comunidad_visual",
    })
    return campos
