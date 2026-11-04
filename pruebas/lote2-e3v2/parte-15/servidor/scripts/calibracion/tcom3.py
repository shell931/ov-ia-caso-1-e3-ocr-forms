import sys; sys.path.insert(0,'/app')
import os, importlib, json, re, unicodedata
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x')
gold={r['id']:r['comunidad_etnia'] for r in json.load(open('/data/e3/gold/gold_lote2.json'))}
def norm(v):
    s=unicodedata.normalize('NFD',str(v or '')); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',s).strip().lower()
def sim(a,b):
    if a==b: return 100
    if not a or not b: return 0
    return round(100*SequenceMatcher(None,a,b).ratio())
P_SIN = """Esta imagen es el interior de una caja de un formulario donde la persona
escribió a mano una respuesta corta (por ejemplo Ninguna, No aplica, N/A,
o el nombre de una comunidad o pueblo).

Copia el texto manuscrito tal cual, en una línea. No corrijas ni completes.
Solo si no hay ningún trazo de tinta responde: VACIO
"""
P2 = """Imagen: recorte de un formulario. Arriba está impreso el título
"A QUE COMUNIDAD DE LA ETNIA PERTENECE" (no lo copies). Debajo, a mano,
la persona escribió una respuesta corta (por ejemplo Ninguna, No aplica, N/A,
o el nombre de una comunidad).

¿Qué escribió a mano? Copia el texto manuscrito tal cual, en una línea.
Solo si debajo del título no hay ningún trazo de tinta responde: VACIO
"""
variantes = {
 'actual':       (dict(), None),
 'p2_y84':       (dict(COM_Y1='0.84'), P2),
 'sintit_y84':   (dict(COM_Y0='0.74', COM_Y1='0.84'), None),
 'sintit_psin':  (dict(COM_Y0='0.74', COM_Y1='0.84'), P_SIN),
}
ids=sorted(gold)
res={}
for nombre,(env,prompt) in variantes.items():
    for k in ('COM_X0','COM_Y0','COM_X1','COM_Y1','COM_ESCALA'): os.environ.pop(k,None)
    os.environ.update(env)
    import comunidad_vision as cv; importlib.reload(cv)
    if prompt: cv.PROMPT=prompt
    with ThreadPoolExecutor(16) as ex:
        vals=list(ex.map(lambda d: cv.leer_comunidad(f'/data/e3/front/{d}.tif',cli,'Qwen/Qwen2.5-VL-7B-Instruct')['valor'], ids))
    res[nombre]=dict(zip(ids,vals))
    for strip in (False,True):
        s=[]; ex_=0
        for d,v in zip(ids,vals):
            if strip: v=re.sub(r'[.,;:]+$','',v).strip()
            a,b=norm(v),norm(gold[d]); s.append(sim(a,b)); ex_+=a==b
        print(f"{nombre:13s} strip={strip!s:5s} conf_real={sum(s)/len(s):.1f} exacto={100*ex_/len(ids):.1f} vacios={sum(1 for v in vals if not v)}", flush=True)
json.dump(res,open('/tmp/tcom3_res.json','w'),ensure_ascii=False)
