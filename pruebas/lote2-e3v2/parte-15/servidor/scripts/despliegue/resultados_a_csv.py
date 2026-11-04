"""Pasa el .jsonl de procesar_lote.sh a un CSV: una fila por formulario.

Por cada campo: valor, confianza declarada y si quedó marcado revisar.
Uso: python3 resultados_a_csv.py <resultados.jsonl> <salida.csv>
El CSV tiene PII: tratarlo igual que los formularios.
"""
import csv
import json
import sys

CAMPOS = (
    "formulario_no", "fecha_inscripcion", "tipo_documento", "numero_documento",
    "fecha_expedicion", "primer_apellido", "segundo_apellido", "primer_nombre",
    "segundo_nombre", "nivel_estudio", "email", "telefono_movil", "telefono_fijo",
    "ciudad", "direccion", "lee_braille", "tipo_discapacidad", "etnia",
    "comunidad_etnia", "funcionario_cedula", "funcionario_nombre",
)

src, dst = sys.argv[1], sys.argv[2]
filas = []
for linea in open(src, encoding="utf-8"):
    r = json.loads(linea)
    got = {c["etiqueta"]: c for c in r.get("campos") or []}
    fila = {"doc_id": r.get("doc_id"), "error": r.get("error", "") if not got else ""}
    for campo in CAMPOS:
        c = got.get(campo, {})
        fila[campo] = c.get("valor", "")
        fila[f"{campo}__conf"] = c.get("confianza", "")
        fila[f"{campo}__revisar"] = "SI" if c.get("revisar") else ""
    filas.append(fila)
filas.sort(key=lambda f: str(f["doc_id"]))
with open(dst, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(filas)
print(f"{len(filas)} formularios -> {dst}")
