import pika, json, time
OUT = "/app/_resultados_parte10.jsonl"  # workers mount -> host
RABBIT = "amqp://guest:guest@rabbitmq:5672/"
conn = pika.BlockingConnection(pika.URLParameters(RABBIT))
ch = conn.channel()
ch.queue_declare(queue="nlp_output", durable=True)
seen = {}
deadline = time.time() + 7200
last = time.time()
with open(OUT, "w") as f:
    while time.time() < deadline and len(seen) < 100:
        m, p, b = ch.basic_get(queue="nlp_output", auto_ack=True)
        if b:
            r = json.loads(b)
            did = r.get("doc_id")
            seen[did] = r
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            last = time.time()
            if len(seen) % 5 == 0:
                print(f"got {len(seen)}/100", flush=True)
        else:
            time.sleep(1)
            if time.time() - last > 60:
                print(f"idle… {len(seen)}/100", flush=True)
                last = time.time()
conn.close()
print(f"recolectados {len(seen)} -> {OUT}", flush=True)
