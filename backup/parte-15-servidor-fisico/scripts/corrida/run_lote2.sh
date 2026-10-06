#!/bin/bash
set -euo pipefail
OUT=${1:-/data/e3/resultados_lote2_parte10.jsonl}
LOG=${2:-/tmp/lote2_run_$(date +%s).log}
N=$(ls /data/e3/front/*.tif | wc -l)
echo "=== Lote E3V2 Parte 10 $(date -Is) N=$N ===" | tee $LOG
for q in ocr_input ocr_output nlp_output; do docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue $q >/dev/null; done
T0=$(date +%s)
docker exec caso1v2e3e3-ocr python /tmp/l2_enqueue.py all | tee -a $LOG
docker exec caso1v2e3e3-ocr python /tmp/l2_consume.py $N /tmp/resultados_lote2.jsonl | tee -a $LOG
T1=$(date +%s); E=$((T1-T0))
echo "wall_clock_s=$E docs_per_hour=$(python3 -c "print(round($N*3600/$E,1))")" | tee -a $LOG
docker cp caso1v2e3e3-ocr:/tmp/resultados_lote2.jsonl "$OUT"
echo "=== DONE $(date -Is) ===" | tee -a $LOG
