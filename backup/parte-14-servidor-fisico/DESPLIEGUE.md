# Despliegue en servidor real — Parte 14

Guía para levantar el pipeline de la Parte 14 en un servidor nuevo con **dos
GPU de 96 GB** (NVIDIA RTX PRO 6000 Blackwell). Todo lo necesario está en esta
carpeta. Las imágenes van fijadas por digest, los modelos por revisión y las
librerías de Python por versión, así que se reproduce exactamente lo que se
midió (KPI 92,4 % vs gold, ~850 docs/h).

## 1. Requisitos del host

Probado con:

| Componente | Versión probada | Mínimo |
| --- | --- | --- |
| GPUs | 2× NVIDIA RTX PRO 6000 Blackwell Server Edition, 96 GB | 2 GPU, GPU0 ≥ 90 GB libres, GPU1 ≥ 40 GB |
| Driver NVIDIA | 595.91.07 | el que pida CUDA 13 (la imagen vLLM es CUDA 13.0) |
| nvidia-container-toolkit | 1.20.0 | runtime `nvidia` registrado en Docker |
| Docker / Compose | 29.1.3 / v2.40.3 | Compose v2 |
| SO | Ubuntu 26.04 LTS | cualquier Linux con lo anterior |
| CPU / RAM | 48 vCPU / 499 GB | ~16 vCPU / 64 GB |
| Disco | 21 GB de pesos + ~3 GB de imágenes Docker + formularios | |

Red: salida a internet en el **primer** arranque (Docker Hub, Hugging Face y
PyPI: los workers hacen `pip install` al arrancar). Ver sección 8 para operar
sin internet.

Comprobar antes de seguir:

```bash
nvidia-smi                      # 2 GPUs visibles
docker info | grep -i runtimes  # debe incluir nvidia
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  ubuntu nvidia-smi -L          # las 2 GPUs dentro de un contenedor
```

Si `nvidia` no aparece: instalar `nvidia-container-toolkit` y
`sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`.

## 2. Copiar el código

```bash
git clone https://github.com/shell931/ov-ia-caso-1-e3-ocr-forms.git
mkdir -p ~/e3 && cp -r ov-ia-caso-1-e3-ocr-forms/backup/parte-14-servidor-fisico ~/e3/
cd ~/e3/parte-14-servidor-fisico
grep -E '^[0-9a-f]{32}  ' MANIFEST.md | md5sum -c --quiet && echo MANIFEST OK
```

## 3. Carpetas de datos

```bash
sudo mkdir -p /data/e3/front /data/hf-cache
sudo chown -R $USER /data/e3 /data/hf-cache
```

- `/data/e3`: formularios. Los contenedores la ven en `/data/e3` **solo
  lectura**. Cada lote va en una subcarpeta (`/data/e3/front`,
  `/data/e3/lote_oct`…), un `.tif`/`.tiff` por formulario (frente 300 dpi). El
  nombre del archivo sin extensión es el `doc_id`.
- `/data/hf-cache`: pesos de los modelos.

Otras rutas: exportar `DATA_HOST=/otra/ruta` y/o `HF_HOST=/otra/ruta` antes
de `docker compose` y de los scripts.

## 4. Descargar los modelos (una vez)

```bash
bash scripts/despliegue/descargar_modelos.sh
```

Baja `Qwen/Qwen2.5-VL-7B-Instruct@cc594898…` y
`Qwen/Qwen2.5-7B-Instruct-AWQ@b2503754…` (21 GB) con el CLI de la propia
imagen vLLM. Son públicos; `HF_TOKEN` es opcional.

## 5. Levantar

```bash
docker compose up -d
docker compose ps
```

| Contenedor | Qué es | GPU | Puerto host |
| --- | --- | --- | --- |
| `caso1v2e3e3-vllm-vl` | Qwen2.5-VL-7B (página + recortes) | GPU 0, ~89 GB | 8001 |
| `caso1v2e3e3-vllm-nlp` | Qwen2.5-7B-AWQ (texto → JSON) | GPU 1, ~40 GB | 8000 |
| `caso1v2e3e3-rabbitmq` | colas `ocr_input` → `ocr_output` → `nlp_output` | — | 5672, 15672 |
| `caso1v2e3e3-ocr` | 8 workers OCR | — | — |
| `caso1v2e3e3-nlp` | 12 workers NLP | — | — |

Los vLLM tardan unos minutos en cargar. Cuando terminen:

```bash
bash scripts/despliegue/verificar.sh     # debe terminar en "TODO OK"
```

GPU0 = vision porque es la que necesita ~89 GB. Si en el servidor nuevo la
GPU0 está ocupada por otra cosa, invertir `device_ids` / `NVIDIA_VISIBLE_DEVICES`
de los dos servicios vLLM.

## 6. Procesar un lote

