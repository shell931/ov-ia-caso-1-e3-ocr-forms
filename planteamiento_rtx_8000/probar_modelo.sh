#!/usr/bin/env bash
# Cambia el modelo VL (GPU0), corre una carpeta y compara contra el gold.
# Copia de scripts/p15/probar_modelo.sh para el planteamiento RTX 8000: en la raíz del
# repo compare_gold_real.py y preds_lote2.py están en scripts/lote2/ (idénticos a
# backup/parte-15-servidor-fisico/scripts/corrida/), no en scripts/corrida/.
# Uso (desde la raíz del repo): bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/<env> p15_muestra80 [gold.json]
# Deja: ~/e3/p15/res/<modelo>_<carpeta>.{jsonl,log}, preds y comparación.
set -euo pipefail
ENVF=$1
CARPETA=$2
GOLD=${3:-/data/e3/gold/gold_lote2.json}
TAG="$(basename "$ENVF" .env)_${CARPETA}"
RES=${RES:-$HOME/e3/p15/res}
mkdir -p "$RES"
set -a; . "$ENVF"; set +a

case ",${COMPOSE_PROFILES:-}," in
  *,doble,*) SERV="vllm-vl vllm-vl2 ocr ocr2 nlp" ;;
  *) SERV="vllm-vl ocr nlp"; docker rm -f caso1v2e3e3-vllm-vl2 caso1v2e3e3-ocr2 >/dev/null 2>&1 || true ;;
esac
LP_GUARDAR=1 docker compose --env-file "$ENVF" up -d --force-recreate $SERV
for i in $(seq 1 80); do
  if bash scripts/despliegue/verificar.sh > "$RES/$TAG.verificar" 2>&1; then break; fi
  sleep 15
done
grep -q "TODO OK" "$RES/$TAG.verificar" || { echo "no arrancó, ver $RES/$TAG.verificar"; exit 1; }
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader > "$RES/$TAG.gpu"

# lo que quede en cola es de la corrida anterior (otro modelo)
PURGAR=1 bash scripts/despliegue/procesar_lote.sh "$CARPETA" "$RES/$TAG.jsonl" "$TAG"
python3 scripts/lote2/preds_lote2.py "$RES/$TAG.jsonl" "$RES/$TAG.preds.json"
python3 scripts/lote2/compare_gold_real.py "$GOLD" "$RES/$TAG.preds.json" "" "$TAG" > "$RES/$TAG.kpi.txt" 2>&1 || true
python3 scripts/p15/eval_confianza.py "$RES/$TAG.jsonl" "$GOLD" "$RES/$TAG.lp.json" > "$RES/$TAG.lp.txt" 2>&1 || true
tail -4 "$RES/$TAG.kpi.txt"
