import sys; sys.path.insert(0,'/app')
import json
from PIL import Image
from openai import OpenAI
import pagina_e3, funcionario_vision as fv
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x'); M='Qwen/Qwen2.5-VL-7B-Instruct'
d=sys.argv[1]
ruta,_=pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d)
for i in range(3): print('lectura', i, fv._leer_uno(cli,M,ruta,'funcionario_nombre')['raw'])
with Image.open(ruta) as im:
    im=im.convert('L'); W,H=im.size; x0,y0,x1,y1=fv.REGIONES['funcionario_nombre']
    c=im.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H))); c.resize((c.width*2,c.height*2)).save('/tmp/nom.png')
