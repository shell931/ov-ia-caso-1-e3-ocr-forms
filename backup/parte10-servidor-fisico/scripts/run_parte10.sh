#!/usr/bin/env bash
# Repite la corrida Parte 10 (100 docs) asumiendo stack ya arriba.
# Uso, desde esta carpeta:
#   ./scripts/run_parte10.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== purge =="
docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue ocr_input
docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue ocr_output
docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue nlp_output

echo "== copy enqueue/consume into OCR container =="
docker cp scripts/enqueue_parte10.py caso1v2e3e3-ocr:/app/enqueue_parte10.py
docker cp scripts/consume_parte10.py caso1v2e3e3-ocr:/app/consume_parte10.py
rm -f workers/_resultados_parte10.jsonl

echo "== consume background =="
docker exec -d caso1v2e3e3-ocr python /app/consume_parte10.py
sleep 2
echo "== enqueue 100 =="
docker exec caso1v2e3e3-ocr python /app/enqueue_parte10.py

echo "Esperando workers/_resultados_parte10.jsonl con 100 líneas…"
for i in $(seq 1 120); do
  n=$(wc -l < workers/_resultados_parte10.jsonl 2>/dev/null || echo 0)
  echo "  t=${i}m líneas=$n"
  if [ "${n:-0}" -ge 100 ]; then break; fi
  sleep 60
done

cp workers/_resultados_parte10.jsonl /data/e3/resultados_parte10.jsonl
python3 - << 'PY'
import json
rows = []
for line in open("/data/e3/resultados_parte10.jsonl"):
    r = json.loads(line)
    r["id"] = r.get("id") or r.get("doc_id")
    r["estado"] = r.get("estado") or "listo"
    rows.append(r)
by = {r["id"]: r for r in rows}
json.dump(list(by.values()), open("/data/e3/preds_parte10.json", "w"),
          ensure_ascii=False, indent=2)
print("preds", len(by))
PY

python3 scripts/compare_gold_real.py \
  /data/e3/gold/gold.json /data/e3/preds_parte10.json "" parte10
python3 scripts/compare_gold_real.py \
  /data/e3/gold/gold_v2.json /data/e3/preds_parte10.json "" parte10v2

echo "Listo. Mira conf_real en /data/e3/parte10v2-gold.json (KPI) y parte10-gold.json."
