#!/usr/bin/env python3
"""Confianza medida con las probabilidades del VL (logprobs), no autodeclarada.

ocr_worker envuelve el cliente del VL en ClienteLP por cada lectura (página,
recortes) y guarda, por llamada, los tokens generados con su probabilidad.
nlp_worker, ya con el valor final de cada campo, busca ese valor en la lectura
que lo produjo y toma la probabilidad MÍNIMA de sus caracteres: un solo dígito
dudoso hace dudoso todo el campo.

Resultado por campo: conf_lp (0-100, o ausente si el valor no viene de una
lectura del VL) y, si conf_lp < umbral del campo, revisar=True.
"""
from __future__ import annotations

import math
import os
import re
import unicodedata
from difflib import SequenceMatcher

LEER_LOGPROBS = os.getenv("LEER_LOGPROBS", "1") == "1"
MARCAR = os.getenv("LP_MARCAR", "1") == "1"
UMBRAL_DEFECTO = int(os.getenv("LP_UMBRAL", "70"))
# En estas casillas la probabilidad no separa buenas de malas (AUC ~60 con
# Qwen2.5-VL-7B); las marca la regla de casillas (varias marcas -> conf 40).
# LP_UMBRALES="direccion=40,email=60" cambia el umbral de un campo (0-100).
UMBRALES = {"tipo_discapacidad": 0, "etnia": 0}
UMBRALES.update({
    k.strip(): int(v)
    for k, v in (p.split("=") for p in os.getenv("LP_UMBRALES", "").split(",") if "=" in p)
})
CONF_CASILLA_DUDOSA = 40

DIGITOS = {"numero_documento", "telefono_movil", "telefono_fijo", "formulario_no",
           "funcionario_cedula"}
FECHAS = {"fecha_inscripcion", "fecha_expedicion"}
CASILLAS = {"tipo_documento", "nivel_estudio", "lee_braille", "tipo_discapacidad", "etnia"}

# fuente del campo -> lecturas de ocr_worker donde buscar primero
_LECTURA_DE_FUENTE = {
    "funcionario_visual": ["funcionario"],
    "direccion_visual": ["direccion"],
    "digitos_visual": ["digitos"],
    "comunidad_visual": ["comunidad"],
    "casilla_visual": ["casillas"],
    "email_visual": ["contacto"],
    "contacto_visual": ["contacto"],
    "apellido_visual": ["apellido"],
}
_LECTURA_DE_CAMPO = {
    "funcionario_cedula": ["funcionario"],
    "funcionario_nombre": ["funcionario"],
    "comunidad_etnia": ["comunidad"],
}


class ClienteLP:
    """Mismo uso que el cliente OpenAI (.chat.completions.create) pero pide
    logprobs y deja cada respuesta en self.llamadas."""

    def __init__(self, client):
        self._client = client
        self.llamadas: list = []
        self.chat = self
        self.completions = self

    def create(self, **kw):
        kw.setdefault("logprobs", True)
        r = self._client.chat.completions.create(**kw)
        toks = []
        try:
            for t in r.choices[0].logprobs.content or []:
                toks.append([t.token, round(math.exp(t.logprob), 4)])
        except Exception:
            pass
        self.llamadas.append(toks)
        return r


def _base(c: str) -> str:
    d = unicodedata.normalize("NFD", c)
    return (d[0] if d else c).lower()


def _texto_probs(toks: list) -> tuple[str, list]:
    txt, probs = [], []
    for tok, p in toks:
        tok = str(tok)
        if tok.startswith("bytes:"):
            tok = "\ufffd"
        for ch in tok:
            txt.append(_base(ch))
            probs.append(p)
    return "".join(txt), probs


def _filtrar(txt: str, probs: list, ok) -> tuple[str, list]:
    pares = [(c, p) for c, p in zip(txt, probs) if ok(c)]
    return "".join(c for c, _ in pares), [p for _, p in pares]


def _min_en(txt: str, probs: list, valor: str, difuso: bool) -> float | None:
    if not valor or not txt:
        return None
    i = txt.find(valor)
    if i >= 0:
        return min(probs[i:i + len(valor)])
    if not difuso or len(valor) < 3:
        return None
    sm = SequenceMatcher(None, txt, valor, autojunk=False)
    a, _, n = sm.find_longest_match(0, len(txt), 0, len(valor))
    if n < 3:
        return None
    ini = max(0, a - (len(valor) - n))
    seg = txt[ini:a + len(valor)]
    sm2 = SequenceMatcher(None, seg, valor, autojunk=False)
    if sm2.ratio() < 0.7:
        return None
    pos = [ini + b.a + k for b in sm2.get_matching_blocks() for k in range(b.size)]
    return min(probs[j] for j in pos) if pos else None


