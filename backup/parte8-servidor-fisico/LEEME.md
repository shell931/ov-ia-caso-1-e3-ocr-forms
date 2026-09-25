# Backup Parte 8 / Parte 9 / Parte 10 — reinstalar en un servidor físico

Esta carpeta es la copia para levantar **el mismo pipeline** que midió
Parte 8 (87,8 %), Parte 9 (88,9 % vs gold_v2) y Parte 10 (89,6 % vs
gold_v2). No trae las imágenes ni el gold: son datos personales y hay
que copiarlos aparte, con el script de abajo, mientras el servidor de
AWS siga encendido.

- Parte 8 (modelos, recortes, fórmula): `docs/parte8-resultados.md`
- Parte 9 (gold_v2 teléfonos + regla NINGUNA): **`PARTE9.md`** en esta
  carpeta y `docs/parte9-resultados.md` en la raíz del repo.
- Parte 10 (lector de dígitos cédula + celular): **`PARTE10.md`** en
  esta carpeta y `docs/parte10-resultados.md` en la raíz del repo.

## Qué hay aquí

| Ruta | Qué es |
| --- | --- |
| `workers/` | Los Python que leen el formulario (incluye la regla NINGUNA de Parte 9 en `casillas_vision.py`). |
| `PARTE9.md` | Qué cambió en Parte 9, números, ejemplo de discapacidad, cómo copiar `gold_v2`. |
| `gold_v2_resumen.json` | Ids de teléfonos confirmados en gold_v2, **sin** los números (PII). |
| `docker-compose.yml` | RabbitMQ + vLLM visión (GPU 0) + vLLM NLP (GPU 1) + 8 workers OCR + 12 workers NLP. La imagen de vLLM está fijada al digest que corrió en AWS el 24 sep 2026. |
| `scripts/load_test_simple.py` | Mete hasta 100 TIFF `6*.tif` en la cola `ocr_input`. |
| `scripts/consume_results.py` | Saca la cola `nlp_output` a un JSONL. |
| `scripts/compare_gold_real.py` | La fórmula oficial: promedio de celda. |
| `scripts/build_parte8_fragment.py` | Arma el JSON del visor. Escribe datos personales en `/data/e3/`. |
| `scripts/add_parte8.py` y `publicar_parte8.sh` | Publican el visor. No hace falta para que el OCR funcione. `publicar_parte8.sh` reescribe el menú de Parte 8 con un texto viejo; no lo corras sobre el visor actual. |

`workers/postprocess_express.py` de esta carpeta es el del servidor que
midió la Parte 8. Incluye el paso de fechas a `DD/MM/YYYY` y el mapa
`CC` → `CEDULA_CIUDADANIA`. Esa versión también quedó copiada en
`workers/postprocess_express.py` de la raíz del repo.

`workers/ocr_worker.py` es el del repo, un superset del que estaba en el
disco del servidor: agrega `LEER_APELLIDO`, apagado por defecto. Con el
flag en 0 el comportamiento es el de la corrida publicada.
`primer_apellido_vision.py` no estaba en el disco del servidor, pero
`nlp_worker.py` lo importa. Sin ese archivo el contenedor NLP no arranca.
El flag sigue en 0, así que no cambia las lecturas.

`workers/casillas_vision.py` incluye la regla de Parte 9: si
`tipo_discapacidad` tiene exactamente dos marcas y una es `NINGUNA`, se
conserva `NINGUNA`. Ver `PARTE9.md`.

## Hardware que usó esta configuración

Dos NVIDIA RTX PRO 6000 Blackwell, 97.887 MiB cada una. Driver 595.84.
Docker 29.1.3, Compose 2.40.3.

vLLM reserva el 90 % de la GPU 0 para el VL y el 40 % de la GPU 1 para el
NLP. Esas dos reservas no caben en una sola tarjeta de 96 GB. Un servidor
físico con dos GPU de esa clase puede usar este `docker-compose.yml` tal
cual. Con tarjetas más chicas hay que bajar `--gpu-memory-utilization` y
`--max-model-len` antes de arrancar; si no, vLLM no carga el modelo.

## 1. Copiar imágenes y gold, ahora

Desde una máquina que tenga la llave SSH del servidor actual:

```bash
export SSH_KEY="$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem"
export DEST="/ruta/del/disco/e3"          # donde vas a guardar el backup de datos
mkdir -p "$DEST/front" "$DEST/gold"
rsync -av -e "ssh -i $SSH_KEY" \
  ubuntu@3.17.139.133:/data/e3/front/ "$DEST/front/"
rsync -av -e "ssh -i $SSH_KEY" \
  ubuntu@3.17.139.133:/data/e3/gold/gold.json \
  ubuntu@3.17.139.133:/data/e3/gold/gold_v2.json \
  ubuntu@3.17.139.133:/data/e3/gold/gold_v2_cambios.json \
  "$DEST/gold/"
```

