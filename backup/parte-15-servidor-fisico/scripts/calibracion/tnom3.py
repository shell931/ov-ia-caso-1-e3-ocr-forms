exec(open('/tmp/tnom2.py').read().split("P_LETRAS")[0].replace("rutas={d:pagina_e3.normalizar(f'/data/e3/front/{d}.tif', d)[0] for d in ids}",""))
V=json.load(open('/tmp/tnom2.json')); base=V['base']
malos={d for d in ids if norm(base[d])!=norm(gold[d])}; muy={d for d in ids if sim(base[d],gold[d])<85}
for k in ('letras','t03'):
  for th in (100,95,90,85,80):
    flag={d for d in ids if sim(base[d],V[k][d])<th}
    ok=set(ids)-flag
    print(k,th,'marcados',len(flag),'mal',len(flag&malos),'cubre_sim<85',f"{len(flag&muy)}/{len(muy)}",'real marcados',round(sum(sim(base[d],gold[d]) for d in flag)/max(1,len(flag)),1),'real resto',round(sum(sim(base[d],gold[d]) for d in ok)/len(ok),1),'exacto resto',round(100*len(ok-malos)/len(ok),1))
