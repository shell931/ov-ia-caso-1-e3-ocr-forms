#!/usr/bin/env python3
"""Deja solo el E-3 cuando el escaneo trae E-3 + E-4 en una misma página.

Todos los recortes (casillas, dirección, dígitos, comunidad) están en
fracciones de una página E-3 sola, alto ≈ 0,88 × ancho. Algunos escaneos
vienen con el E-4 debajo (alto ≈ 1,32 × ancho); ahí cada recorte cae en otra
caja y el VL de página completa ve dos formularios. Si la página es más alta
que E3_RATIO_MAX, se conserva la parte de arriba con la proporción de un
E-3 normal y el resto del pipeline trabaja sobre esa imagen.
"""
from __future__ import annotations

import os

from PIL import Image

RATIO_MAX = float(os.getenv("E3_RATIO_MAX", "1.05"))
ALTO_REL = float(os.getenv("E3_ALTO_REL", "0.882"))
DIR_TMP = os.getenv("E3_DIR_TMP", "/tmp/e3_pagina")


def normalizar(ruta_imagen: str, doc_id: str) -> tuple[str, dict]:
    """Devuelve (ruta a usar, info). Sin cambio si la página ya es un E-3 solo."""
    with Image.open(ruta_imagen) as im:
        W, H = im.size
        if H / W <= RATIO_MAX:
            return ruta_imagen, {"recortada": False, "original": [W, H]}
        alto = min(H, round(W * ALTO_REL))
        os.makedirs(DIR_TMP, exist_ok=True)
        destino = os.path.join(DIR_TMP, f"{doc_id}.tif")
        im.crop((0, 0, W, alto)).save(destino, format="TIFF", compression="tiff_lzw")
    return destino, {"recortada": True, "original": [W, H], "usada": [W, alto]}
