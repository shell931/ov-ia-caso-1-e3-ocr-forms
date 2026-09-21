#!/usr/bin/env python3
"""Lectura focalizada de CORREO / TELEFONO MOVIL del E3 sobre recortes ampliados.

Por que una pasada aparte
-------------------------
email ~37% exacto (51 casi): el VLM en pagina completa confunde letras del
usuario (angelaperez38 -> angulare13). Un recorte de la caja CORREO, ampliado,
transcribe caracter a caracter.

telefono_movil ~40%: hay errores de digito a misma longitud (~15) y vacios.
OJO: ~29 fails son gold truncado vs el formulario (gold 31237932, form
3123793266). Leer el form bien no arregla esos; no inventar digitos extras
tampoco empeora esos casos. Si ayuda a no inventar cuando la caja esta vacia
o a corregir un digito suelto.
"""
from __future__ import annotations

import base64
import io
import os
import re
import unicodedata

from PIL import Image

# Fracciones de (ancho, alto). Calibrado sobre front/*.tif (~2500x2200):
# fila CORREO + MOVIL justo debajo de NIVEL DE ESTUDIO; FIJO al lado de DIRECCION.
REGIONES = {
    "email": (
        float(os.getenv("EMAIL_X0", "0.02")),
        float(os.getenv("EMAIL_Y0", "0.605")),
        float(os.getenv("EMAIL_X1", "0.70")),
        float(os.getenv("EMAIL_Y1", "0.665")),
    ),
    "telefono_movil": (
        float(os.getenv("MOVIL_X0", "0.70")),
        float(os.getenv("MOVIL_Y0", "0.605")),
        float(os.getenv("MOVIL_X1", "0.995")),
        float(os.getenv("MOVIL_Y1", "0.665")),
    ),
    "telefono_fijo": (
        float(os.getenv("FIJO_X0", "0.70")),
        float(os.getenv("FIJO_Y0", "0.665")),
        float(os.getenv("FIJO_X1", "0.995")),
        float(os.getenv("FIJO_Y1", "0.735")),
    ),
}
ESCALA = int(os.getenv("CONTACTO_ESCALA", "3"))

PROMPTS = {
    "email": """Esta imagen es SOLO la caja manuscrita
"CORREO ELECTRÓNICO" de un formulario E3 colombiano.

Transcribe el correo EXACTO, tal como está escrito.
- Copia mayúsculas/minúsculas, puntos, guiones y el @ tal cual.
- Conserva espacios si los hay (ej. "foo @ bar . com").
- Conserva el punto final si está escrito.
- NO inventes, NO completes el usuario ni el dominio, NO corrijas "hotamail".
- Si la caja está vacía, o solo tiene N/A / NA / -, responde exactamente: VACIO

Respuesta: solo el correo (o VACIO), sin comillas ni explicación.
""",
    "telefono_movil": """Esta imagen es SOLO la caja manuscrita
"TELÉFONO MÓVIL" de un formulario E3 colombiano.

Transcribe SOLO los dígitos escritos, en orden, sin espacios.
- NO agregues dígitos para completar a 10.
- NO inventes. Si ves "000" o tachaduras sin número real, responde: 000
- Si la caja está vacía responde exactamente: VACIO

Respuesta: solo dígitos (o 000 o VACIO), sin texto extra.
""",
    "telefono_fijo": """Esta imagen es SOLO la caja manuscrita
"TELÉFONO FIJO" de un formulario E3 colombiano.

Transcribe SOLO los dígitos escritos, en orden, sin espacios.
- NO agregues dígitos. NO inventes.
- Si ves "000" responde: 000
- Si la caja está vacía responde exactamente: VACIO

Respuesta: solo dígitos (o 000 o VACIO), sin texto extra.
""",
}


def _norm_cmp(s: str) -> str:
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().lower()


def _vacio(s: str) -> bool:
    return _norm_cmp(s) in (
        "vacio", "vacío", "none", "n/a", "na", "nil", "-", "",
    )


def limpiar_email(texto: str) -> str:
    s = (texto or "").strip().strip('"').strip("'")
    s = s.splitlines()[0].strip() if s else ""
    s = re.sub(r"(?i)^(correo|email|e-mail|respuesta)\s*:\s*", "", s).strip()
    if _vacio(s):
        return ""
    # higiene minima: no borrar espacios internos (gold a veces los trae)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def limpiar_tel(texto: str) -> str:
    s = (texto or "").strip().strip('"').strip("'")
    s = s.splitlines()[0].strip() if s else ""
    s = re.sub(r"(?i)^(telefono|tel|movil|fijo|respuesta)\s*:\s*", "", s).strip()
    if _vacio(s):
        return ""
    dig = re.sub(r"\D", "", s)
    return dig


