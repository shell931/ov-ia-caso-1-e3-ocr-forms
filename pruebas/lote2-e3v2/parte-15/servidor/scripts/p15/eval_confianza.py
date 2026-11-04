"""¿Qué tan bien separa conf_lp los campos buenos de los malos? (vs gold)

Uso: python3 eval_confianza.py resultados.jsonl gold.json [salida.json] [--recalcular]

--recalcular: vuelve a calcular conf_lp con workers/confianza_lp.py sobre las
lecturas guardadas (corrida con LP_GUARDAR=1), sin volver a correr el VL.

Imprime, por campo, para cada umbral: % de celdas marcadas, % de los errores
reales que quedan marcados (recall) y exactitud de lo NO marcado. Compara con la
confianza autodeclarada. salida.json (opcional) solo trae agregados, sin PII.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "workers"))

args = [a for a in sys.argv[1:] if not a.startswith("--")]
RECALC = "--recalcular" in sys.argv
EXCLUIR = set()
for a in sys.argv[1:]:
    if a.startswith("--excluir="):
        EXCLUIR = set(a.split("=", 1)[1].split(","))
SRC, GOLD = args[0], args[1]
OUT = args[2] if len(args) > 2 else None
UMBRALES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95]


def norm(v):
    s = unicodedata.normalize("NFD", str(v or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


gold = json.load(open(GOLD))
if isinstance(gold, list):
    gold = {str(g["id"]): g for g in gold}
if RECALC:
    import confianza_lp

celdas = []
for linea in open(SRC):
    r = json.loads(linea)
    g = gold.get(str(r["doc_id"]))
    if not g or not r.get("campos"):
        continue
    if RECALC:
        for c in r["campos"]:
            c.pop("conf_lp", None)
            if "revisar_por" in c:
                resto = set(c.pop("revisar_por")) - {"conf_lp", "casilla_dudosa"}
                if resto:
                    c["revisar_por"] = sorted(resto)
                else:
                    c.pop("revisar", None)
        confianza_lp.anotar(r["campos"], r.get("lp"))
    for c in r["campos"]:
        campo = c["etiqueta"]
        if campo not in g or campo in EXCLUIR:
            continue
        celdas.append({
            "doc": str(r["doc_id"]),
            "campo": campo,
            "ok": norm(c.get("valor")) == norm(g.get(campo)),
            "lp": c.get("conf_lp"),
            "dec": int(c.get("confianza") or 0),
            "pol": bool(c.get("revisar")),
        })


def tabla(cs, clave, umbrales):
    n = len(cs)
    mal = sum(not c["ok"] for c in cs)
    filas = []
    for u in umbrales:
        marc = [c for c in cs if c[clave] is not None and c[clave] < u]
        resto = [c for c in cs if not (c[clave] is not None and c[clave] < u)]
        mm = sum(not c["ok"] for c in marc)
        filas.append({
            "umbral": u,
            "marcadas_pct": round(100 * len(marc) / n, 1) if n else 0,
            "errores_atrapados_pct": round(100 * mm / mal, 1) if mal else 0,
            "precision_pct": round(100 * mm / len(marc), 1) if marc else 0,
            "exactitud_no_marcadas_pct": round(100 * sum(c["ok"] for c in resto) / len(resto), 1) if resto else 0,
            # si una persona corrige todo lo marcado
            "exactitud_tras_revision_pct": round(100 * (n - (mal - mm)) / n, 1) if n else 0,
        })
    return {"n": n, "errores": mal, "sin_lp": sum(c[clave] is None for c in cs), "filas": filas}


def auc(cs, clave):
    """P(conf de una celda buena > conf de una mala). 50 = no separa."""
    b = [c[clave] for c in cs if c["ok"] and c[clave] is not None]
    m = [c[clave] for c in cs if not c["ok"] and c[clave] is not None]
    if not b or not m:
        return None
    gana = sum((x > y) + 0.5 * (x == y) for x in b for y in m)
    return round(100 * gana / (len(b) * len(m)), 1)


campos = sorted({c["campo"] for c in celdas})
res = {"n_celdas": len(celdas), "global": {}, "por_campo": {}}
res["global"]["lp"] = tabla(celdas, "lp", UMBRALES)
res["global"]["declarada"] = tabla(celdas, "dec", UMBRALES)
res["global"]["auc_lp"] = auc(celdas, "lp")
res["global"]["auc_declarada"] = auc(celdas, "dec")
print(f"celdas {len(celdas)} · errores {res['global']['lp']['errores']} · "
      f"AUC conf_lp {res['global']['auc_lp']} vs declarada {res['global']['auc_declarada']}")
print("umbral | conf_lp: marcadas atrapa precisión tras-revisar | declarada: marcadas atrapa tras-revisar")
for a, b in zip(res["global"]["lp"]["filas"], res["global"]["declarada"]["filas"]):
    print(f"  <{a['umbral']:<3} | {a['marcadas_pct']:>8}% {a['errores_atrapados_pct']:>6}% "
          f"{a['precision_pct']:>8}% {a['exactitud_tras_revision_pct']:>9}%   | "
          f"{b['marcadas_pct']:>8}% {b['errores_atrapados_pct']:>6}% {b['exactitud_tras_revision_pct']:>9}%")
print()
print(f"{'campo':20} {'n':>4} {'mal':>4} {'AUC lp':>7} {'AUC dec':>8}  marcadas/atrapa @30 @50 @70")
for campo in campos:
    cs = [c for c in celdas if c["campo"] == campo]
    t = tabla(cs, "lp", UMBRALES)
    res["por_campo"][campo] = {"tabla_lp": t, "auc_lp": auc(cs, "lp"), "auc_declarada": auc(cs, "dec")}
    f = {x["umbral"]: x for x in t["filas"]}
    print(f"{campo:20} {t['n']:>4} {t['errores']:>4} {str(res['por_campo'][campo]['auc_lp']):>7} "
          f"{str(res['por_campo'][campo]['auc_declarada']):>8}  "
          + "  ".join(f"{f[u]['marcadas_pct']}/{f[u]['errores_atrapados_pct']}" for u in (30, 50, 70)))


def elegir_umbrales(cs, objetivo):
    """Por campo, el umbral más bajo que atrapa >= objetivo % de sus errores."""
    out = {}
    for campo in sorted({c["campo"] for c in cs}):
        cc = [c for c in cs if c["campo"] == campo]
        mal = [c for c in cc if not c["ok"]]
        if not mal:
            out[campo] = 0
            continue
        out[campo] = 101
        for u in range(5, 101, 5):
            atr = sum(1 for c in mal if c["lp"] is not None and c["lp"] < u)
            if 100 * atr / len(mal) >= objetivo:
                out[campo] = u
                break
    return out


def aplicar_umbrales(cs, um):
    n = len(cs)
    mal = sum(not c["ok"] for c in cs)
    marc = [c for c in cs if c["lp"] is not None and c["lp"] < um.get(c["campo"], 0)]
    mm = sum(not c["ok"] for c in marc)
    return {"marcadas_pct": round(100 * len(marc) / n, 1),
            "errores_atrapados_pct": round(100 * mm / mal, 1) if mal else 0,
            "exactitud_sin_revisar_pct": round(100 * (n - mal) / n, 1),
            "exactitud_tras_revision_pct": round(100 * (n - (mal - mm)) / n, 1)}


n, mal = len(celdas), sum(not c["ok"] for c in celdas)
marc = [c for c in celdas if c["pol"]]
mm = sum(not c["ok"] for c in marc)
res["politica_revisar"] = {
    "marcadas_pct": round(100 * len(marc) / n, 1),
    "errores_atrapados_pct": round(100 * mm / mal, 1) if mal else 0,
    "exactitud_sin_revisar_pct": round(100 * (n - mal) / n, 1),
    "exactitud_tras_revision_pct": round(100 * (n - (mal - mm)) / n, 1),
}
print("\nPolítica final (campo revisar):", res["politica_revisar"])

docs = sorted({c["doc"] for c in celdas})
mitad_a = set(docs[::2])
A = [c for c in celdas if c["doc"] in mitad_a]
B = [c for c in celdas if c["doc"] not in mitad_a]
res["umbrales"] = {}
print("\nUmbrales por campo (ajustados en la mitad A, medidos en la mitad B):")
for objetivo in (60, 70, 80, 90):
    um = elegir_umbrales(A, objetivo)
    r = {"umbrales": um, "en_B": aplicar_umbrales(B, um),
         "todos_ajustados_en_todos": aplicar_umbrales(celdas, elegir_umbrales(celdas, objetivo))}
    res["umbrales"][str(objetivo)] = r
    print(f"  objetivo {objetivo}%: B -> {r['en_B']}")
    print("     LP_UMBRALES=" + ",".join(f"{k}={v}" for k, v in um.items()))

if OUT:
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("->", OUT)
