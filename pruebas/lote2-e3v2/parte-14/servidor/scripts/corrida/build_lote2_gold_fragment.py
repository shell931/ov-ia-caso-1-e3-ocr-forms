#!/usr/bin/env python3
"""Fragmento del visor para el lote E3V2 con gold: KPI oficial = conf_real vs gold_e3.

Uso: python3 build_lote2_gold_fragment.py <resultados.jsonl> <lote2-gold.json>
         <lote2-gold-docs.json> <salida.json> <docs_h> "<elapsed>" ["<variante>"] ["<titulo>"]
El fragmento lleva gold por celda (PII): solo se publica dentro del vault cifrado.
"""
import json
import sys
from collections import defaultdict

SRC, AGG_P, DOCS_P, OUT, DOCS_H, ELAPSED = sys.argv[1:7]
VARIANTE = sys.argv[7] if len(sys.argv) > 7 else ""
TITULO = sys.argv[8] if len(sys.argv) > 8 else ""
DOCS_H = float(DOCS_H)
RECS = [json.loads(l) for l in open(SRC)]
AGG = json.load(open(AGG_P))
DOCS = json.load(open(DOCS_P))["docs"]

dec = defaultdict(list)
for r in RECS:
    for c in r.get("campos", []):
        if c.get("confianza") is not None:
            dec[c["etiqueta"]].append(float(c["confianza"]))
conf_campos = [{"etiqueta": et, "confianza": round(sum(v) / len(v), 1)}
               for et, v in dec.items() if v]

gold_eval = {
    "conf_real": AGG["conf_real"],
    "brecha": AGG["brecha"],
    "falsos_100": AGG["falsos_100"],
    "comparaciones": AGG["comparaciones"],
    "gold_docs": AGG["gold_docs"],
    "veredictos": AGG["veredictos"],
    "umbral_casi": AGG.get("umbral_casi", 85),
    "campos": [{"etiqueta": c["etiqueta"], "conf_declarada": c["conf_declarada"],
                "conf_real": c["conf_real"], "exacto": c.get("exacto"),
                "brecha": c["brecha"]} for c in AGG["campos"]],
}


def promedio(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


rows = []
for n, rec in enumerate(sorted(RECS, key=lambda r: str(r.get("doc_id"))), 1):
    did = str(rec.get("doc_id"))
    goldd = DOCS.get(did, {})
    campos = []
    for c in rec.get("campos", []):
        campo = {"etiqueta": c.get("etiqueta"), "valor": c.get("valor", ""),
                 "confianza": c.get("confianza", 0)}
        if c.get("revisar"):
            campo.update(revisar=True, segunda_lectura=c.get("segunda_lectura", ""))
        g = goldd.get(c.get("etiqueta"))
        if g:
            campo.update(conf_real=g.get("conf_real"), veredicto=g.get("veredicto"),
                         gold=g.get("gold", ""))
        campos.append(campo)
    ok = bool(rec.get("campos"))
    rows.append({
        "id": did, "n": n, "formulario": did,
        "estado": "listo" if ok else "error", "estado_label": "listo" if ok else "error",
        "confianza": promedio(float(c["confianza"]) for c in rec.get("campos", [])
                              if c.get("confianza") is not None),
        "conf_real": promedio(v.get("conf_real") for v in goldd.values()),
        "hora": "", "ruta": f"/data/e3/front/{did}.tif",
        "campos": campos,
    })

errores = sum(1 for r in rows if r["estado"] != "listo")
frag = {
    "titulo": TITULO or f"Lote E3V2 · Parte 10{' ' + VARIANTE if VARIANTE else ''} ({len(rows)} frentes, gold_e3)",
    "estado": "listo",
    "listo": len(rows) - errores, "jobs": len(rows), "errores": errores, "pct": 100,
    "docs_per_hour": DOCS_H, "meta": 1250, "cumple_meta": DOCS_H >= 1250,
    "elapsed_fmt": ELAPSED,
    "workers": "8 OCR + 12 NLP",
    "concurrency": 20,
    "modelos": [
        {"nombre": "Qwen/Qwen2.5-VL-7B-Instruct", "rol": "Vision / OCR + recortes",
         "donde": "GPU 0 · :8001", "vram": "~89 GB"},
        {"nombre": "Qwen/Qwen2.5-7B-Instruct-AWQ", "rol": "NLP / JSON",
         "donde": "GPU 1 · :8000", "vram": "~40 GB"},
    ],
    "conf_campos": conf_campos,
    "gold_eval": gold_eval,
    "rows": rows,
    "nota_kpi": (f"KPI oficial {AGG['conf_real']}% = promedio de conf_real por celda vs gold_e3 "
                 f"({AGG['gold_docs']} docs, {AGG['comparaciones']} celdas). "
                 + (VARIANTE if TITULO else
                    f"Pipeline Parte 10 {VARIANTE}." if VARIANTE else "Pipeline Parte 10 tal cual.")),
}
json.dump(frag, open(OUT, "w"), ensure_ascii=False)
print("rows", len(rows), "errores", errores, "kpi", AGG["conf_real"])
