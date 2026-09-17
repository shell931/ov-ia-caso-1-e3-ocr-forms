#!/usr/bin/env python3
"""OCR Worker - Extrae texto de formularios E3/E4 usando Docling + VLM."""

import os
import json
import time
import logging
import pika
from pathlib import Path
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Config
RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
VLLM_VL_URL = os.getenv('VLLM_VL_URL', 'http://localhost:8001/v1')
VL_MODEL = os.getenv('VLLM_VL_MODEL', 'Qwen/Qwen2.5-VL-7B-Instruct')
DATA_DIR = os.getenv('DATA_DIR', '/data/e3')
WORKER_ID = os.getenv('HOSTNAME', 'ocr-worker')

# Cliente OpenAI (vLLM es compatible)
client_vl = OpenAI(base_url=VLLM_VL_URL, api_key="not-needed")

VLM_PROMPT = """Este es un formulario E3 o E4 del Consulado colombiano.

INSTRUCCIONES:
1. Lee TODO el texto del formulario
2. Transcribe EXACTAMENTE lo que ves, campo por campo
3. Respeta el orden del formulario
4. NO omitas ningún campo
5. Si un campo está vacío, escribe "VACÍO"

IMPORTANTE:
- Para direcciones: "Cll" no "C11", "#" no "+", separar números y letras
- Para ciudades: Sin números ni caracteres especiales (ej: "Bogota" no "Bo50.t3")
- Para teléfonos: Solo dígitos, sin espacios
- Para emails: Formato válido (@ y .com/net/co)

Transcribe el formulario completo:"""


def imagen_a_base64(ruta_imagen):
    """Convierte imagen a base64 para enviar a VLM."""
    import base64
    with open(ruta_imagen, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def procesar_ocr_vlm(ruta_imagen):
    """Procesa la imagen con el modelo VLM."""
    try:
        # Leer imagen
        img_base64 = imagen_a_base64(ruta_imagen)
        
        start = time.time()
        
        response = client_vl.chat.completions.create(
            model=VL_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VLM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/tiff;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048,
            temperature=0.1
        )
        
        texto = response.choices[0].message.content
        elapsed = time.time() - start
        
        logger.info(f"VLM OK - {len(texto)} chars - {elapsed:.2f}s")
        
        return {
            'texto_ocr': texto,
            'ocr_time_s': elapsed,
            'ocr_engine': 'vlm'
        }
        
    except Exception as e:
        logger.error(f"Error VLM: {e}")
        return {
            'texto_ocr': '',
            'error': str(e)
        }


def callback(ch, method, properties, body):
    """Callback de RabbitMQ."""
    try:
        data = json.loads(body)
        doc_id = data.get('doc_id', 'unknown')
        ruta_imagen = data.get('ruta_imagen', '')
        
        logger.info(f"[{doc_id}] Procesando OCR...")
        
        # Verificar que existe la imagen
        if not os.path.exists(ruta_imagen):
            logger.error(f"[{doc_id}] No existe: {ruta_imagen}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        
        # Procesar con VLM
        resultado_ocr = procesar_ocr_vlm(ruta_imagen)
        
        # Preparar para siguiente stage
        resultado = {
            'doc_id': doc_id,
            'ruta_imagen': ruta_imagen,
            **resultado_ocr,
            'metadata': data.get('metadata', {})
        }
        
        # Publicar a siguiente cola
        ch.basic_publish(
            exchange='',
            routing_key='ocr_output',
            body=json.dumps(resultado, ensure_ascii=False),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[{doc_id}] OCR completado")
        
    except Exception as e:
        logger.error(f"Error en callback: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Worker principal."""
    logger.info(f"=== OCR Worker [{WORKER_ID}] ===")
    logger.info(f"VLM: {VLLM_VL_URL}")
    logger.info(f"Model: {VL_MODEL}")
    logger.info(f"Data: {DATA_DIR}")
    
    # Esperar RabbitMQ
    for i in range(30):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
            break
        except Exception as e:
            logger.warning(f"Esperando RabbitMQ... {e}")
            time.sleep(2)
    
    channel = connection.channel()
    channel.queue_declare(queue='ocr_input', durable=True)
    channel.queue_declare(queue='ocr_output', durable=True)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='ocr_input', on_message_callback=callback)
    
    logger.info("✅ OCR Worker listo. Esperando tareas...")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Deteniendo worker...")
        channel.stop_consuming()
    
    connection.close()


if __name__ == '__main__':
    main()
