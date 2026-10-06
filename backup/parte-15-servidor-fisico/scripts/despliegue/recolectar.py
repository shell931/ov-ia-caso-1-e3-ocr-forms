"""Recoge resultados de nlp_output a un .jsonl. Corre DENTRO del contenedor ocr.

Uso: python recolectar.py <N esperados> <salida.jsonl> [minutos sin novedades, default 10]
Termina al tener N doc_id distintos o tras ese tiempo sin mensajes nuevos.
"""
import json
import sys
import time

import pika

N = int(sys.argv[1])
OUT = sys.argv[2]
QUIETO = 60 * float(sys.argv[3] if len(sys.argv) > 3 else 10)

conn = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@rabbitmq:5672/"))
ch = conn.channel()
ch.queue_declare(queue="nlp_output", durable=True)
vistos = {}
ultimo = aviso = time.time()
with open(OUT, "w") as f:
    while len(vistos) < N and time.time() - ultimo < QUIETO:
        _, _, body = ch.basic_get(queue="nlp_output", auto_ack=True)
        if not body:
            time.sleep(1)
            if time.time() - aviso > 60:
                print(f"esperando {len(vistos)}/{N}", flush=True)
                aviso = time.time()
            continue
        r = json.loads(body)
        vistos[r.get("doc_id")] = r
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        ultimo = aviso = time.time()
        if len(vistos) % 25 == 0:
            print(f"recibidos {len(vistos)}/{N}", flush=True)
conn.close()
print(f"recolectados {len(vistos)}/{N} -> {OUT}", flush=True)
