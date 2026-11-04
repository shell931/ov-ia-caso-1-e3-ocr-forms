import csv,json,sys
raw={r['FORMULARIO No.']:r for r in csv.DictReader(open(sys.argv[1],encoding='utf-8-sig'))}
pred={}
for l in open('/data/e3/resultados_lote2_parte10.jsonl'):
    r=json.loads(l); pred[r['doc_id']]={c['etiqueta']:c for c in r['campos']}
from collections import Counter
cnt=Counter(); ej=[]
for d,r in raw.items():
    g=r['TIPO DE DISCAPACIDAD'].strip(); p=pred[d]['tipo_discapacidad']['valor']
    com=r['A QUE COMUNIDAD DE LA ETNIA PERTENECE'].strip().upper()
    comN = com in ('NINGUNA','NINGUNO')
    if g=='' :
        cnt[('gold_vacio', 'pred='+(p or '""'), 'comunidad_NINGUNA' if comN else 'comunidad='+(com or '""'))]+=1
    if p=='NINGUNA' and g!='NINGUNA': ej.append((d,g,com,pred[d]['tipo_discapacidad'].get('marcadas')))
    cnt[('pred',p=='NINGUNA','gold',g=='NINGUNA')]+=1
for k,v in sorted(cnt.items(),key=str): print(k,v)
print('pred NINGUNA y gold distinto:',ej)
# gold NINGUNA cases: how many have comunidad NINGUNA (could be correct by luck)
gN=[d for d,r in raw.items() if r['TIPO DE DISCAPACIDAD'].strip()=='NINGUNA']
print('gold NINGUNA',len(gN),'con comunidad NINGUNA',sum(1 for d in gN if raw[d]['A QUE COMUNIDAD DE LA ETNIA PERTENECE'].strip().upper() in('NINGUNA','NINGUNO')))
