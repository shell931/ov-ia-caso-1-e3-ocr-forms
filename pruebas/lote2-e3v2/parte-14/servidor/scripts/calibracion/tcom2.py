import sys; sys.path.insert(0,'/app')
import os, importlib, csv
from openai import OpenAI
cli=OpenAI(base_url='http://vllm-vl:8000/v1', api_key='x')
ids=sys.argv[1].split(',')
P2 = """Imagen: recorte de un formulario. Arriba está impreso el título
"A QUE COMUNIDAD DE LA ETNIA PERTENECE" (no lo copies). Debajo, a mano,
la persona escribió una respuesta corta (por ejemplo Ninguna, No aplica, N/A,
o el nombre de una comunidad).

¿Qué escribió a mano? Copia el texto manuscrito tal cual, en una línea.
Solo si debajo del título no hay ningún trazo de tinta responde: VACIO
"""
variantes = {
 'base_y84': dict(COM_Y1='0.84'),
 'y84_e3': dict(COM_Y1='0.84', COM_ESCALA='3'),
 'sin_titulo_y84': dict(COM_Y0='0.74', COM_Y1='0.84'),
 'p2_y84': dict(COM_Y1='0.84', _P='P2'),
}
for nombre, env in variantes.items():
    for k in ('COM_X0','COM_Y0','COM_X1','COM_Y1','COM_ESCALA'): os.environ.pop(k, None)
    for k,v in env.items():
        if not k.startswith('_'): os.environ[k]=v
    import comunidad_vision as cv; importlib.reload(cv)
    if env.get('_P')=='P2': cv.PROMPT=P2
    out=[]
    for d in ids:
        r=cv.leer_comunidad(f'/data/e3/front/{d}.tif', cli, 'Qwen/Qwen2.5-VL-7B-Instruct')
        out.append(r['valor'] or '-')
    print(nombre.ljust(16), ' | '.join(out))
