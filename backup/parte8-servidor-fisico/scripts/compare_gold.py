#!/usr/bin/env python3
"""Compara predicciones del pipeline (nlp_output) contra el gold E3.

Reconstruccion transparente del compare_gold.py que falta en el repo.

Metrica (documentada):
- Se evalua field-level sobre los campos EVAL que tengan valor no vacio en gold.
- correcto  = normalizado(pred) == normalizado(gold) (por tipo de campo).
- conf_real = 100 * (#correctos / #evaluados)         -> exactitud real
- reportada = promedio de 'confianza' del modelo en esos campos
- brecha    = reportada - conf_real                    -> sobrevaloracion
- falsos_100= #campos con confianza>=100 pero incorrectos

Uso: compare_gold.py <gold.json> <resultados.jsonl> [salida.csv]
"""
import sys, json, re, csv, unicodedata
from collections import defaultdict

GOLD = sys.argv[1] if len(sys.argv) > 1 else "/data/e3/gold/gold.json"
PRED = sys.argv[2] if len(sys.argv) > 2 else "/data/e3/resultados.jsonl"
OUTCSV = sys.argv[3] if len(sys.argv) > 3 else "/data/e3/comparacion-mejorado.csv"

EVAL = ["formulario_no", "tipo_documento", "numero_documento",
        "fecha_inscripcion", "fecha_expedicion",
        "primer_apellido", "segundo_apellido", "primer_nombre", "segundo_nombre",
        "email", "telefono_movil", "telefono_fijo", "ciudad", "direccion"]

DOCMAP = {"cc": "cedula_ciudadania", "ce": "cedula_extranjeria",
          "ti": "tarjeta_identidad", "pa": "pasaporte", "pas": "pasaporte",
          "pp": "pasaporte"}


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def norm(s):
    s = strip_accents(s).lower().strip()
    return re.sub(r"\s+", " ", s)


def digits(s):
    return re.sub(r"\D", "", str(s))


def norm_doc(s):
    n = norm(s).replace(" ", "_").strip("_")
    key = n.replace("_", "")
    if key in DOCMAP:
        return DOCMAP[key]
    return n


def is_correct(field, pred, gold):
    if field in ("numero_documento", "telefono_movil", "telefono_fijo", "formulario_no"):
        return digits(pred) == digits(gold) and digits(gold) != ""
    if field.startswith("fecha"):
        return sorted(digits(pred)) == sorted(digits(gold)) and digits(gold) != ""
    if field == "tipo_documento":
        return norm_doc(pred) == norm_doc(gold)
    return norm(pred) == norm(gold)


# cargar gold indexado por id/formulario_no
gold_by_id = {}
for r in json.load(open(GOLD)):
    key = str(r.get("id") or r.get("formulario_no"))
    gold_by_id[key] = r

# cargar predicciones
preds = {}
with open(PRED) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        did = str(r.get("doc_id"))
        campos = {c.get("etiqueta"): c for c in r.get("campos", [])}
        preds[did] = campos

n_docs = 0
tot = correct = 0
conf_sum = 0.0
falsos_100 = 0
per_field = defaultdict(lambda: [0, 0])  # field -> [correct, total]
rows = []

for did, gold in gold_by_id.items():
    if did not in preds:
        continue
    n_docs += 1
    pcampos = preds[did]
    for field in EVAL:
        gval = gold.get(field, "")
        if gval is None or str(gval).strip() == "":
            continue  # solo evaluamos campos con gold
        pc = pcampos.get(field, {})
        pval = pc.get("valor", "")
        conf = float(pc.get("confianza", 0) or 0)
        ok = is_correct(field, pval, gval)
        tot += 1
        conf_sum += conf
        per_field[field][1] += 1
        if ok:
            correct += 1
            per_field[field][0] += 1
        elif conf >= 100:
            falsos_100 += 1
        rows.append([did, field, gval, pval, conf, "ok" if ok else "distinto"])

conf_real = 100.0 * correct / tot if tot else 0.0
reportada = conf_sum / tot if tot else 0.0
brecha = reportada - conf_real

with open(OUTCSV, "w", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["doc_id", "campo", "gold", "pred", "confianza", "estado"])
    w.writerows(rows)

print("=" * 60)
print(f"Documentos evaluados : {n_docs}")
print(f"Campos evaluados     : {tot}")
print(f"Campos correctos     : {correct}")
print("-" * 60)
print(f"CONFIANZA REAL       : {conf_real:.1f}%   (meta >= 80%)")
print(f"Confianza reportada  : {reportada:.1f}%")
print(f"BRECHA (sobrevalor.) : {brecha:+.1f} pts (meta <= 15)")
print(f"FALSOS 100%          : {falsos_100}")
print("-" * 60)
print("Exactitud por campo:")
for field in EVAL:
    c, t = per_field[field]
    if t:
        print(f"  {field:20s} {c:3d}/{t:3d}  {100.0*c/t:5.1f}%")
print(f"\nCSV detalle -> {OUTCSV}")
