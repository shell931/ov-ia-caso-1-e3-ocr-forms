#!/usr/bin/env python3
"""Lectura del pie INFORMACIÓN DEL FUNCIONARIO ELECTORAL RESPONSABLE DE LA
INSCRIPCIÓN del E3: CÉDULA (cuadritos) y NOMBRE (manuscrito).

El NLP no los pide; se leen aparte sobre recortes ampliados de la página ya
normalizada (pagina_e3), igual que comunidad_vision y digitos_vision.
"""
from __future__ import annotations

import base64
import io
import os
import re
import unicodedata

from PIL import Image

REGIONES = {
    "funcionario_cedula": (
        float(os.getenv("FUNC_CED_X0", "0.04")),
        float(os.getenv("FUNC_CED_Y0", "0.925")),
        float(os.getenv("FUNC_CED_X1", "0.52")),
        float(os.getenv("FUNC_CED_Y1", "0.995")),
    ),
    "funcionario_nombre": (
        float(os.getenv("FUNC_NOM_X0", "0.50")),
        float(os.getenv("FUNC_NOM_Y0", "0.925")),
        float(os.getenv("FUNC_NOM_X1", "0.99")),
        float(os.getenv("FUNC_NOM_Y1", "0.995")),
    ),
}
# Medido contra gold_e3 (267): cédula exacta 66 % a escala 2, 51 % a 3, 74 % a 1.
ESCALA = int(os.getenv("FUNC_ESCALA", "1"))

_PROMPT = {
    "funcionario_cedula": """Imagen: recorte del pie de un formulario E3 colombiano. A la derecha de
la etiqueta impresa "CÉDULA" hay una fila de cuadritos; en cada cuadrito hay
a lo sumo UN dígito escrito a mano.

Recorre los cuadritos de izquierda a derecha y escribe el dígito de cada
cuadrito que tenga tinta, sin saltarte ninguno (también los 1 delgados y los
dígitos repetidos seguidos, como 11 o 00).
- Responde SOLO los dígitos, sin espacios ni puntos.
- Cuadritos vacíos al final: no inventes ceros.
- Si todos están vacíos responde exactamente: VACIO
""",
    "funcionario_nombre": """Imagen: recorte del pie de un formulario E3
colombiano, sección "INFORMACIÓN DEL FUNCIONARIO ELECTORAL". Hay una caja con
la etiqueta impresa "NOMBRE" (no la copies) y, a mano, el nombre del
funcionario.

Copia el nombre manuscrito tal cual, letra por letra, en una línea.
- NO corrijas ni completes nombres; no agregues palabras que no estén escritas.
- Solo si la caja no tiene ningún trazo de tinta responde: VACIO
""",
}


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().lower()


def _primera_linea(raw: str) -> str:
    s = (raw or "").strip().strip('"').strip("'")
    return s.splitlines()[0].strip() if s else ""


def limpiar_cedula(raw: str) -> str:
    s = _primera_linea(raw)
    if _norm(s) in ("vacio", "none", "n/a", "-", ""):
        return ""
    return re.sub(r"\D", "", s)


def limpiar_nombre(raw: str) -> str:
    s = _primera_linea(raw)
    s = re.sub(r"(?i)^(respuesta|nombre)\s*:\s*", "", s).strip()
    if _norm(s) in ("vacio", "none", "n/a", "-", ""):
        return ""
    s = re.sub(r"[.,;:]+$", "", s).strip()
    return re.sub(r"\s+", " ", s).strip()


_LIMPIAR = {"funcionario_cedula": limpiar_cedula, "funcionario_nombre": limpiar_nombre}


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
        r = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": _PROMPT[campo]},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            max_tokens=48,
            temperature=0.0,
        )
        raw = r.choices[0].message.content or ""
    except Exception:
        return out
    out.update({"valor": _LIMPIAR[campo](raw), "evidencia": bool(raw.strip()),
                "raw": raw.strip()[:120]})
    return out


def leer_funcionario(ruta_imagen: str, client, modelo: str) -> dict:
    """Devuelve {campo: {valor, evidencia, raw}} para cédula y nombre."""
    return {c: _leer_uno(client, modelo, ruta_imagen, c) for c in REGIONES}


def aplicar_funcionario(campos: list, lectura: dict | None) -> list:
    """Agrega (o reemplaza) funcionario_cedula / funcionario_nombre."""
    lectura = lectura or {}
    campos = [c for c in campos if c.get("etiqueta") not in REGIONES]
    for campo in REGIONES:
        info = lectura.get(campo) or {}
        valor = (info.get("valor") or "").strip()
        confianza = (90 if valor else 85) if info.get("evidencia") else 0
        campos.append({
            "etiqueta": campo,
            "valor": valor,
            "confianza": confianza,
            "fuente": "funcionario_visual",
        })
    return campos
