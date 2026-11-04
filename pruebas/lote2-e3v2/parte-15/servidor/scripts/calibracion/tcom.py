import sys; sys.path.insert(0, '/app')
import os, sys, importlib
from openai import OpenAI
ids=sys.argv[1].split(',')
cli=OpenAI(base_url=os.getenv('VLLM_VL_URL','http://vllm-vl:8001/v1'), api_key='x')
for y1 in ('0.82','0.84'):
    os.environ['COM_Y1']=y1
    import comunidad_vision as cv; importlib.reload(cv)
    for d in ids:
        r=cv.leer_comunidad(f'/data/e3/front/{d}.tif', cli, 'Qwen/Qwen2.5-VL-7B-Instruct')
        print(y1, d, repr(r['raw']), '->', repr(r['valor']))
