#!/bin/bash
# Procesa todos los .tif/.tiff de una carpeta y deja el resultado en un .jsonl del host.
# Los documentos que salen con error (p. ej. JSON cortado del NLP) se reintentan una vez.
#
# Uso: bash procesar_lote.sh <subcarpeta bajo DATA_HOST> <salida.jsonl> [etiqueta]
#   ej: bash procesar_lote.sh front /home/ubuntu/resultados/lote_oct.jsonl lote_oct
# Las colas deben estar vacías; con PURGAR=1 se vacían antes de empezar.
set -euo pipefail
SUB=${1:?subcarpeta bajo DATA_HOST}; OUT=${2:?salida.jsonl}; ETQ=${3:-lote}
DATA_HOST=${DATA_HOST:-/data/e3}
P=caso1v2e3e3
DIR=$(cd "$(dirname "$0")" && pwd)
LOG="${OUT%.jsonl}.log"

N=$(find "$DATA_HOST/$SUB" -maxdepth 1 -type f \( -iname '*.tif' -o -iname '*.tiff' \) | wc -l)
[ "$N" -gt 0 ] || { echo "sin .tif/.tiff en $DATA_HOST/$SUB"; exit 1; }
mkdir -p "$(dirname "$OUT")"

pend=$(docker exec $P-rabbitmq rabbitmqctl list_queues name messages 2>/dev/null \
       | awk '$1 ~ /^(ocr_input|ocr_output|nlp_output)$/ {s += $2} END {print s + 0}')
if [ "$pend" -gt 0 ]; then
  if [ "${PURGAR:-0}" = 1 ]; then
    for q in ocr_input ocr_output nlp_output; do docker exec $P-rabbitmq rabbitmqctl purge_queue $q >/dev/null; done
  else
    echo "hay $pend mensajes en cola de otra corrida; vaciar con PURGAR=1"; exit 1
  fi
fi

docker cp "$DIR/encolar.py" $P-ocr:/tmp/encolar.py
docker cp "$DIR/recolectar.py" $P-ocr:/tmp/recolectar.py

echo "=== $ETQ $(date -Is) N=$N" | tee "$LOG"
T0=$(date +%s)
docker exec $P-ocr python -u /tmp/encolar.py "/data/e3/$SUB" "" "$ETQ" | tee -a "$LOG"
docker exec $P-ocr python -u /tmp/recolectar.py "$N" /tmp/salida.jsonl | tee -a "$LOG"
docker cp $P-ocr:/tmp/salida.jsonl "$OUT"

FALTAN=$(python3 - "$OUT" "$DATA_HOST/$SUB" <<'EOF'
import json, sys
from pathlib import Path
ok = {}
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r.get("campos"):
        ok[r["doc_id"]] = 1
todos = [p.stem for p in Path(sys.argv[2]).iterdir() if p.suffix.lower() in (".tif", ".tiff")]
print(",".join(d for d in todos if d not in ok))
EOF
)
if [ -n "$FALTAN" ]; then
  K=$(echo "$FALTAN" | tr ',' '\n' | wc -l)
  echo "reintento de $K doc(s): $FALTAN" | tee -a "$LOG"
  docker exec $P-ocr python -u /tmp/encolar.py "/data/e3/$SUB" "$FALTAN" "$ETQ-reintento" | tee -a "$LOG"
  docker exec $P-ocr python -u /tmp/recolectar.py "$K" /tmp/reintento.jsonl | tee -a "$LOG"
  docker cp $P-ocr:/tmp/reintento.jsonl "${OUT%.jsonl}.reintento.jsonl"
  python3 - "$OUT" "${OUT%.jsonl}.reintento.jsonl" <<'EOF'
import json, sys
base = {}
for l in open(sys.argv[1]):
    r = json.loads(l); base[r["doc_id"]] = r
for l in open(sys.argv[2]):
    r = json.loads(l)
    if r.get("campos") or r["doc_id"] not in base:
        base[r["doc_id"]] = r
open(sys.argv[1], "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in base.values()))
EOF
fi

T1=$(date +%s); E=$((T1 - T0))
python3 - "$OUT" "$N" "$E" <<'EOF' | tee -a "$LOG"
import json, sys
rs = [json.loads(l) for l in open(sys.argv[1])]
n, e = int(sys.argv[2]), int(sys.argv[3])
err = [r["doc_id"] for r in rs if not r.get("campos")]
rev = sum(1 for r in rs for c in r.get("campos", []) if c.get("revisar"))
print(f"listos {len(rs) - len(err)}/{n} · errores {len(err)} {err if err else ''}")
print(f"campos marcados revisar: {rev}")
print(f"tiempo {e // 60} min {e % 60} s · {round(n * 3600 / max(e, 1), 1)} docs/h")
EOF
echo "=== FIN $(date -Is) -> $OUT" | tee -a "$LOG"