Son 100 TIFF de frente, ids `6000000001`–`6000000101` excepto
`6000000033`, más `gold.json` y `gold_v2.json`. No subas esa carpeta a git.

## 2. Preparar el servidor físico

Ubuntu con las dos GPU visibles en `nvidia-smi`. Instala Docker y el
NVIDIA Container Toolkit (el paquete que registra el runtime `nvidia`).
Comprueba:

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

Crea los directorios y copia los datos del paso 1:

```bash
sudo mkdir -p /data/e3/front /data/e3/gold /data/hf-cache
sudo chown -R "$USER" /data/e3 /data/hf-cache
cp -a "$DEST/front/." /data/e3/front/
cp -a "$DEST/gold/gold.json" /data/e3/gold/gold.json
```

El primer arranque descarga los dos modelos a `/data/hf-cache`
(unos 16 GiB el VL y unos 5 GiB el NLP). Hace falta salida a
`huggingface.co`.

## 3. Levantar el stack

En esta carpeta (`backup/parte8-servidor-fisico`):

```bash
docker compose up -d
docker compose logs -f vllm-vl vllm
```

Espera a que los dos vLLM digan que la aplicación arrancó. La primera vez
tarda lo que tarde la descarga. Después:

```bash
docker compose ps
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv
```

GPU 0 debe mostrar el proceso del VL y GPU 1 el del NLP, con la memoria
reservada desde el arranque aunque no haya documentos en cola.

Los workers OCR y NLP instalan `pika`, `openai` y `pillow` al arrancar
(`workers/requirements.txt`) y quedan 8 y 12 procesos dentro de cada
contenedor.

Flags que ya vienen apagados y deben seguir así con este VL 7B:

- `LEER_APELLIDO` no está en el compose, así que vale 0.
- `LEER_CONTACTO` vale 0.
- `LEER_CASILLAS`, `LEER_DIRECCION`, `VOTE_NUMERIC` y `BACKFILL_FORMULARIO` valen 1.

## 4. Correr los 100 otra vez

En el host, con el puerto 5672 publicado:

```bash
python3 -m pip install pika
export RABBIT_URL=amqp://guest:guest@127.0.0.1:5672/
export DATA_DIR=/data/e3
python3 scripts/load_test_simple.py
python3 scripts/consume_results.py /data/e3/resultados_it4.jsonl 100
```

`load_test_simple.py` toma los primeros 100 archivos `6*.tif` que encuentre.
La carpeta `front/` tiene que contener solo los 100 del gold. Si hay TIFF
de más, el corte de 100 no es el lote publicado.

El comparador espera una lista JSON con `id` y `estado=listo`, no el JSONL
crudo. Desde el host:

```bash
python3 - << 'PY'
import json
rows = []
for line in open("/data/e3/resultados_it4.jsonl"):
    r = json.loads(line)
    r["id"] = r.get("doc_id")
    r["estado"] = "listo"
    rows.append(r)
json.dump(rows, open("/data/e3/preds_parte8.json", "w"), ensure_ascii=False)
print(len(rows))
PY
python3 scripts/compare_gold_real.py \
  /data/e3/gold/gold.json /data/e3/preds_parte8.json p8 parte8
```

Ese script escribe al lado del archivo de predicciones el agregado sin
datos personales y el detalle por documento. El número oficial es
`conf_real` del agregado: el promedio de las 1.800 celdas. En la corrida
de septiembre 2026 ese valor fue 87,8.

Las salidas con el texto de cada campo son datos personales. No las subas
a git ni al visor en claro.

## 5. Comprobar que es el mismo pipeline

```bash
docker logs caso1v2e3e3-vllm-vl 2>&1 \
  | grep -E "model_tag|Checkpoint size|Model loading took|Available KV cache" | head -4
docker logs caso1v2e3e3-vllm-nlp 2>&1 \
  | grep -E "model_tag|Checkpoint size|Model loading took|Available KV cache" | head -4
```

VL: modelo `Qwen/Qwen2.5-VL-7B-Instruct`, checkpoint cerca de 15,5 GiB.
NLP: `Qwen/Qwen2.5-7B-Instruct-AWQ`, checkpoint cerca de 5,2 GiB.

Rabbit de este compose usa `guest` / `guest` y publica el puerto 5672 y la
consola 15672. En un servidor alcanzable desde la red, cambia usuario y
contraseña en `docker-compose.yml` antes de levantarlo.
