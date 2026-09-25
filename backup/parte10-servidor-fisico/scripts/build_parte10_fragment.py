#!/usr/bin/env python3
"""Construye partes.parte10 para el vault. KPI oficial = conf_real vs gold_v2.
El visor lee d.rows (no d.resultados).
"""
import json
from collections import defaultdict

AGG = json.load(open('/data/e3/parte10v2-gold.json'))
AGG_G1 = json.load(open('/data/e3/parte10-gold.json'))
DOCS = json.load(open('/data/e3/parte10v2-gold-docs.json'))['docs']
RECS = [json.loads(l) for l in open('/data/e3/resultados_parte10.jsonl')]

dec_por_campo = defaultdict(list)
for r in RECS:
    for c in r.get('campos', []):
        if c.get('confianza') is not None:
            dec_por_campo[c['etiqueta']].append(float(c['confianza']))

conf_campos = [{'etiqueta': et, 'confianza': round(sum(v) / len(v), 1)}
               for et, v in dec_por_campo.items() if v]

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
    'vs_gold_original': AGG_G1['conf_real'],
}

def doc_dec(rec):
    vals = [float(c['confianza']) for c in rec.get('campos', []) if c.get('confianza') is not None]
    return round(sum(vals) / len(vals), 1) if vals else None

def doc_real(job):
    d = DOCS.get(job, {})
    vals = [v.get('conf_real') for v in d.values() if v.get('conf_real') is not None]
    return round(sum(vals) / len(vals), 1) if vals else None

rows = []
for n, rec in enumerate(sorted(RECS, key=lambda r: str(r.get('doc_id'))), 1):
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

parte10 = {
    'titulo': 'Parte 10 . lector dedicado de dígitos (cédula + celular)',
    'estado': 'listo',
    'listo': len(RECS), 'jobs': len(RECS), 'pct': 100,
    'docs_per_hour': 872, 'meta': 1250, 'cumple_meta': False,
    'elapsed_fmt': '~6 min 53 s',
    'conf_campos': conf_campos,
    'gold_eval': gold_eval,
    'rows': rows,
    'nota_kpi': (
        f"KPI oficial {AGG['conf_real']}% = promedio vs gold_v2. "
        f"Misma corrida vs gold original: {AGG_G1['conf_real']}%. "
        "Recortes de dígitos + VL 7B (sin cuantizar). Parte 8/9 intactas."
    ),
}

open('/data/e3/parte10_vault_fragment.json', 'w').write(
    json.dumps(parte10, ensure_ascii=False))
print('wrote fragment rows=', len(rows), 'kpi', AGG['conf_real'])
