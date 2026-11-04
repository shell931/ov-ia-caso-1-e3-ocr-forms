import pika, json, sys, time
from pathlib import Path
ids = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "all" else None
conn = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@rabbitmq:5672/"))
ch = conn.channel()
ch.queue_declare(queue="ocr_input", durable=True)
imgs = sorted(Path("/data/e3/front").glob("6*.tif"))
if ids:
    imgs = [p for p in imgs if p.stem in ids]
for img in imgs:
    ch.basic_publish(exchange="", routing_key="ocr_input",
                     body=json.dumps({"doc_id": img.stem, "ruta_imagen": str(img),
                                      "metadata": {"test": "lote2_parte10", "ts": time.time()}}),
                     properties=pika.BasicProperties(delivery_mode=2))
print(f"enqueue {len(imgs)}", flush=True)
conn.close()
