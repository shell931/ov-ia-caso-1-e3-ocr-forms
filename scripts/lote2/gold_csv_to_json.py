#!/usr/bin/env python3
"""Convierte el gold CSV del lote E3V2 al gold.json que lee compare_gold_real.py.

Uso: python3 gold_csv_to_json.py gold_e3.csv gold_lote2.json

Convenciones (las mismas que aplica el pipeline a su salida):
  - casillas con dos o más marcas -> vacío (el formulario las invalida)
  - CEDULA DE CIUDADANIA -> CEDULA_CIUDADANIA, COM.NEGRAS -> COM_NEGRAS,
    ROM (GITANA) -> ROM
  - teléfonos solo dígitos; N/A -> vacío; prefijo 57 de 12 dígitos fuera
  - BOGOTA D.C / DC -> BOGOTA (corregir_ciudad colapsa todas a Bogotá)
  - comunidad_etnia literal (Ninguna, No aplica, N/A…)
El JSON resultante tiene PII: va solo al servidor, nunca a git.
"""
import csv
import json
import re
import sys

COLS = {
    "formulario_no": "FORMULARIO No.",
    "fecha_inscripcion": "FECHA DE INSCRIPCIÓN",
    "tipo_documento": "TIPO DE DOCUMENTO",
    "numero_documento": "NÚMERO DE DOCUMENTO",
    "fecha_expedicion": "FECHA DE EXPEDICIÓN",
    "primer_apellido": "PRIMER APELLIDO",
    "segundo_apellido": "SEGUNDO APELLIDO",
    "primer_nombre": "PRIMER NOMBRE",
    "segundo_nombre": "SEGUNDO NOMBRE",
    "nivel_estudio": "NIVEL DE ESTUDIO",
    "telefono_movil": "TELÉFONO MÓVIL",
    "email": "CORREO ELECTRONICO",
    "ciudad": "CIUDAD / MUNICIPIO DE RESIDENCIA",
    "direccion": "DIRECCIÓN Y/O LUGAR DE RESIDEN",
    "telefono_fijo": "TELÉFONO FIJO",
    "lee_braille": "LEE BRAILLE",
    "tipo_discapacidad": "TIPO DE DISCAPACIDAD",
    "etnia": "ETNIA",
    "comunidad_etnia": "A QUE COMUNIDAD DE LA ETNIA PERTENECE",
}
CASILLAS = {"tipo_documento", "nivel_estudio", "lee_braille", "tipo_discapacidad", "etnia"}
ALIAS = {
    "CEDULA DE CIUDADANIA": "CEDULA_CIUDADANIA",
    "CEDULA DE EXTRANJERIA": "CEDULA_EXTRANJERIA",
    "COM.NEGRAS": "COM_NEGRAS",
    "ROM (GITANA)": "ROM",
}


def telefono(v: str) -> str:
    d = re.sub(r"\D", "", v)
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    return d


def ciudad(v: str) -> str:
    return "BOGOTA" if re.fullmatch(r"BOGOTA\s*D\.?\s*C\.?", v.strip().upper()) else v


def convertir(row: dict) -> dict:
    out = {}
    for campo, col in COLS.items():
        v = (row.get(col) or "").strip()
        if campo in CASILLAS:
            v = "" if ";" in v else ALIAS.get(v, v)
        elif campo.startswith("telefono"):
            v = telefono(v)
        elif campo == "ciudad":
            v = ciudad(v)
        out[campo] = v
    out["id"] = out["formulario_no"]
    return out


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    rows = [convertir(r) for r in csv.DictReader(open(src, encoding="utf-8-sig"))]
    json.dump(rows, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    multi = {c: sum(1 for r in csv.DictReader(open(src, encoding="utf-8-sig"))
                    if ";" in (r.get(COLS[c]) or "")) for c in sorted(CASILLAS)}
    print(f"gold docs: {len(rows)} -> {dst}")
    print("casillas con 2+ marcas (gold vacío):", multi)


if __name__ == "__main__":
    main()
