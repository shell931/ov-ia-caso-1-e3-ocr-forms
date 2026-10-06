import sys; sys.path.insert(0,'/app')
import json, random
from PIL import Image, ImageDraw
import pagina_e3, funcionario_vision as fv
R={r['doc_id']:r for r in map(json.loads,open('/tmp/resultados_lote2.jsonl'))}
ids=sorted(R); random.seed(14); ids=random.sample(ids,16)
tiles=[]
for d in ids:
    ruta,_=pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d)
    with Image.open(ruta) as im:
        im=im.convert('L'); W,H=im.size
        t=im.crop((int(0.04*W),int(0.935*H),int(0.99*W),int(0.99*H))).resize((1100,int(1100*0.055*H/(0.95*W))))
    v={c['etiqueta']:c['valor'] for c in R[d]['campos']}
    cap=Image.new('L',(1100,t.height+22),255); cap.paste(t,(0,22))
    ImageDraw.Draw(cap).text((5,4),f"{d}  ced={v.get('funcionario_cedula')}  nom={v.get('funcionario_nombre')}",fill=0)
    tiles.append(cap)
out=Image.new('L',(1100,sum(t.height for t in tiles)),128); y=0
for t in tiles: out.paste(t,(0,y)); y+=t.height
out.save('/tmp/spot.png'); print(ids)