```bash
cp /ruta/de/los/tif/*.tif /data/e3/front/
bash scripts/despliegue/procesar_lote.sh front ~/resultados/lote1.jsonl lote1
python3 scripts/despliegue/resultados_a_csv.py ~/resultados/lote1.jsonl ~/resultados/lote1.csv
```

`procesar_lote.sh` encola todos los `.tif/.tiff` de la subcarpeta, recoge
los resultados, reintenta una vez los que salgan con error y escribe el
resumen (listos, errores, campos `revisar`, docs/h) en
`~/resultados/lote1.log`. Si quedaron mensajes de una corrida anterior en
las colas, se niega a empezar; con `PURGAR=1` las vacía.

Cada formulario sale con 21 campos (`formulario_no` … `funcionario_nombre`).
Cada campo trae `valor`, `confianza` declarada y, si las dos lecturas no
coinciden, `revisar: true` y `segunda_lectura` (dirección y nombre del
funcionario). Lo que tiene confianza 60 / `revisar` es lo que conviene
mirar a mano.

## 7. Prueba de aceptación (con el lote E3V2 y su gold)

Reproduce la medición de la Parte 14 en el servidor nuevo:

```bash
aws s3 sync s3://forme3/E3V2/front_300/ /data/e3/front/        # 267 .tif
bash scripts/despliegue/procesar_lote.sh front ~/resultados/e3v2.jsonl e3v2
# gold (tiene PII: no subir a git)
python3 scripts/corrida/gold_csv_to_json.py gold_e3.csv /data/e3/gold_lote2.json
python3 scripts/corrida/preds_lote2.py ~/resultados/e3v2.jsonl ~/resultados/preds.json
python3 scripts/corrida/compare_gold_real.py /data/e3/gold_lote2.json ~/resultados/preds.json "" e3v2
```

Esperado (ruido entre corridas ±0,3 en el total): TOTAL ≈ **92,4 %**,
`funcionario_cedula` ≈ 74 %, `funcionario_nombre` ≈ 92,5 %, 0 errores,
~850 docs/h, ~37 nombres y ~50 direcciones `revisar`. Valores por campo en
`kpis/lote2-parte14-gold-kpis.json`.

## 8. Operación

- Logs: `docker logs -f caso1v2e3e3-ocr` (o `-nlp`, `-vllm-vl`, `-vllm-nlp`).
- Reiniciar workers tras cambiar código en `workers/`:
  `docker restart caso1v2e3e3-ocr caso1v2e3e3-nlp` (no hace falta reiniciar los vLLM).
- Apagar / encender: `docker compose down` / `docker compose up -d`
  (todo tiene `restart: unless-stopped`; vuelve solo tras reiniciar el host).
- Más o menos workers: el `{1..8}` / `{1..12}` del `command` en
  `docker-compose.yml`. El cuello de botella es el VL de GPU0, no los workers.
- Sin internet después del primer arranque: los pesos quedan en
  `/data/hf-cache` y las imágenes en Docker. El `pip install` de los workers
  sí necesita PyPI en cada arranque. Para evitarlo, hacer
  `docker commit caso1v2e3e3-ocr e3-workers:p14` una vez y usar esa imagen
  en `ocr` y `nlp` quitando el `pip install` del `command`.
- Variables que cambian el comportamiento (default = lo medido): ver tabla
  de flags en `LEEME.md`. Ninguna hace falta en el compose.

## 9. Seguridad antes de producción

- RabbitMQ usa `guest/guest` y publica 5672/15672; los vLLM publican 8000/8001
  sin autenticación. En un servidor real: cerrar esos puertos en el firewall
  (los contenedores se hablan por la red interna de Compose) o cambiar los
  `ports:` a `127.0.0.1:…`, y cambiar la clave de RabbitMQ en
  `RABBITMQ_DEFAULT_PASS` y en `RABBIT_URL` (más `encolar.py` / `recolectar.py`).
- Formularios, `.jsonl`, CSV y gold tienen PII: no van a git ni al visor en
  claro.

## 10. Problemas conocidos

| Síntoma | Causa / qué hacer |
| --- | --- |
| Un doc con `error: Unterminated string…` | El NLP cortó el JSON. `procesar_lote.sh` lo reintenta solo; si persiste, reencolar ese id. |
| `Permission denied` al escribir en `/data/e3` dentro del contenedor | Es solo lectura a propósito; los scripts escriben en `/tmp` del contenedor y copian con `docker cp`. |
| `verificar.sh` dice que un vLLM no responde | Recién arrancado: esperar. Si sigue: `docker logs caso1v2e3e3-vllm-vl` (VRAM ocupada en esa GPU, driver viejo). |
| Página E-3 + E-4 en un mismo escaneo | Se procesa solo el E-3 de arriba (`pagina_e3.py`). Un escaneo girado o solo E-4 no se corrige. |
| Muchos `revisar` en nombres | Esperado (~14 %): letra ambigua; el VL tiende a completar con nombres frecuentes. |
