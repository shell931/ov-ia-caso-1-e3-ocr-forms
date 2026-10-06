"""Tabla comparativa de modelos VL sobre la misma muestra (sin PII).

Uso: python3 comparar_modelos.py <dir res> <muestra> <gold.json> <salida.json> modelo1 modelo2 ...
Lee <res>/<modelo>_<muestra>.{kpi.txt,log,jsonl} (de probar_modelo.sh).
Para cada modelo: KPI total y por campo (exacto, conf_real), docs/h y la
política de revisar con el umbral único de conf_lp que atrapa >= 75 % de los
errores (umbral elegido en la mitad A de los documentos, medido en la B).
"""
import json
import os
import re
import subprocess
import sys

RES, MUESTRA, GOLD, OUT = sys.argv[1:5]
MODELOS = sys.argv[5:]
AQUI = os.path.dirname(os.path.abspath(__file__))
OBJETIVO = 75


def kpi(path):
    campos, total = {}, None
    for linea in open(path):
        p = linea.split()
        if len(p) >= 6 and p[1].isdigit() and p[2].endswith("%"):
            fila = {"n": int(p[1]), "exacto": float(p[2].rstrip("%")),
                    "conf_real": float(p[-2].rstrip("%"))}
            if p[0] == "TOTAL":
                total = {"n": int(p[1]), "kpi": float(p[2].rstrip("%"))}
            else:
                campos[p[0]] = fila
    return total, campos


def docs_h(path):
    for linea in open(path):
        m = re.search(r"([\d.]+) docs/h", linea)
        if m:
            return float(m.group(1))
    return None


def politica(jsonl):
    sys.path.insert(0, AQUI)
    cmd = [sys.executable, os.path.join(AQUI, "eval_confianza.py"), jsonl, GOLD, "/tmp/_lp.json", "--recalcular"]
    subprocess.run(cmd, check=True, capture_output=True)
    d = json.load(open("/tmp/_lp.json"))
    os.remove("/tmp/_lp.json")
    filas = d["global"]["lp"]["filas"]
    elegido = next((f for f in filas if f["errores_atrapados_pct"] >= OBJETIVO), filas[-1])
    return {"auc_lp": d["global"]["auc_lp"], "auc_declarada": d["global"]["auc_declarada"],
            "umbral_unico": elegido["umbral"], "con_umbral_unico": elegido,
            "politica_actual": d.get("politica_revisar")}


out = {"muestra": MUESTRA, "modelos": {}}
for m in MODELOS:
    base = os.path.join(RES, f"{m}_{MUESTRA}")
    if not os.path.exists(base + ".kpi.txt"):
        continue
    total, campos = kpi(base + ".kpi.txt")
    out["modelos"][m] = {"total": total, "campos": campos,
                         "docs_h": docs_h(base + ".log") if os.path.exists(base + ".log") else None,
                         "confianza": politica(base + ".jsonl")}

ms = list(out["modelos"])
print(f"{'':22}" + "".join(f"{m[:16]:>17}" for m in ms))
print(f"{'KPI total':22}" + "".join(f"{out['modelos'][m]['total']['kpi']:>16}%" for m in ms))
print(f"{'docs/h':22}" + "".join(f"{str(out['modelos'][m]['docs_h']):>17}" for m in ms))
print(f"{'AUC conf_lp':22}" + "".join(f"{str(out['modelos'][m]['confianza']['auc_lp']):>17}" for m in ms))
print(f"{'umbral p/ atrapar 75%':22}" + "".join(f"{out['modelos'][m]['confianza']['umbral_unico']:>17}" for m in ms))
print(f"{'  % celdas a revisar':22}" + "".join(f"{out['modelos'][m]['confianza']['con_umbral_unico']['marcadas_pct']:>16}%" for m in ms))
print(f"{'  exacto tras revisar':22}" + "".join(f"{out['modelos'][m]['confianza']['con_umbral_unico']['exactitud_tras_revision_pct']:>16}%" for m in ms))
print("exacto % por campo")
for c in out["modelos"][ms[0]]["campos"]:
    print(f"  {c:20}" + "".join(f"{out['modelos'][m]['campos'].get(c, {}).get('exacto', ''):>17}" for m in ms))
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print("->", OUT)
