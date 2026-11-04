exec(open('/tmp/tfunc2.py').read().split("V={}")[0])
V=json.load(open('/tmp/tfunc2.json'))
V['esc1']=run({'FUNC_ESCALA':'1'})
V['cajas_esc1']=run({'FUNC_ESCALA':'1'}, P_CAJAS)
V['x10_esc1']=run({'FUNC_ESCALA':'1','FUNC_CED_X0':'0.10','FUNC_CED_X1':'0.46'}, P_CAJAS)
for k in ('esc1','cajas_esc1','x10_esc1'): print(k, score(V[k]), flush=True)
def largo(*vs):
    return {d:max([v[d] for v in vs if v[d]] or [''],key=len) for d in ids}
for a in ('base','esc1','cajas_esc1','x10_esc1','cajas_x10'):
    for b in ('esc1','cajas_esc1','x10_esc1','cajas_x10'):
        if a<b: print('largo',a,b,score(largo(V[a],V[b])))
print('largo base esc1 cajas_x10', score(largo(V['base'],V['esc1'],V['cajas_x10'])))
json.dump(V,open('/tmp/tfunc2.json','w'))
