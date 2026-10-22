#!/usr/bin/env bash
# Tarea B4 · Datos, gold, imagen y pesos para correr el stack E3 en Turing.
# Validado en AWS g4dn.metal (2026-10-21). Se puede correr más de una vez.
#
# Uso (desde la raíz del repo, después de instalar_servidor.sh):
#   GOLD_CSV=/ruta/gold_e3.csv bash planteamiento_rtx_8000/preparar_datos.sh
#
# Variables (con sus defaults):
#   GOLD_CSV   CSV del gold (gold_e3_obtenido-con-fable.csv). Obligatorio la
#              primera vez; tiene PII: copiarlo al servidor por scp, nunca a git.
#   S3_SRC     s3://forme3/E3V2/front_300/
#   DATA_HOST  /data/e3          HF_HOST  /data/hf-cache
#   CONTROL=1  baja también Qwen2.5-VL-7B (control de la Parte 16b)
#   HF_TOKEN   opcional; sin él Hugging Face limita la velocidad
set -euo pipefail
# con pipefail, "cmd | grep -q" puede fallar por SIGPIPE si grep corta antes: usar grep -c

S3_SRC=${S3_SRC:-s3://forme3/E3V2/front_300/}
DATA_HOST=${DATA_HOST:-/data/e3}
HF_HOST=${HF_HOST:-/data/hf-cache}
CONTROL=${CONTROL:-0}
PREFIJO='000000010010101;'   # los TIFF de S3 lo traen; el gold y el pipeline usan solo el número
IMG=$(grep -m1 -o 'vllm/vllm-openai@sha256:[0-9a-f]*' planteamiento_rtx_8000/docker-compose.yml)
ok()  { echo "  ok    $*"; }
mal() { echo "  ERROR $*" >&2; exit 1; }

[ -f planteamiento_rtx_8000/docker-compose.yml ] || mal "correr desde la raíz del repo"
docker info >/dev/null 2>&1 || mal "docker no responde para $USER (¿instalar_servidor.sh? ¿volver a entrar por SSH?)"

echo "== Carpetas"
sudo mkdir -p "$DATA_HOST/front" "$DATA_HOST/s3_front_300" "$DATA_HOST/gold" "$HF_HOST"
sudo chown -R "$USER:$USER" "$DATA_HOST" "$HF_HOST"
chmod 700 "$DATA_HOST/gold"
ok "$DATA_HOST · $HF_HOST"

echo "== Formularios desde $S3_SRC"
aws s3 sync --only-show-errors "$S3_SRC" "$DATA_HOST/s3_front_300/"
# copia con el nombre corto (6000000030.tif); doc_id = nombre del archivo, y
# nlp_worker completa formulario_no con sus dígitos: con el prefijo el KPI cae ~4 pp
n=0
for f in "$DATA_HOST"/s3_front_300/*.tif; do
  b=$(basename "$f"); d="$DATA_HOST/front/${b#"$PREFIJO"}"; [ -e "$d" ] || cp "$f" "$d"; n=$((n + 1))
done
ok "$n en S3 · $(ls "$DATA_HOST/front" | wc -l) en $DATA_HOST/front (sin prefijo)"
ls "$DATA_HOST/front" | grep -c ';' >/dev/null && mal "quedaron archivos con ';' en $DATA_HOST/front"

echo "== Gold"
if [ -n "${GOLD_CSV:-}" ]; then
  install -m 600 "$GOLD_CSV" "$DATA_HOST/gold/gold_e3.csv"
  python3 scripts/lote2/gold_csv_to_json.py "$DATA_HOST/gold/gold_e3.csv" "$DATA_HOST/gold/gold_lote2.json"
  chmod 600 "$DATA_HOST/gold/gold_lote2.json"
fi
[ -f "$DATA_HOST/gold/gold_lote2.json" ] || mal "falta el gold: pasar GOLD_CSV=/ruta/al.csv"
python3 - "$DATA_HOST" <<'PY'
import json, pathlib, sys
d = pathlib.Path(sys.argv[1])
gold = {str(r["id"]) for r in json.load(open(d / "gold/gold_lote2.json"))}
tif = {p.stem for p in (d / "front").glob("*.tif")}
print(f"  ok    gold {len(gold)} docs · TIFF {len(tif)} · coinciden {len(gold & tif)}")
if gold - tif: sys.exit(f"  ERROR {len(gold - tif)} ids del gold sin TIFF (ej. {sorted(gold - tif)[:3]})")
PY

echo "== Imagen vLLM"
docker image inspect "$IMG" >/dev/null 2>&1 || docker pull -q "$IMG" >/dev/null
docker run --rm --entrypoint python3 "$IMG" -c \
  "import torch, vllm; a = torch.cuda.get_arch_list(); print('  ok    vllm', vllm.__version__, '· torch', torch.__version__, '·', a); assert 'sm_75' in a, 'sin kernels para Turing (sm_75)'"

echo "== Imagen de los workers (dependencias preinstaladas: arrancan sin red)"
docker compose -f planteamiento_rtx_8000/docker-compose.yml build -q ocr
ok "$(docker image inspect e3-workers:p16 --format 'e3-workers:p16 · {{.Size}} bytes')"

echo "== Pesos en $HF_HOST"
HF_HOST=$HF_HOST bash scripts/despliegue/descargar_modelos.sh 2>&1 | grep -E '^==|ok|G\s'
if [ "$CONTROL" = 1 ]; then
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e HF_TOKEN="${HF_TOKEN:-}" -e HF_HOME=/hf \
    -v "$HF_HOST":/hf --entrypoint hf "$IMG" \
    download Qwen/Qwen2.5-VL-7B-Instruct --revision cc594898137f460bfe9f0759e9844b3ce807cfb5 >/dev/null 2>&1
  ok "Qwen2.5-VL-7B (control)"
fi
ok "cache: $(du -sh "$HF_HOST" | cut -f1)"

echo
echo ">> Datos listos. Siguiente (B4.5): levantar con el env elegido y verificar, ver DESPLIEGUE_DELL.md."
