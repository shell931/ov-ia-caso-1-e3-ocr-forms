# Planteamiento RTX 8000 — Dell R740xd (Turing, 2× 48 GB)

Nuevo planteamiento por cambio de infraestructura. **La Parte 15 sigue siendo
la prueba oficial** (95,7 % `conf_real`, 934 docs/h en g7e.12xlarge) y no se
modifica: ni el `docker-compose.yml` de la raíz, ni `modelos/`, ni `workers/`,
ni `backup/parte-15-servidor-fisico/`.

Esta carpeta solo agrega un compose y envs para correr el **mismo código P15**
sobre el hardware nuevo y medir cuánto se pierde/gana contra el baseline.

## Infraestructura nueva vs Parte 15

| Pieza | Parte 15 (oficial) | Planteamiento RTX 8000 |
| --- | --- | --- |
| Servidor | AWS g7e.12xlarge | Dell PowerEdge R740xd |
| CPU | 48 vCPU | 2× Xeon Gold 6248R (24C/48T c/u) |
| RAM | — | 128 GB DDR4 |
| GPU | 2× RTX PRO 6000 Blackwell, 96 GB | 2× Quadro RTX 8000, 48 GB |
| Arquitectura | Blackwell `sm_120` | **Turing `sm_75`** |
| BF16 | sí | **no** → `float16` |
| FP8 | nativo (W8A8) | **solo pesos (W8A16, FP8 Marlin)** |
| Ancho de banda memoria | ~1,8 TB/s | ~672 GB/s |

## Restricciones que obligan a cambiar

1. **VRAM a la mitad.** `Qwen3.6-27B-FP8` (rev `e89b16eb…`) pesa **30,9 GB**
   en safetensors. En la GPU1 de P15 la réplica B tenía `VL2_MEM=0.50` y el
   NLP `0.40` fijo: en 48 GB eso da 24 GB para VL2, **menos que los pesos**.
   El perfil `doble` tal cual no arranca.
2. **Sin BF16.** El `config.json` del modelo declara `"dtype": "bfloat16"`;
   en Turing hay que forzar `--dtype float16`. Riesgo: overflow numérico en
   FP16 → **hay que remedir KPI**, no asumir que se mantiene.
3. **FP8 sin cómputo nativo.** vLLM corre FP8 en `sm_75` como W8A16 Marlin
   (doc oficial de FP8 de vLLM). Funciona, pero más lento.
4. **Riesgos no confirmados** (solo se resuelven corriendo):
   - el modelo es FP8 **por bloques** (`weight_block_size`): no está
     confirmado que la variante por bloques tenga kernel en `sm_75`;
   - el modelo es **híbrido** (`mamba_ssm_dtype` en config): kernels de
     atención lineal sobre Turing sin verificar;
   - la imagen vLLM fijada por digest se usó en Blackwell: verificar que trae
     kernels para `sm_75`
     (`python -c "import torch; print(torch.cuda.get_arch_list())"` dentro
     de la imagen).

## Qué cambia en esta carpeta

`docker-compose.yml` es copia del de P15 con solo esto:

| Cambio | Por qué | Default (= P15) |
| --- | --- | --- |
| `../workers:/app` | el compose vive en esta subcarpeta | — |
| `--dtype ${VL_DTYPE}` en `vllm-vl` y `vllm-vl2` | Turing no tiene BF16 | `auto` |
| `--gpu-memory-utilization ${NLP_MEM}` en `vllm` | liberar GPU1 para VL2 | `0.40` |
| `--tensor-parallel-size ${VL_TP}` en `vllm-vl` y `vllm-vl2` | repartir el VL en T4 de 16 GB (g4dn) | `1` |
| `VL_GPUS` / `VL2_GPUS` / `NLP_GPUS` | elegir GPUs por servicio | `0` / `1` / `1` |

Mismas imágenes por digest, mismos modelos por revisión, mismo `name:` y
nombres de contenedor (los scripts de `scripts/despliegue/` siguen sirviendo).

## Envs de screening (`modelos/`)

| Env | Qué prueba | Layout |
| --- | --- | --- |
| `qwen25vl-7b-turing.env` | **Control**: código P15 + VL 7B (en g7e dio 92,3 %). Aísla el efecto del hardware | VL GPU0 · NLP GPU1 |
| `qwen36-27b-fp8-turing-simple.env` | 27B-FP8 en una réplica | VL GPU0 (0,92) · NLP GPU1 (0,40) |
| `qwen36-27b-fp8-turing-doble.env` | 27B-FP8 en dos réplicas, como P15 | VL GPU0 (0,92) · VL2 (0,72) + NLP (0,20) GPU1 |

Presupuesto GPU1 en `doble`: 0,72 × 48 ≈ 34,5 GB para VL2 (30,9 GB de pesos →
~3,5 GB para KV/activaciones, **justo**) y 0,20 × 48 ≈ 9,6 GB para el
7B-AWQ (~5,5 GB de pesos). Si VL2 no arranca, quedarse con `simple`.

