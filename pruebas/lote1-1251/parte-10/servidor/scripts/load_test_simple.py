#!/usr/bin/env python3
"""Script de load test para Parte 4 - 2 GPU."""

import os
import sys
import json
import time
import pika
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config
RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
DATA_DIR = Path(os.getenv('DATA_DIR', '/data/e3'))
GOLD_DIR = DATA_DIR / 'gold'
FRONT_DIR = DATA_DIR / 'front'

# Parámetros del test
NUM_DOCS = 100  # Número de documentos a procesar
CONCURRENT = 20  # Requests concurrentes
PREFIX = '6*'   # p4* para Parte 4 (o usar gold)


def enviar_tarea(doc_id, ruta_imagen):
    """Envía una tarea a la cola de OCR."""
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        channel = connection.channel()
        channel.queue_declare(queue='ocr_input', durable=True)
        
        mensaje = {
            'doc_id': doc_id,
            'ruta_imagen': str(ruta_imagen),
            'metadata': {
                'test': 'parte4_load_test',
                'timestamp': time.time()
            }
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='ocr_input',
            body=json.dumps(mensaje, ensure_ascii=False),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error enviando {doc_id}: {e}")
        return False


def main():
    print("═══════════════════════════════════════")
    print("  LOAD TEST - Parte 4 (2 GPU)")
    print("═══════════════════════════════════════")
    print(f"RabbitMQ: {RABBIT_URL}")
    print(f"Documentos: {NUM_DOCS}")
    print(f"Concurrentes: {CONCURRENT}")
    print(f"Prefix: {PREFIX}")
    print()
    
    # Buscar imágenes
    imagenes = list(FRONT_DIR.glob(f'{PREFIX}.tif'))[:NUM_DOCS]
    
    if not imagenes:
        print(f"❌ No se encontraron imágenes en {FRONT_DIR} con patrón {PREFIX}")
        sys.exit(1)
    
    print(f"✅ Encontradas {len(imagenes)} imágenes")
    print()
    
    # Enviar tareas
    print("Enviando tareas...")
    start = time.time()
    
    tareas = [
        (img.stem, str(img))
        for img in imagenes
    ]
    
    enviados = 0
    with ThreadPoolExecutor(max_workers=CONCURRENT) as executor:
        futures = [
            executor.submit(enviar_tarea, doc_id, ruta)
            for doc_id, ruta in tareas
        ]
        
        for future in as_completed(futures):
            if future.result():
                enviados += 1
    
    elapsed = time.time() - start
    
    print()
    print("═══════════════════════════════════════")
    print(f"✅ Enviados: {enviados}/{NUM_DOCS}")
    print(f"⏱️  Tiempo: {elapsed:.2f}s")
    print(f"📊 Rate: {enviados/elapsed:.1f} docs/s")
    print()
    print("🔍 Monitorear:")
    print("  - RabbitMQ: http://localhost:15672")
    print("  - Logs: sudo docker compose logs -f ocr nlp")
    print("  - GPU: watch -n1 nvidia-smi")


if __name__ == '__main__':
    main()