def recortar_b64(ruta_imagen: str, region: tuple[float, float, float, float]) -> str:
    with Image.open(ruta_imagen) as im:
        im = im.convert("L")
        W, H = im.size
        x0, y0, x1, y1 = region
        rec = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
        if ESCALA != 1:
            rec = rec.resize((rec.width * ESCALA, rec.height * ESCALA), Image.LANCZOS)
        buf = io.BytesIO()
        rec.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()


def _leer_campo(ruta_imagen: str, client, modelo: str, campo: str) -> dict:
    out = {"valor": "", "evidencia": False, "raw": ""}
    region = REGIONES.get(campo)
    prompt = PROMPTS.get(campo)
    if not region or not prompt:
        return out
    try:
        b64 = recortar_b64(ruta_imagen, region)
    except Exception:
        return out
    try:
        r = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            max_tokens=80,
            temperature=0.0,
        )
        raw = r.choices[0].message.content or ""
    except Exception:
        return out
    if campo == "email":
        valor = limpiar_email(raw)
    else:
        valor = limpiar_tel(raw)
    out.update({"valor": valor, "evidencia": bool(raw.strip()), "raw": raw.strip()[:200]})
    return out


def leer_contacto(ruta_imagen: str, client, modelo: str) -> dict:
    """Devuelve {email, telefono_movil, telefono_fijo} cada uno {valor,evidencia,raw}."""
    return {
        campo: _leer_campo(ruta_imagen, client, modelo, campo)
        for campo in ("email", "telefono_movil", "telefono_fijo")
    }


def _email_score(s: str) -> int:
    s = s or ""
    has_at = 1 if "@" in s else 0
    has_dot = 1 if "." in s else 0
    return has_at * 5 + has_dot * 2 + len(s)


def _tel_usable(vision: str, nlp: str) -> bool:
    """Vision gana si NLP vacio, o vision no inventa relleno, o corrige digito."""
    if not vision and nlp:
        # vision vacio: solo pisar NLP si NLP parece inventado (muy largo vs tipico)
        return False
    if vision and not nlp:
        return True
    if not vision:
        return False
    if vision == nlp:
        return False
    # Preferir vision si NLP agrego digitos de mas (padding a 10) y vision es prefijo
    if nlp.startswith(vision) and len(nlp) > len(vision):
        return True
    # Preferir vision si misma longitud (posible correccion de digito)
    if len(vision) == len(nlp) and len(vision) >= 7:
        return True
    # Preferir vision si NLP es prefijo corto de vision (NLP corto) — NO:
    # eso pelea con gold truncado. Mejor no.
    if vision.startswith(nlp) and len(vision) > len(nlp):
        return False
    # Si longitudes distintas y no es padding claro, quedarse con NLP
    return False


def aplicar_contacto(campos: list, lectura: dict | None) -> list:
    """Sobrescribe email / telefonos si el recorte visual aporta."""
    lectura = lectura or {}
    if not lectura:
        return campos

    # --- email ---
    em = lectura.get("email") or {}
    if em.get("evidencia"):
        vision = (em.get("valor") or "").strip()
        dest = next((c for c in campos if c.get("etiqueta") == "email"), None)
        nlp = (dest.get("valor") or "").strip() if dest else ""
        if vision and _norm_cmp(vision) != _norm_cmp(nlp):
            # Preferir vision si NLP vacio o vision parece mas completa / con @
            if (not nlp) or (_email_score(vision) >= _email_score(nlp) - 1):
                nuevo = {
                    "etiqueta": "email",
                    "valor": vision,
                    "confianza": 92,
                    "fuente": "email_visual",
                }
                if dest is None:
                    campos.append(nuevo)
                else:
                    dest.update(nuevo)
        elif not vision and nlp and _norm_cmp(nlp) not in ("n/a", "na"):
            # caja vacia: no inventar. Si NLP puso algo raro, limpiar solo si
            # NLP no parece un correo real con @.
            pass

    # --- telefonos ---
    for campo in ("telefono_movil", "telefono_fijo"):
        lec = lectura.get(campo) or {}
        if not lec.get("evidencia"):
            continue
        vision = (lec.get("valor") or "").strip()
        dest = next((c for c in campos if c.get("etiqueta") == campo), None)
        nlp = re.sub(r"\D", "", str(dest.get("valor") or "") if dest else "")
        # "000" es valor gold valido (placeholder en el form)
        if vision == "000":
            nuevo = {
                "etiqueta": campo,
                "valor": "000",
                "confianza": 90,
                "fuente": "contacto_visual",
            }
            if dest is None:
                campos.append(nuevo)
            else:
                dest.update(nuevo)
            continue
        if not vision:
            # caja vacia: si NLP invento digitos, borrar
            if nlp and dest is not None:
                dest["valor"] = ""
                dest["fuente"] = "contacto_visual_vacio"
                dest["confianza"] = 80
            continue
        if _tel_usable(vision, nlp):
            nuevo = {
                "etiqueta": campo,
                "valor": vision,
                "confianza": 92,
                "fuente": "contacto_visual",
            }
            if dest is None:
                campos.append(nuevo)
            else:
                dest.update(nuevo)
    return campos
