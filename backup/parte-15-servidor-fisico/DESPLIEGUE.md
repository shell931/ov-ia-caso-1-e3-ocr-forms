# Despliegue en servidor real — Parte 15

Guía para levantar el pipeline de la Parte 15 en un servidor con **dos GPU
de 96 GB** (NVIDIA RTX PRO 6000 Blackwell). Reproduce el KPI medido
(**95,7 %** `conf_real` vs gold, **934 docs/h**) con
`Qwen/Qwen3.6-27B-FP8` en perfil dual + NLP 7B-AWQ + logprobs.

La Parte 14 sigue disponible en `backup/parte-14-servidor-fisico/` (7B,
92,4 %).

## 1. Requisitos del host

Igual que Parte 14, más disco para el FP8:

| Componente | Parte 15 |
| --- | --- |
| GPUs | 2× 96 GB; GPU0 ~90 GB (VL), GPU1 ~40 GB NLP + ~50 GB VL2 |
| Disco HF | ~291 GB de cache de screening; mínimo ~60 GB si solo bajas FP8 + 7B-AWQ |
| Resto | Docker + nvidia-container-toolkit, Ubuntu, salida a HF/PyPI en el 1.er arranque |

```bash
nvidia-smi
docker info | grep -i runtimes   # debe incluir nvidia
```

## 2. Copiar el código

```bash
git clone https://github.com/shell931/ov-ia-caso-1-e3-ocr-forms.git
mkdir -p ~/e3 && cp -r ov-ia-caso-1-e3-ocr-forms/backup/parte-15-servidor-fisico ~/e3/
cd ~/e3/parte-15-servidor-fisico
grep -E '^[0-9a-f]{32}  ' MANIFEST.md | md5sum -c --quiet && echo MANIFEST OK
```

## 3. Carpetas de datos

```bash
sudo mkdir -p /data/e3/front /data/hf-cache
sudo chown -R $USER /data/e3 /data/hf-cache
# copiar los 267 TIFF a /data/e3/front y el gold a /data/e3/gold/gold_lote2.json
```

## 4. Descargar modelos

```bash
# NLP 7B-AWQ + VL FP8 (revisión fijada)
bash scripts/despliegue/descargar_modelos.sh
```

Por defecto baja:

- `Qwen/Qwen2.5-7B-Instruct-AWQ@b2503754…`
- `Qwen/Qwen3.6-27B-FP8@e89b16eb…`

Para repetir el screening de otros VL, añadir revisiones a mano en
`/data/hf-cache` (ver `modelos/*.env`).

## 5. Levantar (perfil dual)

```bash
set -a; . modelos/qwen36-27b-fp8-doble.env; set +a
docker compose --env-file modelos/qwen36-27b-fp8-doble.env --profile doble up -d
# esperar 3–5 min a que los VL carguen
VL_MODELO=Qwen/Qwen3.6-27B-FP8 COMPOSE_PROFILES=doble OCR_WORKERS=16 \
  bash scripts/despliegue/verificar.sh
```

Servicios esperados: `rabbitmq`, `vllm` (:8000 NLP), `vllm-vl` (:8001),
`vllm-vl2` (:8002), `ocr`, `ocr2`, `nlp`. Consumidores: **32 OCR + 12 NLP**.

## 6. Procesar un lote

```bash
# atajo medido (recreate + KPI + confianza)
bash scripts/p15/probar_modelo.sh modelos/qwen36-27b-fp8-doble.env front

# o manual:
PURGAR=1 bash scripts/despliegue/procesar_lote.sh front /tmp/salida.jsonl p15
python3 scripts/corrida/preds_lote2.py /tmp/salida.jsonl /tmp/preds.json
python3 scripts/corrida/compare_gold_real.py \
  /data/e3/gold/gold_lote2.json /tmp/preds.json "" p15
```

Aceptación: `TOTAL` ≥ **95 %** conf_real, 0 errores, ~900+ docs/h,
`verificar.sh` en verde.

## 7. Confianza / revisar

```bash
python3 scripts/p15/eval_confianza.py /tmp/salida.jsonl \
  /data/e3/gold/gold_lote2.json --recalcular | head -40
```

Con `LP_UMBRAL=80` (~22 % celdas) se atrapa ~79 % de errores y la exactitud
tras revisar las marcadas ronda **97 %**.

## 8. Volver a Parte 14 (7B)

```bash
docker compose --profile doble down
# desde el backup de Parte 14, sin profile doble:
cd ~/e3/parte-14-servidor-fisico && docker compose up -d
```

## 9. Seguridad / offline

Igual que Parte 14: RabbitMQ guest abierto, workers con `pip install` al
arranque. Para aire-gapeado, precalentar imágenes y wheelhouse; no subir
preds/jsonl con PII a git.

## 10. Troubleshooting

| Síntoma | Qué mirar |
| --- | --- |
| `vllm-vl2` OOM | bajar `VL2_MEM` o apagar profile `doble` |
| OCR ≠ 32 | `COMPOSE_PROFILES=doble` y `OCR_WORKERS=16` en el env |
| KPI ~92 % | estás en 7B; comprobar `curl :8001/v1/models` |
| Email peor | `LEER_CONTACTO` debe ser `0` |
| Root sin espacio | pesos solo en `/data/hf-cache`, nunca en `/` |
