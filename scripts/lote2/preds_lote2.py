"""jsonl de la corrida -> preds.json para compare_gold_real.py (id = doc_id, estado = listo).

Uso: python3 preds_lote2.py [resultados.jsonl] [preds.json]
"""
import json
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "/data/e3/resultados_lote2_parte10.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/data/e3/preds_lote2.json"
seen = {}
for l in open(SRC):
    r = json.loads(l)
    d = str(r["doc_id"])
    seen[d] = {"doc_id": d, "id": d, "estado": "listo" if r.get("campos") else "error",
               "campos": r.get("campos", [])}
json.dump(list(seen.values()), open(OUT, "w"), ensure_ascii=False)
print("preds", len(seen))
