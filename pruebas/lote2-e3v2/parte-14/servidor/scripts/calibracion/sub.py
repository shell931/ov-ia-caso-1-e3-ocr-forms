import json,sys
ids=set(sys.argv[3].split(','))
for src,dst in ((sys.argv[1],'/tmp/sub_antes.json'),(sys.argv[2],'/tmp/sub_despues.json')):
    out=[]
    for l in open(src):
        r=json.loads(l)
        if r['doc_id'] in ids: out.append({'doc_id':r['doc_id'],'id':r['doc_id'],'estado':'listo','campos':r['campos']})
    json.dump(out,open(dst,'w'),ensure_ascii=False)
