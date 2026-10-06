import sys; sys.path.insert(0,'/app')
import json, re, unicodedata
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
import pagina_e3, funcionario_vision as fv
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x'); M='Qwen/Qwen2.5-VL-7B-Instruct'
gold={r['id']:r.get('funcionario_nombre','') for r in json.load(open('/data/e3/gold/gold_lote2.json'))}
ids=sorted(gold)
rutas={d:pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d)[0] for d in ids}
def norm(v):
    s=unicodedata.normalize('NFD',str(v or '')); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',s).strip().lower()
def sim(a,b):
    a,b=norm(a),norm(b)
    if a==b: return 100
    if not a or not b: return 0
    return round(100*SequenceMatcher(None,a,b).ratio())
P_LETRAS = """Imagen: recorte del pie de un formulario E3 colombiano, caja "NOMBRE"
(etiqueta impresa, no la copies). A mano está el nombre del funcionario.

Transcribe letra por letra lo que ves escrito, aunque el resultado no parezca
un nombre real o común. No adivines nombres: si una letra es dudosa, escribe
la que más se parece a lo trazado. Una sola línea.
Solo si la caja no tiene ningún trazo de tinta responde: VACIO
"""
def leer(d, prompt, temp):
    b64=fv._crop_b64(rutas[d], fv.REGIONES['funcionario_nombre'])
    r=cli.chat.completions.create(model=M, messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}}]}], max_tokens=48, temperature=temp)
    return fv.limpiar_nombre(r.choices[0].message.content or "")
P0=fv._PROMPT['funcionario_nombre']
V={}
with ThreadPoolExecutor(24) as ex:
    for k,(p,t) in {'base':(P0,0.0),'t03':(P0,0.3),'t03b':(P0,0.3),'letras':(P_LETRAS,0.0),'letras_t03':(P_LETRAS,0.3)}.items():
        V[k]=dict(zip(ids, ex.map(lambda d: leer(d,p,t), ids)))
json.dump(V,open('/tmp/tnom2.json','w'))
def sc(v): s=[sim(v[d],gold[d]) for d in ids]; return round(sum(s)/len(s),1), round(100*sum(x==100 for x in s)/len(s),1)
for k,v in V.items(): print(k,'conf_real,exacto',sc(v))
base=V['base']
malos={d for d in ids if norm(base[d])!=norm(gold[d])}
muy_malos={d for d in ids if sim(base[d],gold[d])<85}
for k in ('t03','letras','letras_t03'):
    flag={d for d in ids if norm(V[k][d])!=norm(base[d])}
    print(f"flag {k}: marcados {len(flag)} | de ellos mal {len(flag&malos)} | cubre {len(flag&malos)}/{len(malos)} no-exactos, {len(flag&muy_malos)}/{len(muy_malos)} con sim<85 | sim prom marcados {round(sum(sim(base[d],gold[d]) for d in flag)/max(1,len(flag)),1)} vs no marcados {round(sum(sim(base[d],gold[d]) for d in set(ids)-flag)/max(1,len(set(ids)-flag)),1)}")
