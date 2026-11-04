import sys; sys.path.insert(0,'/app')
from PIL import Image
import pagina_e3
ids='6000000108,6000000109,6000000141,6000000153,6000000154,6000000194,6000000203,6000000237,6000000238,6000000239'.split(',')
regs={'pie':(0.195,0.70,0.975,0.87),'top':(0.42,0.08,0.98,0.33)}
for nombre,(x0,y0,x1,y1) in regs.items():
    tiles=[]
    for d in ids:
        p,info=pagina_e3.normalizar(f'/data/e3/front/{d}.tif',d)
        im=Image.open(p).convert('L'); W,H=im.size
        c=im.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H))); tiles.append(c.resize((c.width//3,c.height//3)))
    w=max(t.width for t in tiles); h=sum(t.height+6 for t in tiles)
    out=Image.new('L',(w,h),128); y=0
    for t in tiles: out.paste(t,(0,y)); y+=t.height+6
    out.save(f'/tmp/vnorm_{nombre}.png'); print(nombre, info)
