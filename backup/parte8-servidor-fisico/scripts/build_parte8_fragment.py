#!/usr/bin/env python3
"""Construye el objeto partes.parte8 para el vault del visor e3-pages.

Combina:
  - parte8-gold.json      (agregado por campo, metrica original)
  - parte8-gold-docs.json (gold/veredicto/conf_real por doc y campo)
  - resultados_it4.jsonl  (valor + confianza declarada por doc y campo)

Salida: /data/e3/parte8_vault_fragment.json  (CONTIENE PII: valores capturados)
"""
import json
from collections import defaultdict

AGG = json.load(open('/data/e3/parte8-gold.json'))
DOCS = json.load(open('/data/e3/parte8-gold-docs.json'))['docs']  # {job: {campo: {gold,sim,veredicto,conf_real}}}
RECS = [json.loads(l) for l in open('/data/e3/resultados_it4.jsonl')]

# --- confianza declarada promedio por campo (para el panel "declarada") ---
dec_por_campo = defaultdict(list)
for r in RECS:
    for c in r.get('campos', []):
        if c.get('confianza') is not None:
            dec_por_campo[c['etiqueta']].append(float(c['confianza']))

conf_campos = [{'etiqueta': et, 'confianza': round(sum(v) / len(v), 1)}
               for et, v in dec_por_campo.items() if v]

# --- gold_eval (del agregado, metrica original) ---
gold_eval = {
    'conf_real': AGG['conf_real'],
    'brecha': AGG['brecha'],
    'falsos_100': AGG['falsos_100'],
    'comparaciones': AGG['comparaciones'],
    'gold_docs': AGG['gold_docs'],
    'veredictos': AGG['veredictos'],
    'umbral_casi': AGG.get('umbral_casi', 85),
    'campos': [{'etiqueta': c['etiqueta'], 'conf_declarada': c['conf_declarada'],
                'conf_real': c['conf_real'], 'exacto': c.get('exacto'),
                'brecha': c['brecha']} for c in AGG['campos']],
}

# --- filas por documento (con captura por campo) ---
def doc_dec(rec):
    vals = [float(c['confianza']) for c in rec.get('campos', []) if c.get('confianza') is not None]
    return round(sum(vals) / len(vals), 1) if vals else None

def doc_real(job):
    d = DOCS.get(job, {})
    vals = [v.get('conf_real') for v in d.values() if v.get('conf_real') is not None]
    return round(sum(vals) / len(vals), 1) if vals else None

rows = []
recs_sorted = sorted(RECS, key=lambda r: str(r.get('doc_id')))
for n, rec in enumerate(recs_sorted, 1):
    did = str(rec.get('doc_id'))
    goldd = DOCS.get(did, {})
    campos = []
    for c in rec.get('campos', []):
        et = c.get('etiqueta')
        g = goldd.get(et, {})
        campo = {'etiqueta': et, 'valor': c.get('valor', ''), 'confianza': c.get('confianza', 0)}
        if g:
            campo['conf_real'] = g.get('conf_real')
            campo['veredicto'] = g.get('veredicto')
            campo['gold'] = g.get('gold', '')
        campos.append(campo)
    rows.append({
        'id': did, 'n': n, 'formulario': did,
        'estado': 'listo', 'estado_label': 'listo',
        'confianza': doc_dec(rec), 'conf_real': doc_real(did),
        'hora': '', 'ruta': f'/data/e3/front/{did}.tif',
        'campos': campos,
    })

parte8 = {
    'titulo': 'Parte 8 . 2 GPU Frente — mejoras + casillas por visión',
    'estado': 'listo',
    'listo': len(RECS), 'jobs': len(RECS), 'pct': 100,
    'docs_per_hour': 968, 'meta': 1250, 'cumple_meta': False,
    'elapsed_fmt': '~6 min 12 s',
    'errores': 0, 'cola': 0, 'concurrency': 20, 'workers': '8 OCR + 12 NLP',
    'stamp': '',
    'confianza': {
        'general': round(sum(c['confianza'] for c in conf_campos) / len(conf_campos), 1) if conf_campos else None,
        'n_docs': len(RECS), 'campos': conf_campos,
    },
    'modelos': [
        {'nombre': 'Qwen/Qwen2.5-VL-7B-Instruct', 'rol': 'Visión / OCR', 'donde': 'GPU 0 · vLLM :8001', 'vram': '~88 GB'},
        {'nombre': 'Qwen/Qwen2.5-7B-Instruct-AWQ', 'rol': 'NLP / campos', 'donde': 'GPU 1 · vLLM :8000', 'vram': '~40 GB'},
    ],
    'vram': {'used_gb': 128, 'total_gb': 192, 'used_mib': 128174, 'total_mib': 195774, 'gpu': '2× RTX PRO 6000'},
    'gold_eval': gold_eval,
    'rows': rows,
}

json.dump(parte8, open('/data/e3/parte8_vault_fragment.json', 'w'), ensure_ascii=False)
print('fragmento parte8 escrito: /data/e3/parte8_vault_fragment.json')
print('  docs:', len(rows), '| conf_real:', gold_eval['conf_real'], '| brecha:', gold_eval['brecha'])