def _conf_valor(campo: str, valor: str, toks: list) -> float | None:
    txt, probs = _texto_probs(toks)
    if campo in DIGITOS:
        d = re.sub(r"\D", "", valor)
        t, p = _filtrar(txt, probs, str.isdigit)
        return _min_en(t, p, d, difuso=False)
    if campo in FECHAS:
        d = re.sub(r"\D", "", valor)
        t, p = _filtrar(txt, probs, str.isdigit)
        if len(d) == 8:
            y, m, dd = d[:4], d[4:6], d[6:]
            for cand in (dd + m + y, y + m + dd, dd + m + y[2:], m + dd + y):
                r = _min_en(t, p, cand, difuso=False)
                if r is not None:
                    return r
        return _min_en(t, p, d, difuso=False)
    v = "".join(_base(c) for c in valor)
    v = re.sub(r"\s+", "", v)
    t, p = _filtrar(txt, probs, lambda c: not c.isspace())
    return _min_en(t, p, v, difuso=True)


CASILLA_MODO = os.getenv("LP_CASILLA_MODO", "elegida")


def _conf_casilla(campo: str, toks: list, valor: str = "") -> float | None:
    """Probabilidad de las marcas ([X] / [ ]) en las líneas del campo.

    modo "elegida": solo la marca de la opción elegida (o, sin valor, la
    mínima de todas); modo "min": la mínima de todas las líneas del campo.
    """
    txt, probs = _texto_probs(toks)
    elegida = re.sub(r"[^a-z]", "", "".join(_base(c) for c in valor))
    mins, la_elegida = [], None
    pos = 0
    for linea in txt.split("\n"):
        ini, pos = pos, pos + len(linea) + 1
        s = linea.lstrip("- ").strip()
        if not s.startswith(campo + ".") and not s.startswith(campo + " ."):
            continue
        k = linea.find("=")
        if k < 0:
            continue
        seg = probs[ini + k:ini + len(linea)]
        seg = [p for c, p in zip(linea[k:], seg) if not c.isspace()]
        if not seg:
            continue
        mins.append(min(seg))
        opcion = re.sub(r"[^a-z]", "", s[len(campo) + 1:s.find("=")])
        if elegida and opcion and (opcion.startswith(elegida) or elegida.startswith(opcion)):
            la_elegida = min(seg)
    if not mins:
        return None
    if CASILLA_MODO == "elegida" and la_elegida is not None:
        return la_elegida
    return min(mins)


def _vacio(toks_list: list) -> float | None:
    for toks in toks_list:
        txt, probs = _texto_probs(toks)
        t, p = _filtrar(txt, probs, str.isalpha)
        if t.startswith("vacio"):
            return min(p[:5])
    return None


def conf_campo(c: dict, lp: dict) -> float | None:
    campo = c.get("etiqueta", "")
    if c.get("backfilled"):
        return None
    valor = str(c.get("valor") or "").strip()
    orden = (_LECTURA_DE_FUENTE.get(c.get("fuente") or "")
             or _LECTURA_DE_CAMPO.get(campo) or [])
    orden = orden + [k for k in ("pagina", "numeros") if k not in orden]
    if campo in CASILLAS and (c.get("fuente") == "casilla_visual"):
        for toks in lp.get("casillas") or []:
            r = _conf_casilla(campo, toks, valor)
            if r is not None:
                return r
        return None
    if not valor:
        if orden[0] in ("pagina", "numeros"):
            return None
        return _vacio(lp.get(orden[0]) or [])
    for nombre in orden:
        for toks in lp.get(nombre) or []:
            r = _conf_valor(campo, valor, toks)
            if r is not None:
                return r
    return None


def anotar(campos: list, lp: dict | None) -> list:
    """Agrega conf_lp (0-100) y, bajo el umbral del campo, revisar=True."""
    if not lp:
        return campos
    for c in campos:
        if (MARCAR and c.get("etiqueta") in CASILLAS
                and int(c.get("confianza") or 0) <= CONF_CASILLA_DUDOSA):
            c["revisar"] = True
            c["revisar_por"] = sorted(set(c.get("revisar_por", [])) | {"casilla_dudosa"})
        r = conf_campo(c, lp)
        if r is None:
            continue
        c["conf_lp"] = round(100 * r)
        umbral = UMBRALES.get(c.get("etiqueta", ""), UMBRAL_DEFECTO)
        if MARCAR and c["conf_lp"] < umbral:
            c["revisar"] = True
            c["revisar_por"] = sorted(set(c.get("revisar_por", [])) | {"conf_lp"})
    return campos
