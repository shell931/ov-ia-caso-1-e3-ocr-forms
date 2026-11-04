#!/usr/bin/env python3
"""Lectura focalizada del campo DIRECCION del E3 sobre un recorte ampliado.

Por que una pasada aparte
-------------------------
direccion ~17% exacto: la mayoria son "casi" (sim ~86%). El VLM en pagina
completa pierde letras de via, digitos o el sufijo SUR. Una pasada solo sobre
la caja DIRECCION, ampliada, transcribe el texto tal cual (sin rearmar JSON:
reestructurar Cll/# rompia matches contra gold que dice Calle/Kra/etc.).
"""
from __future__ import annotations

import base64
import io
import os
import re
import unicodedata

from PIL import Image

REGION = (
    float(os.getenv("DIR_X0", "0.04")),
    float(os.getenv("DIR_Y0", "0.655")),
    float(os.getenv("DIR_X1", "0.78")),
    float(os.getenv("DIR_Y1", "0.722")),
)
ESCALA = int(os.getenv("DIR_ESCALA", "3"))

PROMPT = """Esta imagen es SOLO la caja manuscrita
"DIRECCIÓN Y/O LUGAR DE RESIDENCIA" de un formulario E3 colombiano.

Transcribe la dirección EXACTA, en UNA sola línea, tal como está escrita.
- Copia tipo de vía como aparece (Calle/Cll/Cra/Kra/Tv/Av/Dg…).
- Conserva letras de la vía (90J, 71 a, 54 F, Bis).
- Conserva # o Nº y guiones (50-29, 79-97).
- Conserva Sur/Norte/Este/Oeste y complementos (Torre, Apto, Etapa…).
- NO inventes, NO completes, NO reformatees.
- Si la caja está vacía responde exactamente: VACIO

Respuesta: solo la dirección (o VACIO), sin comillas ni explicación.
"""


def _norm_cmp(s: str) -> str:
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().lower()


def limpiar(texto: str) -> str:
    s = (texto or "").strip().strip('"').strip("'")
    s = s.splitlines()[0].strip() if s else ""
    # quitar prefijos tipicos del modelo
    s = re.sub(r"(?i)^(direccion|la direccion|respuesta)\s*:\s*", "", s).strip()
    if _norm_cmp(s) in ("vacio", "vacío", "none", "n/a", "-"):
        return ""
    # higiene minima que no cambia el match vs gold tipico
    s = s.replace("+", "#")
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


def leer_direccion(ruta_imagen: str, client, modelo: str) -> dict:
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
            max_tokens=120,
            temperature=0.0,
        )
        raw = r.choices[0].message.content or ""
    except Exception:
        return out
    valor = limpiar(raw)
    out.update({"valor": valor, "evidencia": bool(raw.strip()), "raw": raw.strip()[:200]})
    return out


def _score(s: str) -> int:
    """Heuristica simple de completitud (mas tokens/digitos = mejor)."""
    s = s or ""
    dig = len(re.findall(r"\d", s))
    toks = len(re.findall(r"[A-Za-z0-9]+", s))
    has_hash = 1 if "#" in s or "nº" in s.lower() or "no." in s.lower() else 0
    return dig * 3 + toks + has_hash * 2 + len(s) // 4


def aplicar_direccion(campos: list, lectura: dict | None) -> list:
    """Usa la lectura visual si aporta mas que el valor NLP (o si NLP vacio)."""
    lectura = lectura or {}
    if not lectura.get("evidencia"):
        return campos
    vision = (lectura.get("valor") or "").strip()
    dest = next((c for c in campos if c.get("etiqueta") == "direccion"), None)
    nlp = (dest.get("valor") or "").strip() if dest else ""

    if not vision:
        return campos
    # Preferir vision si NLP vacio, o si vision parece mas completa.
    # Si son iguales tras normalizar, no tocar.
    if _norm_cmp(vision) == _norm_cmp(nlp):
        if dest is not None:
            dest["fuente"] = dest.get("fuente") or "nlp"
        return campos
    if nlp and _score(vision) < _score(nlp) - 2:
        # vision claramente peor: conservar NLP
        return campos

    nuevo = {
        "etiqueta": "direccion",
        "valor": vision,
        "confianza": 92,
        "fuente": "direccion_visual",
    }
    if dest is None:
        campos.append(nuevo)
    else:
        dest.update(nuevo)
    return campos
