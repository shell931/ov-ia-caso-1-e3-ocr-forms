import sys; sys.path.insert(0,'/app')
import json
from PIL import Image
from openai import OpenAI
import pagina_e3, funcionario_vision as fv
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x')
ids=sys.argv[1].split(',')
tiles=[]
for d in ids:
    ruta,_=pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d)
    r=fv.leer_funcionario(ruta, cli, 'Qwen/Qwen2.5-VL-7B-Instruct')
    print(d, json.dumps({k:v['raw'] for k,v in r.items()}, ensure_ascii=False))
    with Image.open(ruta) as im:
        im=im.convert('L'); W,H=im.size
        for c,(x0,y0,x1,y1) in fv.REGIONES.items():
            tiles.append(im.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H))).resize((600,int(600*(y1-y0)*H/((x1-x0)*W)))))
w=1200; h=sum(t.height for t in tiles[::2])+4*len(ids)
out=Image.new('L',(w,h),128); y=0
for i in range(0,len(tiles),2):
    out.paste(tiles[i],(0,y)); out.paste(tiles[i+1],(600,y)); y+=max(tiles[i].height,tiles[i+1].height)+4
out.save('/tmp/fcrops.png')
