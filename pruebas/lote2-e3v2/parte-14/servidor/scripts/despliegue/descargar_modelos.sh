#!/bin/bash
# Descarga los dos modelos en la revisión exacta de la Parte 14 a HF_HOST.
# Usa el CLI `hf` de la misma imagen vLLM (no hace falta Python en el host).
# Uso: HF_TOKEN=... bash descargar_modelos.sh      (token opcional; modelos públicos)
set -euo pipefail
HF_HOST=${HF_HOST:-/data/hf-cache}
IMG=vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1
mkdir -p "$HF_HOST"
for spec in \
  "Qwen/Qwen2.5-VL-7B-Instruct cc594898137f460bfe9f0759e9844b3ce807cfb5" \
  "Qwen/Qwen2.5-7B-Instruct-AWQ b25037543e9394b818fdfca67ab2a00ecc7dd641"; do
  set -- $spec
  echo "== $1 @ $2"
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
    -e HF_TOKEN="${HF_TOKEN:-}" -e HF_HOME=/hf \
    -v "$HF_HOST":/hf --entrypoint hf "$IMG" \
    download "$1" --revision "$2" >/dev/null
  ls "$HF_HOST/hub/models--${1//\//--}/snapshots/$2" >/dev/null && echo "   ok"
done
du -sh "$HF_HOST"
