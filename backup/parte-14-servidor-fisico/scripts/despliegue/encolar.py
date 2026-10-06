"""Encola formularios E3 en ocr_input. Corre DENTRO del contenedor ocr.

Uso: python encolar.py <carpeta> [ids separados por coma] [etiqueta]
  carpeta   ruta vista desde el contenedor, bajo /data/e3 (p. ej. /data/e3/front)
  ids       opcional: solo esos nombres de archivo sin extensión
doc_id = nombre del archivo sin extensión. Acepta .tif y .tiff.
"""
import json
import sys
import time
from pathlib import Path

import pika

carpeta = Path(sys.argv[1])
ids = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else None
etiqueta = sys.argv[3] if len(sys.argv) > 3 else "lote"

imgs = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in (".tif", ".tiff"))
if ids:
    imgs = [p for p in imgs if p.stem in ids]
if not imgs:
    raise SystemExit(f"sin .tif/.tiff en {carpeta}")
stems = [p.stem for p in imgs]
if len(set(stems)) != len(stems):
    raise SystemExit("hay nombres repetidos (mismo doc_id con distinta extensión)")

conn = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@rabbitmq:5672/"))
ch = conn.channel()
ch.queue_declare(queue="ocr_input", durable=True)
for img in imgs:
    ch.basic_publish(
        exchange="", routing_key="ocr_input",
        body=json.dumps({"doc_id": img.stem, "ruta_imagen": str(img),
                         "metadata": {"lote": etiqueta, "ts": time.time()}}),
        properties=pika.BasicProperties(delivery_mode=2))
conn.close()
print(f"encolados {len(imgs)}", flush=True)
