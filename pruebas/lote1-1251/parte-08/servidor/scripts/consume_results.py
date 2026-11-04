#!/usr/bin/env python3
"""Drena la cola nlp_output y guarda los resultados en JSONL.

Uso: consume_results.py <salida.jsonl> <esperados>
- <esperados>: si >0, para al recolectar esa cantidad de doc_id unicos
  (o al vencer el timeout). Si 0, para tras 15s sin mensajes nuevos.
"""
import os, sys, json, time
import pika

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/data/e3/resultados.jsonl"
expected = int(sys.argv[2]) if len(sys.argv) > 2 else 0

conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
ch = conn.channel()
ch.queue_declare(queue="nlp_output", durable=True)

seen = {}
deadline = time.time() + (900 if expected else 60)
idle = 0
with open(OUT, "w") as f:
    while time.time() < deadline:
        m, p, b = ch.basic_get(queue="nlp_output", auto_ack=True)
        if b:
            r = json.loads(b)
            seen[r.get("doc_id")] = r
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            idle = 0
            if expected and len(seen) >= expected:
                break
        else:
            idle += 1
            time.sleep(1)
            if not expected and idle > 15:
                break
conn.close()
print(f"recolectados {len(seen)} resultados unicos -> {OUT}")
