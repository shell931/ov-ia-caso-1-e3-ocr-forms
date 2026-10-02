import json
seen={}
for l in open('/data/e3/resultados_lote2_parte10.jsonl'):
    r=json.loads(l); d=str(r['doc_id'])
    seen[d]={'doc_id':d,'id':d,'estado':'listo' if r.get('campos') else 'error','campos':r.get('campos',[])}
json.dump(list(seen.values()),open('/data/e3/preds_lote2.json','w'),ensure_ascii=False)
print('preds',len(seen))
