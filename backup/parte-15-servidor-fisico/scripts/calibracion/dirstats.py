import json,re,unicodedata,sys
sys.path.insert(0,'/home/ubuntu/test-ia-local/caso-1-v2-e3/workers')
from difflib import SequenceMatcher
g={x['id']:x['direccion'] for x in json.load(open('/data/e3/gold/gold_lote2.json'))}
def norm(v):
    s=unicodedata.normalize('NFD',str(v or '')); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',s).strip().lower()
COMP=re.compile(r'\b(apto|apt|ap|apartamento|lote|lt|torre|int|interior|casa|etapa|bloque|bl|mz|manzana|piso)\b')
for f in ('resultados_lote2_e3sola','resultados_lote2_dir'):
    inv=[];rev=[];fuentes={}
    for l in open(f'/data/e3/{f}.jsonl'):
        r=json.loads(l); c=next(x for x in r['campos'] if x['etiqueta']=='direccion'); d=r['doc_id']
        fuentes[c.get('fuente','nlp')]=fuentes.get(c.get('fuente','nlp'),0)+1
        gc={ 'apto' if t in('apt','ap','apartamento') else t for t in COMP.findall(norm(g[d]))}
        pc={ 'apto' if t in('apt','ap','apartamento') else t for t in COMP.findall(norm(c['valor']))}
        if pc-gc: inv.append((d,c['valor']))
        if c.get('revisar'): rev.append((d, norm(c['valor'])==norm(g[d]), round(100*SequenceMatcher(None,norm(c['valor']),norm(g[d])).ratio())))
    print(f, 'fuentes',fuentes,'complemento_inventado',len(inv),inv[:6])
    if rev: print('  revisar',len(rev),'de ellos exactos',sum(1 for x in rev if x[1]),'sim media',round(sum(x[2] for x in rev)/len(rev),1))
r=[json.loads(l) for l in open('/data/e3/resultados_lote2_dir.jsonl')]
print([c for x in r if x['doc_id']=='6000000075' for c in x['campos'] if c['etiqueta']=='direccion'])
