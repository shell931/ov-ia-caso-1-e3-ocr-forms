# Backup Parte 10 — reinstalar tal cual en un servidor físico

Esta carpeta es **independiente** de `backup/parte8-servidor-fisico/`.
Es la copia exacta del pipeline que midió y publicó **Parte 10**
(25 sep 2026):

| Métrica | Valor |
| --- | ---: |
| Contra `gold_v2` (**KPI oficial**) | **89,6 %** |
| Contra `gold.json` (original) | **88,4 %** |
| `numero_documento` | **88 %** |
| `telefono_movil` (gold / gold_v2) | 40 % / 58 % |
| `tipo_discapacidad` | 91 % |

Visor: https://shell931.github.io/e3-pages/ — menú **Parte 10**.
Detalle de diseño: `IMPLEMENTACION.md` en esta carpeta y
`docs/parte10-resultados.md` en la raíz del repo.

No trae las imágenes TIFF ni el gold (datos personales). Hay que
copiarlos aparte **mientras el servidor AWS siga encendido** (paso 1).

## Qué hay aquí

| Ruta | Qué es |
| --- | --- |
| `IMPLEMENTACION.md` | Documentación completa de Parte 10: módulo, flags, reglas, calibración, qué no se tocó. |
| `LEEME.md` | Este archivo: cómo desplegar y repetir la corrida. |
| `workers/` | Python exactos del servidor AWS el día de la medición (incluye `digitos_vision.py`, regla NINGUNA, dirección, etc.). |
| `docker-compose.yml` | RabbitMQ + vLLM VL (GPU 0) + vLLM NLP (GPU 1) + 8 OCR + 12 NLP. Imagen vLLM fijada al digest `sha256:c29147676055…`. |
| `scripts/` | Carga, consumo, comparación oficial, enqueue/consume Parte 10, fragmento del visor. |
| `kpis/parte10-gold.json` | Agregado vs gold original (**sin PII**). |
| `kpis/parte10v2-gold.json` | Agregado vs gold_v2 (**sin PII**) — el del KPI. |
| `gold_v2_resumen.json` | Ids de teléfonos confirmados en gold_v2, **sin** los números. |

## Hardware de la corrida publicada

Dos NVIDIA RTX PRO 6000 Blackwell, 97.887 MiB cada una. Driver 595.84.
Docker 29.1.3, Compose 2.40.3.

vLLM reserva el **90 %** de la GPU 0 para el VL y el **40 %** de la GPU 1
para el NLP. Esas dos reservas **no caben en una sola** tarjeta de 96 GB.
Un servidor físico con dos GPU de esa clase puede usar este
`docker-compose.yml` tal cual. Con tarjetas más chicas hay que bajar
`--gpu-memory-utilization` y `--max-model-len` antes de arrancar.

Modelos (no van en git; se descargan a `/data/hf-cache`):

- Visión: `Qwen/Qwen2.5-VL-7B-Instruct` (~15,5 GiB)
- NLP: `Qwen/Qwen2.5-7B-Instruct-AWQ` (~5,2 GiB)

**No se cuantizó el VL** en Parte 10: no había VRAM libre para un segundo
modelo; se reutiliza el 7B sobre recortes.

## Flags tal cual la corrida

| Variable | Default Parte 10 |
| --- | --- |
| `LEER_DIGITOS` | **1** (nuevo) |
| `LEER_CASILLAS` | 1 |
| `LEER_DIRECCION` | 1 |
| `VOTE_NUMERIC` | 1 |
| `BACKFILL_FORMULARIO` | 1 |
| `LEER_CONTACTO` | **0** |
| `LEER_APELLIDO` | **0** |
| `DIGITOS_ESCALA` | **2** |

Recortes de cédula (defaults en `digitos_vision.py`):
`CED_X0=0.02 CED_Y0=0.330 CED_X1=0.55 CED_Y1=0.410`.

## 1. Copiar imágenes y gold, ahora

Desde una máquina con la llave SSH del servidor AWS actual:

```bash
export SSH_KEY="$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem"
export DEST="/ruta/del/disco/e3"   # backup de datos (NO subir a git)
mkdir -p "$DEST/front" "$DEST/gold"
rsync -av -e "ssh -i $SSH_KEY" \
  ubuntu@3.17.139.133:/data/e3/front/ "$DEST/front/"
rsync -av -e "ssh -i $SSH_KEY" \
  ubuntu@3.17.139.133:/data/e3/gold/gold.json \
  ubuntu@3.17.139.133:/data/e3/gold/gold_v2.json \
  ubuntu@3.17.139.133:/data/e3/gold/gold_v2_cambios.json \
  "$DEST/gold/"
```

