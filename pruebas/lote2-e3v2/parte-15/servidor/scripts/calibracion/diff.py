import json
g={r['id']:r for r in json.load(open('/data/e3/gold/gold_lote2.json'))}
def load(p):
    o={}
    for l in open(p):
        r=json.loads(l); o[r['doc_id']]={c['etiqueta']:c for c in r['campos']}
    return o
a=load('/data/e3/resultados_lote2_parte10.jsonl'); import sys; b=load(sys.argv[1])
for campo in ('tipo_discapacidad','etnia'):
    mej=peo=otro=0
    for d in sorted(a):
        va=a[d][campo]['valor']; vb=b[d][campo]['valor']; gv=g[d][campo]
        if va==vb: continue
        ok_a=va.upper()==gv.upper(); ok_b=vb.upper()==gv.upper()
        tag='MEJORA' if ok_b and not ok_a else 'EMPEORA' if ok_a and not ok_b else 'igual-mal'
        mej+=tag=='MEJORA'; peo+=tag=='EMPEORA'; otro+=tag=='igual-mal'
        print(campo,d,tag,'antes',va or '""',a[d][campo].get('marcadas'),'ahora',vb or '""',b[d][campo].get('marcadas'),'gold',gv or '""')
    print(campo,'mejoras',mej,'empeora',peo,'otros',otro)
