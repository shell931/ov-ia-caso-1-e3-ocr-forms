exec(open('/tmp/tfunc2.py').read().split("V={}")[0])
from difflib import SequenceMatcher
import unicodedata
gn={r['id']:r.get('funcionario_nombre','') for r in json.load(open('/data/e3/gold/gold_lote2.json'))}
def norm(v):
    s=unicodedata.normalize('NFD',str(v or '')); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',s).strip().lower()
def sim(a,b):
    a,b=norm(a),norm(b)
    if a==b: return 100
    if not a or not b: return 0
    return round(100*SequenceMatcher(None,a,b).ratio())
def runn(env):
    for k in list(os.environ):
        if k.startswith('FUNC_'): os.environ.pop(k)
    os.environ.update(env); importlib.reload(fv)
    with ThreadPoolExecutor(24) as ex:
        return dict(zip(ids, ex.map(lambda d: fv._leer_uno(cli,M,rutas[d],'funcionario_nombre')['valor'], ids)))
for nom,env in (('base',{}),('esc1',{'FUNC_ESCALA':'1'})):
    v=runn(env); s=[sim(v[d],gn[d]) for d in ids]
    print(nom,'conf_real',round(sum(s)/len(s),1),'exacto',round(100*sum(x==100 for x in s)/len(s),1),flush=True)
