#!/usr/bin/env python3
"""NLP Worker - Extrae campos estructurados del OCR usando LLM."""

import os
import re
import json
import time
import logging
import pika
from openai import OpenAI

# MEJORA: Importar post-procesamiento
from postprocess_express import postprocesar_campos_express

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Config
RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
VLLM_URL = os.getenv('VLLM_URL', 'http://localhost:8000/v1')
NLP_MODEL = os.getenv('NLP_MODEL', 'Qwen/Qwen2.5-7B-Instruct-AWQ')
WORKER_ID = os.getenv('HOSTNAME', 'nlp-worker')

# Cliente OpenAI (vLLM es compatible)
client = OpenAI(base_url=VLLM_URL, api_key="not-needed")

PROMPT_TEMPLATE = """Eres un asistente experto en extraer información de formularios gubernamentales colombianos (E3/E4).

El usuario te dará el TEXTO COMPLETO extraído del formulario por OCR.

Tu trabajo es:
1. Leer TODO el texto
2. Identificar los campos y sus valores
3. Devolver un JSON con el formato exacto especificado

CAMPOS A EXTRAER:
- formulario_no: Número de formulario (ej: 6001234)
- tipo_documento: CC, CE, TI, etc.
- numero_documento: Solo dígitos
- fecha_inscripcion: YYYY-MM-DD
- fecha_expedicion: YYYY-MM-DD
- lugar_expedicion: Ciudad de expedición
- primer_apellido, segundo_apellido, primer_nombre, segundo_nombre
- genero: MASCULINO o FEMENINO
- estado_civil: SOLTERO, CASADO, UNION_LIBRE, etc.
- direccion: Dirección completa (Cll, Cra, # sin +)
- ciudad: Solo la ciudad, sin departamento
- telefono_movil: 10 dígitos
- telefono_fijo: 7 dígitos
- email: Formato válido
- nivel_estudio: BACHILLERATO, TECNICO, PROFESIONAL, etc.
- lee_braille: SI o NO
- tipo_discapacidad: NINGUNA, VISUAL, AUDITIVA, FISICA, etc.
- etnia: INDIGENA, AFROCOLOMBIANA, RAIZALES, o vacío si no aplica
- votara: SI, NO, EN_BLANCO

FORMATO DE SALIDA (JSON):
```json
{
  "campos": [
    {"etiqueta": "formulario_no", "valor": "valor", "confianza": 95},
    {"etiqueta": "tipo_documento", "valor": "CC", "confianza": 100},
    ...
  ]
}
```

REGLAS IMPORTANTES:
- confianza: 0-100 (100 = completamente seguro)
- Si no encuentras un campo, ponlo con valor "" y confianza 0
- NO inventes datos
- IMPORTANTE: Para direcciones usa "Cll" no "C11", usa "#" no "+"
- IMPORTANTE: Ciudades sin números ni caracteres especiales
- IMPORTANTE: Teléfonos sin espacios ni guiones

TEXTO DEL FORMULARIO:
{texto_ocr}

Devuelve SOLO el JSON, sin explicaciones."""

def procesar_nlp(data):
    """Procesa el texto OCR y extrae campos estructurados."""
    texto_ocr = data.get('texto_ocr', '')
    doc_id = data.get('doc_id', 'unknown')
    
    if not texto_ocr:
        logger.warning(f"[{doc_id}] Sin texto OCR")
        return {
            'doc_id': doc_id,
            'campos': [],
            'error': 'Sin texto OCR'
        }
    
    # El template incluye un ejemplo JSON con llaves literales, por lo que no se
    # puede usar str.format (interpretaría {"campos": ...} como campos de formato).
    prompt = PROMPT_TEMPLATE.replace('{texto_ocr}', texto_ocr)
    
    try:
        start = time.time()
        
        response = client.chat.completions.create(
            model=NLP_MODEL,
            messages=[
                {"role": "system", "content": "Eres un extractor de datos experto."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        
        content = response.choices[0].message.content
        elapsed = time.time() - start
        
        # Parse JSON
        # Buscar el JSON en la respuesta (puede tener markdown)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        resultado = json.loads(content.strip())
        campos = resultado.get('campos', [])
        
        # ✨ MEJORA: Aplicar post-procesamiento
        campos = postprocesar_campos_express(campos)

        # Backfill de formulario_no desde el doc_id (intake): los formularios se
        # nombran por su numero (6000000001.tif -> formulario_no 6000000001), y el
        # VLM lo omite en ~60% de los casos. Solo se rellena si viene vacio.
        if os.getenv('BACKFILL_FORMULARIO', '1') == '1':
            doc_num = re.sub(r'\D', '', str(doc_id))
            if doc_num:
                fcampo = next((c for c in campos if c.get('etiqueta') == 'formulario_no'), None)
                if fcampo is None:
                    campos.append({'etiqueta': 'formulario_no', 'valor': doc_num,
                                   'confianza': 90, 'backfilled': True})
                elif not str(fcampo.get('valor') or '').strip():
                    fcampo['valor'] = doc_num
                    fcampo['confianza'] = 90
                    fcampo['backfilled'] = True

        logger.info(f"[{doc_id}] NLP OK - {len(campos)} campos - {elapsed:.2f}s")
        
        return {
            'doc_id': doc_id,
            'campos': campos,
            'metadata': data.get('metadata', {}),
            'nlp_time_s': elapsed
        }
        
    except Exception as e:
        logger.error(f"[{doc_id}] Error NLP: {e}")
        return {
            'doc_id': doc_id,
            'campos': [],
            'error': str(e)
        }


def callback(ch, method, properties, body):
    """Callback de RabbitMQ."""
    try:
        data = json.loads(body)
        doc_id = data.get('doc_id', 'unknown')
        
        logger.info(f"[{doc_id}] Procesando NLP...")
        
        resultado = procesar_nlp(data)
        
        # Publicar resultado
        ch.basic_publish(
            exchange='',
            routing_key='nlp_output',
            body=json.dumps(resultado, ensure_ascii=False),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[{doc_id}] NLP completado")
        
    except Exception as e:
        logger.error(f"Error en callback: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Worker principal."""
    logger.info(f"=== NLP Worker [{WORKER_ID}] ===")
    logger.info(f"VLLM: {VLLM_URL}")
    logger.info(f"Model: {NLP_MODEL}")
    logger.info(f"RabbitMQ: {RABBIT_URL}")
    
    # Esperar RabbitMQ
    for i in range(30):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
            break
        except Exception as e:
            logger.warning(f"Esperando RabbitMQ... {e}")
            time.sleep(2)
    
    channel = connection.channel()
    channel.queue_declare(queue='ocr_output', durable=True)
    channel.queue_declare(queue='nlp_output', durable=True)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='ocr_output', on_message_callback=callback)
    
    logger.info("✅ NLP Worker listo. Esperando tareas...")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Deteniendo worker...")
        channel.stop_consuming()
    
    connection.close()


if __name__ == '__main__':
    main()
