import pika, json, sys, time
N = int(sys.argv[1]); OUT = sys.argv[2]
conn = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@rabbitmq:5672/"))
ch = conn.channel()
ch.queue_declare(queue="nlp_output", durable=True)
seen = {}; deadline = time.time() + 7200; last = time.time()
with open(OUT, "w") as f:
    while time.time() < deadline and len(seen) < N:
        m, p, b = ch.basic_get(queue="nlp_output", auto_ack=True)
        if b:
            r = json.loads(b); seen[r.get("doc_id")] = r
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush(); last = time.time()
            if len(seen) % 25 == 0:
                print(f"got {len(seen)}/{N}", flush=True)
        else:
            time.sleep(1)
            if time.time() - last > 60:
                print(f"idle {len(seen)}/{N}", flush=True); last = time.time()
print(f"recolectados {len(seen)} -> {OUT}", flush=True)