`VL_SEQS` / `OCR_WORKERS` bajan de 16 a 8 por el menor KV cache; ajustar
según `nvidia-smi` y docs/h medidos.

Todos los envs definen `COMPOSE_FILE=planteamiento_rtx_8000/docker-compose.yml`,
así que se corre desde la raíz del repo con `planteamiento_rtx_8000/probar_modelo.sh`.
Es una copia de `scripts/p15/probar_modelo.sh` con un solo cambio: en la raíz,
`preds_lote2.py` y `compare_gold_real.py` están en `scripts/lote2/` (idénticos a
los de `backup/parte-15-servidor-fisico/scripts/corrida/`), y el original los
busca en `scripts/corrida/`, que en la raíz no existe.

`scripts/despliegue/descargar_modelos.sh` baja solo el 27B-FP8 y el NLP 7B-AWQ.
El VL 7B del control (`Qwen2.5-VL-7B-Instruct`) lo descarga vLLM al arrancar,
así que el servidor necesita salida a Hugging Face (o copiar ese modelo a
`/data/hf-cache` antes).

## Cómo correr (desde la raíz del repo)

```bash
# 1. control 7B (muestra 80)
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/qwen25vl-7b-turing.env p15_muestra80

# 2. 27B-FP8 una réplica (muestra 80)
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/qwen36-27b-fp8-turing-simple.env p15_muestra80

# 3. 27B-FP8 doble (muestra 80, luego full 267)
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/qwen36-27b-fp8-turing-doble.env p15_muestra80
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/qwen36-27b-fp8-turing-doble.env front
```

Comparar siempre contra P15: muestra 80 → 95,3 % / 966 docs/h (`fp8-doble`);
full 267 → **95,7 % / 934 docs/h**.

## Plan de pruebas antes del Dell (AWS)

No hay Quadro RTX 8000 en AWS. Se separa en dos validaciones:

| Instancia | Valida | No valida |
| --- | --- | --- |
| `g4dn.12xlarge` (4× T4 16 GB, `sm_75`) | misma arquitectura: kernels, FP16, FP8 Marlin, KPI en FP16 | memoria por GPU (16 GB → 27B requiere TP=4), throughput |
| `g6e.12xlarge` (4× L40S 48 GB, `sm_89`), usando 2 GPU | layout de VRAM a 48 GB (`VL_MEM`/`VL2_MEM`/`NLP_MEM`) | tiene BF16/FP8 nativos → falsos positivos de compatibilidad; throughput optimista |

El throughput real solo se mide en el R740xd.

### Validación elegida: `g4dn.metal` (8× T4 16 GB, `sm_75`)

Misma arquitectura que la RTX 8000, así que mide **compatibilidad y KPI en
FP16**; no mide docs/h ni el layout de memoria del Dell. Como cada T4 tiene
16 GB, el VL se reparte con tensor parallel (`VL_TP`) y cada servicio elige
sus GPUs (`VL_GPUS` / `VL2_GPUS` / `NLP_GPUS`; defaults = P15).

| Env | VL | NLP | Libres |
| --- | --- | --- | --- |
| `g4dn-metal-qwen25vl-7b.env` (control) | 7B FP16, TP=2, GPU 0-1 | GPU 4 (0,85) | 2, 3, 5-7 |
| `g4dn-metal-qwen36-27b-fp8.env` | 27B FP8, TP=4, GPU 0-3 | GPU 4 (0,85) | 5-7 |

TP verificado contra los `config.json`: 27B → 24 heads / 4 KV / intermediate
17408 (÷4 = 4352, múltiplo del bloque FP8 de 128); 7B → 28 heads / 4 KV (÷2).

```bash
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/g4dn-metal-qwen25vl-7b.env p15_muestra80
bash planteamiento_rtx_8000/probar_modelo.sh planteamiento_rtx_8000/modelos/g4dn-metal-qwen36-27b-fp8.env p15_muestra80
```

Comprobar al levantar: `docker exec caso1v2e3e3-vllm-vl nvidia-smi -L` debe
listar las GPUs de `VL_GPUS` (el compose pasa `"0,1,2,3"` como un solo
`device_id`; Docker lo une en `NVIDIA_VISIBLE_DEVICES`). Las T4 no tienen
NVLink: TP va por PCIe, más lento, sin efecto en el KPI salvo décimas por el
orden de las sumas.

## Plan B si el 27B-FP8 no corre o degrada en Turing

- 27B en AWQ/GPTQ int4 (soportado en `sm_75`), más VRAM libre para KV.
- Volver a candidatos del screening P15 que entren en 48 GB.
- Medir siempre en `p15_muestra80` con el mismo gold, igual que P15.

## Qué no hacer

- **No** modificar el compose raíz ni `modelos/` de P15: son el baseline.
- **No** activar `LEER_CONTACTO` / `LEER_APELLIDO` (mismo hallazgo P15).
- **No** subir preds/jsonl/gold con PII a git.
