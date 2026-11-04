import sys; sys.path.insert(0,'/app')
import os, json, importlib, re
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
import pagina_e3
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x'); M='Qwen/Qwen2.5-VL-7B-Instruct'
gold={r['id']:r.get('funcionario_cedula','') for r in json.load(open('/data/e3/gold/gold_lote2.json'))}
ids=sorted(gold)
rutas={}
for d in ids: rutas[d]=pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d)[0]
P_CAJAS = """Imagen: recorte del pie de un formulario E3 colombiano. A la derecha de
la etiqueta impresa "CÉDULA" hay una fila de cuadritos; en cada cuadrito hay
a lo sumo UN dígito escrito a mano.

Recorre los cuadritos de izquierda a derecha y escribe el dígito de cada
cuadrito que tenga tinta, sin saltarte ninguno (también los 1 delgados y los
dígitos repetidos seguidos, como 11 o 00).
- Responde SOLO los dígitos, sin espacios ni puntos.
- Cuadritos vacíos al final: no inventes ceros.
- Si todos están vacíos responde exactamente: VACIO
"""
import funcionario_vision as fv
def run(env, prompt=None):
    for k in list(os.environ):
        if k.startswith('FUNC_'): os.environ.pop(k)
    os.environ.update(env); importlib.reload(fv)
    if prompt: fv._PROMPT['funcionario_cedula']=prompt
    with ThreadPoolExecutor(24) as ex:
        return dict(zip(ids, ex.map(lambda d: fv._leer_uno(cli,M,rutas[d],'funcionario_cedula')['valor'], ids)))
def score(v): return round(100*sum(v[d]==gold[d] for d in ids)/len(ids),1)
V={}
V['base']=run({})
V['esc3']=run({'FUNC_ESCALA':'3'})
V['tight']=run({'FUNC_CED_Y0':'0.94','FUNC_CED_Y1':'0.985'})
V['cajas']=run({}, P_CAJAS)
V['cajas_esc3']=run({'FUNC_ESCALA':'3'}, P_CAJAS)
V['cajas_x10']=run({'FUNC_CED_X0':'0.10','FUNC_CED_X1':'0.46'}, P_CAJAS)
for k,v in V.items(): print(k, score(v), flush=True)
def largo(*vs):
    out={}
    for d in ids:
        c=[v[d] for v in vs if v[d]]
        out[d]=max(c,key=len) if c else ''
    return out
from collections import Counter
def voto(*vs):
    out={}
    for d in ids:
        c=Counter(v[d] for v in vs if v[d])
        if not c: out[d]=''; continue
        top=c.most_common(); best=[x for x,n in top if n==top[0][1]]
        out[d]=max(best,key=len)
    return out
ks=list(V)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        print('largo',ks[i],ks[j],score(largo(V[ks[i]],V[ks[j]])))
print('voto todos', score(voto(*V.values())))
print('oracle', round(100*sum(any(v[d]==gold[d] for v in V.values()) for d in ids)/len(ids),1))
json.dump(V,open('/tmp/tfunc2.json','w'))
