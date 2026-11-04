#!/bin/bash
# Descarga NLP 7B-AWQ + VL Qwen3.6-27B-FP8 (Parte 15) en HF_HOST.
# Uso: HF_TOKEN=... bash descargar_modelos.sh
set -euo pipefail
HF_HOST=${HF_HOST:-/data/hf-cache}
IMG=vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1
mkdir -p "$HF_HOST"
for spec in \
  "Qwen/Qwen2.5-7B-Instruct-AWQ b25037543e9394b818fdfca67ab2a00ecc7dd641" \
  "Qwen/Qwen3.6-27B-FP8 e89b16ebf1988b3d6befa7de50abc2d76f26eb09"; do
  set -- $spec
  echo "== $1 @ $2"
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
    -e HF_TOKEN="${HF_TOKEN:-}" -e HF_HOME=/hf \
    -v "$HF_HOST":/hf --entrypoint hf "$IMG" \
    download "$1" --revision "$2" >/dev/null
  ls "$HF_HOST/hub/models--${1//\//--}/snapshots/$2" >/dev/null && echo "   ok"
done
du -sh "$HF_HOST"
