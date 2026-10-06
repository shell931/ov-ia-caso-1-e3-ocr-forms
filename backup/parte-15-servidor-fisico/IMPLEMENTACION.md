# Parte 15 — implementación

## Objetivo

Subir el KPI del Lote E3V2 (21 campos, 267 frentes) por encima del 92,4 %
de la Parte 14 **sin fine-tuning**, midiendo tres cambios por separado y
dejando una configuración reproducible.

## Cableado nuevo

### `workers/confianza_lp.py`

- `ClienteLP`: pide `logprobs` a vLLM en cada lectura VL y calcula
  `conf_lp` = mínimo de las probs de los caracteres del valor emitido
  (0–100).
- `anotar_confianza(campos, lecturas)`: escribe `conf_lp` y, si
  `LP_MARCAR=1` y `conf_lp < umbral`, pone `revisar=True` y
  `revisar_por=["conf_lp"]`.
- Umbral: `LP_UMBRAL` (único) o `LP_UMBRALES=campo=N,...`.
- Casillas: `LP_CASILLA_MODO=elegida` (mejor AUC que `min` en 7B).

### `workers/ocr_worker.py` / `nlp_worker.py`

- OCR envuelve las lecturas con `ClienteLP` cuando `LEER_LOGPROBS=1`.
- NLP llama `anotar_confianza` al final (también marca casillas dudosas).

### `workers/direccion_vision.py`

- `normalizar_formato()` detrás de `DIR_NORMALIZAR=1` (default):
  1. espacios alrededor de `-` → `-`
  2. `N°` / `Nº` → `N`
  3. quitar punto final
  4. colapsar espacios
- **No** expandir `CL`/`CRA`/…: el gold es literal y esa expansión baja
  exactos. `No.`→`N` también empeora (gold mixto).

### Compose

- Variables `VL_MODELO`, `VL_REV`, `VL_MEM`, `VL_EAGER`, `VL_SEQS`,
  `OCR_WORKERS`, flags LP/DIR.
- Profile `doble`: servicio `vllm-vl2` (GPU1, `VL2_MEM`) + `ocr2`.
- NLP sigue en GPU1 con mem 0.40; VL2 usa el resto (`0.50`).

## Scripts P15

| Script | Uso |
| --- | --- |
| `scripts/p15/probar_modelo.sh ENV CARPETA [GOLD]` | Recreate VL/OCR, verificar, procesar, KPI, eval confianza |
| `scripts/p15/eval_confianza.py jsonl gold [--recalcular]` | AUC, umbrales, política `revisar` |
| `scripts/p15/comparar_modelos.py` | Tabla screening → `comparativa80*.json` |

## Screening y elección

Muestra `/data/e3/p15_muestra80` (80 docs, `seed=15`). Baseline 7B en
muestra: 91,2 %. Qwen3.6-27B (bf16) 95,5 %; FP8 casi igual y más rápido;
dual FP8 **95,3 % @ 966 docs/h**. Full 267 con esa config: **95,7 % @
934 docs/h**.

`LEER_CONTACTO`/`LEER_APELLIDO` en dual empeoran email → quedan en `0`.

## Política de revisión (full)

| Umbral único | % celdas | % errores atrapados | exacto tras revisar |
| --- | ---: | ---: | ---: |
| 70 | 16,5 | 70,5 | 96,2 |
| **80** (elegido) | **21,7** | **78,7** | **97,2** |
| 90 | 29,7 | 87,6 | 98,4 |

AUC `conf_lp` 92,0 vs declarada 47,8. La confianza del extractor no sirve
para filtrar; la de logprobs sí.

## Cómo repetir la medición

```bash
cd ~/e3/parte-15-servidor-fisico   # o backup descomprimido
set -a; . modelos/qwen36-27b-fp8-doble.env; set +a
docker compose --env-file modelos/qwen36-27b-fp8-doble.env --profile doble up -d
bash scripts/despliegue/verificar.sh
bash scripts/p15/probar_modelo.sh modelos/qwen36-27b-fp8-doble.env front
grep TOTAL ~/e3/p15/res/qwen36-27b-fp8-doble_front.kpi.txt
```

Gold: `/data/e3/gold/gold_lote2.json` (PII, solo servidor).
