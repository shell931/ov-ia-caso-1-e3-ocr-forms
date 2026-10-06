#!/bin/bash
# Chequeo del stack levantado: GPUs, contenedores, modelos servidos, workers y colas.
# Uso: bash verificar.sh        (sale con código 1 si algo falla)
#      VL_MODELO=Qwen/... bash verificar.sh   si el VL no es el de por defecto
set -uo pipefail
VL=${VL_MODELO:-Qwen/Qwen2.5-VL-7B-Instruct}
NOCR=${OCR_WORKERS:-8}
DOBLE=0; case ",${COMPOSE_PROFILES:-}," in *,doble,*) DOBLE=1;; esac
SERV="rabbitmq vllm-vl vllm-nlp ocr nlp"; MODS="8001 $VL|8000 Qwen/Qwen2.5-7B-Instruct-AWQ"
if [ $DOBLE = 1 ]; then SERV="$SERV vllm-vl2 ocr2"; MODS="$MODS|8002 $VL"; NOCR=$((NOCR * 2)); fi
P=caso1v2e3e3
fallas=0
ok() { echo "  OK   $*"; }
mal() { echo "  FALLA $*"; fallas=$((fallas + 1)); }

echo "== GPUs"
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader | sed 's/^/  /'
n=$(nvidia-smi -L | wc -l); [ "$n" -ge 2 ] && ok "$n GPUs" || mal "se esperaban 2 GPUs, hay $n"

echo "== Contenedores"
for c in $SERV; do
  st=$(docker inspect -f '{{.State.Status}}' "$P-$c" 2>/dev/null || echo ausente)
  [ "$st" = running ] && ok "$P-$c" || mal "$P-$c: $st"
done

echo "== Modelos servidos"
IFS="|" read -ra PM <<< "$MODS"
for port_model in "${PM[@]}"; do
  set -- $port_model
  if curl -sf "http://localhost:$1/v1/models" | grep -q "\"$2\""; then ok ":$1 $2"
  else mal ":$1 $2 no responde (si recién arrancó, esperar ~3-5 min)"; fi
done

echo "== Workers (consumidores en RabbitMQ)"
colas=$(docker exec $P-rabbitmq rabbitmqctl list_queues name messages consumers 2>/dev/null)
o=$(echo "$colas" | awk '$1 == "ocr_input" {print $3}')
l=$(echo "$colas" | awk '$1 == "ocr_output" {print $3}')
[ "${o:-0}" = "$NOCR" ] && ok "$NOCR OCR" || mal "OCR workers: ${o:-0} (esperado $NOCR; ver docker logs $P-ocr)"
[ "${l:-0}" = 12 ] && ok "12 NLP" || mal "NLP workers: ${l:-0} (esperado 12; ver docker logs $P-nlp)"

echo "== Colas (mensajes pendientes)"
echo "$colas" | awk '$1 ~ /^(ocr_input|ocr_output|nlp_output)$/ {print "  " $1 ": " $2}'

[ $fallas -eq 0 ] && echo "== TODO OK" || echo "== $fallas falla(s)"
exit $((fallas > 0))
