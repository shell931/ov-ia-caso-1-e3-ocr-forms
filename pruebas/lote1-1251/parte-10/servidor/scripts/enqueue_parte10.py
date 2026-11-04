import pika, json, time
from pathlib import Path
RABBIT = "amqp://guest:guest@rabbitmq:5672/"
conn = pika.BlockingConnection(pika.URLParameters(RABBIT))
ch = conn.channel()
ch.queue_declare(queue="ocr_input", durable=True)
imgs = sorted(Path("/data/e3/front").glob("6*.tif"))[:100]
print(f"enqueue {len(imgs)}", flush=True)
for img in imgs:
    msg = {
        "doc_id": img.stem,
        "ruta_imagen": str(img),
        "metadata": {"test": "parte10", "ts": time.time()},
    }
    ch.basic_publish(
        exchange="",
        routing_key="ocr_input",
        body=json.dumps(msg),
        properties=pika.BasicProperties(delivery_mode=2),
    )
print("done", flush=True)
conn.close()
