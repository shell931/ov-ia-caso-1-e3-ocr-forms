#!/usr/bin/env python3
"""Fragmento del visor para el lote E3V2 (sin gold): confianza declarada por campo."""
import json
import sys
from collections import defaultdict

SRC, OUT, DOCS_H, ELAPSED = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
RECS = [json.loads(l) for l in open(SRC)]

dec = defaultdict(list)
vacios = defaultdict(int)
for r in RECS:
    for c in r.get("campos", []):
        if c.get("confianza") is not None:
            dec[c["etiqueta"]].append(float(c["confianza"]))
        if not str(c.get("valor") or "").strip():
            vacios[c["etiqueta"]] += 1

conf_campos = [{"etiqueta": et, "confianza": round(sum(v) / len(v), 1)}
               for et, v in dec.items() if v]


def doc_dec(rec):
    vals = [float(c["confianza"]) for c in rec.get("campos", []) if c.get("confianza") is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


rows = []
for n, rec in enumerate(sorted(RECS, key=lambda r: str(r.get("doc_id"))), 1):
    did = str(rec.get("doc_id"))
    rows.append({
        "id": did, "n": n, "formulario": did,
        "estado": "listo" if rec.get("campos") else "error",
        "estado_label": "listo" if rec.get("campos") else "error",
        "confianza": doc_dec(rec), "hora": "",
        "ruta": f"/data/e3/front/{did}.tif",
        "campos": [{"etiqueta": c.get("etiqueta"), "valor": c.get("valor", ""),
                    "confianza": c.get("confianza", 0)} for c in rec.get("campos", [])],
    })

errores = sum(1 for r in rows if r["estado"] != "listo")
frag = {
    "titulo": f"Lote E3V2 · Parte 10 ({len(rows)} frentes, sin gold)",
    "estado": "listo",
    "listo": len(rows) - errores, "jobs": len(rows), "errores": errores, "pct": 100,
    "docs_per_hour": DOCS_H, "meta": 1250, "cumple_meta": DOCS_H >= 1250,
    "elapsed_fmt": ELAPSED,
    "conf_campos": conf_campos,
    "vacios_por_campo": dict(vacios),
    "rows": rows,
    "nota_kpi": ("Pipeline Parte 10 tal cual sobre el lote nuevo E3V2 (front 300 dpi, S3 forme3/E3V2). "
                 "Sin gold: la confianza mostrada es la declarada por el extractor, no conf_real."),
}
json.dump(frag, open(OUT, "w"), ensure_ascii=False)
print("rows", len(rows), "errores", errores, "docs/h", DOCS_H)
print("vacios:", {k: v for k, v in sorted(vacios.items(), key=lambda x: -x[1])})