Son 100 TIFF de frente (`6000000001`–`6000000101` excepto `6000000033`),
más `gold.json` y `gold_v2.json`.

## 2. Preparar el servidor físico

Ubuntu con **dos** GPU visibles en `nvidia-smi`. Instala Docker y el
NVIDIA Container Toolkit. Comprueba:

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

```bash
sudo mkdir -p /data/e3/front /data/e3/gold /data/hf-cache
sudo chown -R "$USER" /data/e3 /data/hf-cache
cp -a "$DEST/front/." /data/e3/front/
cp -a "$DEST/gold/." /data/e3/gold/
```

El primer arranque descarga los modelos a `/data/hf-cache` (hace falta
salida a `huggingface.co`).

## 3. Levantar el stack

En esta carpeta (`backup/parte10-servidor-fisico`):

```bash
docker compose up -d
docker compose logs -f vllm-vl vllm
```

Espera a que ambos vLLM digan que la app arrancó. Luego:

```bash
docker compose ps
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv
```

GPU 0 = VL, GPU 1 = NLP, memoria reservada desde el arranque.

Los workers OCR/NLP instalan `pika`, `openai` y `pillow` al arrancar
(`workers/requirements.txt`) y dejan 8 y 12 procesos dentro de cada
contenedor.

## 4. Correr los 100 (Parte 10)

Purga colas, encola 100, consume a JSONL (vía contenedor OCR, que ya
tiene `pika` y monta `/data/e3` y `./workers`):

```bash
docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue ocr_input
docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue ocr_output
docker exec caso1v2e3e3-rabbitmq rabbitmqctl purge_queue nlp_output

# Los scripts viven en ./scripts; cópialos al volume workers o ejecuta así:
docker cp scripts/enqueue_parte10.py caso1v2e3e3-ocr:/app/enqueue_parte10.py
docker cp scripts/consume_parte10.py caso1v2e3e3-ocr:/app/consume_parte10.py

# Consumir en background y luego encolar
docker exec -d caso1v2e3e3-ocr python /app/consume_parte10.py
docker exec caso1v2e3e3-ocr python /app/enqueue_parte10.py
```

`consume_parte10.py` escribe en el volume montado:
`workers/_resultados_parte10.jsonl` → muévelo a `/data/e3/`:

```bash
cp workers/_resultados_parte10.jsonl /data/e3/resultados_parte10.jsonl

python3 - << 'PY'
import json
rows = []
for line in open("/data/e3/resultados_parte10.jsonl"):
    r = json.loads(line)
    r["id"] = r.get("id") or r.get("doc_id")
    r["estado"] = r.get("estado") or "listo"
    rows.append(r)
by = {r["id"]: r for r in rows}
json.dump(list(by.values()), open("/data/e3/preds_parte10.json", "w"),
          ensure_ascii=False, indent=2)
print(len(by))
PY

python3 scripts/compare_gold_real.py \
  /data/e3/gold/gold.json /data/e3/preds_parte10.json "" parte10
python3 scripts/compare_gold_real.py \
  /data/e3/gold/gold_v2.json /data/e3/preds_parte10.json "" parte10v2
```

El número oficial de Parte 10 es `conf_real` de `parte10v2-gold.json`
(**89,6** en la corrida publicada). El de `parte10-gold.json` es la
misma corrida contra el gold original (**88,4**).

Las salidas con texto de cada campo son datos personales: no las subas
a git.

## 5. Comprobar que es el mismo pipeline

```bash
docker logs caso1v2e3e3-vllm-vl 2>&1 \
  | grep -E "model_tag|Checkpoint size|Model loading took" | head -4
docker logs caso1v2e3e3-ocr 2>&1 | grep -E "LEER_DIGITOS|Worker listo|digitos" | head
docker exec caso1v2e3e3-ocr python -c "from digitos_vision import ESCALA, REGIONES; print(ESCALA, REGIONES['numero_documento'])"
```

Esperado: `ESCALA 2` y caja `(0.02, 0.33, 0.55, 0.41)`.

Rabbit de este compose usa `guest`/`guest` y publica 5672/15672. En un
servidor expuesto a red, cambia usuario y contraseña antes de levantarlo.

## Relación con el backup de Parte 8

`backup/parte8-servidor-fisico/` documenta Parte 8 (+ notas 9/10).
**Esta carpeta** es el paquete autocontenido para repetir **solo** el
estado Parte 10. No mezcles workers entre carpetas si quieres números
reproducibles.
