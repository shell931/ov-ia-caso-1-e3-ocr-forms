import sys; sys.path.insert(0,'/app')
import os, importlib, json, re, unicodedata
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
import pagina_e3
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x')
gold={r['id']:r['direccion'] for r in json.load(open('/data/e3/gold/gold_lote2.json'))}
def norm(v):
    s=unicodedata.normalize('NFD',str(v or '')); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',s).strip().lower()
def sim(a,b):
    if a==b: return 100
    if not a or not b: return 0
    return round(100*SequenceMatcher(None,a,b).ratio())
COMP=re.compile(r'\b(apto|apt|ap|apartamento|lote|lt|torre|tor|int|interior|casa|cs|etapa|et|bloque|bl|blq|mz|manzana|piso|conjunto|barrio)\b')
P_B = """Esta imagen es SOLO la caja manuscrita
"DIRECCIÓN Y/O LUGAR DE RESIDENCIA" de un formulario E3 colombiano.

Copia la dirección escrita a mano, carácter por carácter, en UNA sola línea.
- Copia solo lo que se ve escrito. NO agregues palabras que no estén escritas.
- No interpretes ni completes: si un trazo no se entiende, no lo conviertas
  en una palabra.
- El símbolo de número puede estar escrito como N, No, Nº o #: cópialo así.
- Respeta letras y números de la vía, guiones y puntos tal como aparecen.
- Si la caja está vacía responde exactamente: VACIO

Respuesta: solo la dirección (o VACIO), sin comillas ni explicación.
"""
P_C = """Esta imagen es SOLO la caja manuscrita
"DIRECCIÓN Y/O LUGAR DE RESIDENCIA" de un formulario E3 colombiano.

Transcribe la dirección EXACTA, en UNA sola línea, tal como está escrita.
- Copia tipo de vía como aparece (Calle/Cll/Cra/Kra/Tv/Av/Dg…).
- Conserva letras de la vía (90J, 71 a, 54 F, Bis).
- Conserva # o Nº y guiones (50-29, 79-97).
- Conserva Sur/Norte/Este/Oeste y los complementos que estén escritos.
- NO agregues palabras que no estén escritas. NO inventes, NO completes, NO reformatees.
- Si la caja está vacía responde exactamente: VACIO

Respuesta: solo la dirección (o VACIO), sin comillas ni explicación.
"""
variantes={'actual_rep':({},None),'sin_ejemplos':({},P_C),'sin_ejemplos_sin_ciudad':({'DIR_X0':'0.25'},P_C)}
ids=sorted(gold); norm_paths={}
for d in ids:
    p,_=pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d); norm_paths[d]=p
res={}
for nombre,(env,prompt) in variantes.items():
    for k in ('DIR_X0','DIR_Y0','DIR_X1','DIR_Y1','DIR_ESCALA'): os.environ.pop(k,None)
    os.environ.update(env)
    import direccion_vision as dv; importlib.reload(dv)
    if prompt: dv.PROMPT=prompt
    with ThreadPoolExecutor(16) as ex:
        vals=list(ex.map(lambda d: dv.leer_direccion(norm_paths[d],cli,'Qwen/Qwen2.5-VL-7B-Instruct')['valor'], ids))
    res[nombre]=dict(zip(ids,vals))
    s=[sim(norm(v),norm(gold[d])) for d,v in zip(ids,vals)]
    ex_=sum(norm(v)==norm(gold[d]) for d,v in zip(ids,vals))
    inv=sum(1 for d,v in zip(ids,vals) if set(COMP.findall(norm(v)))-set(COMP.findall(norm(gold[d]))))
    print(f"{nombre:24s} conf_real={sum(s)/len(s):.1f} exacto={100*ex_/len(ids):.1f} complemento_inventado={inv} vacios={sum(1 for v in vals if not v)} r75={res[nombre]['6000000075']!r}", flush=True)
json.dump(res,open('/tmp/tdir_res2.json','w'),ensure_ascii=False)
for nombre,vals in res.items():
    for d,v in vals.items():
        if set(COMP.findall(norm(v)))-set(COMP.findall(norm(gold[d]))): print('inventa',nombre,d,repr(v))
