from PIL import Image; import glob, statistics
r=[];alt=[]
for p in sorted(glob.glob('/data/e3/front/*.tif')):
    im=Image.open(p); w,h=im.size
    (alt if h/w>1.05 else r).append((p.split('/')[-1][:-4],w,h,round(h/w,4)))
print('normales',len(r),'ratio min/med/max',min(x[3] for x in r),statistics.median(x[3] for x in r),max(x[3] for x in r))
print('anchos normales',min(x[1] for x in r),max(x[1] for x in r))
for a in alt: print('alta',a)
tiles=[]
for d,w,h,_ in alt:
    im=Image.open(f'/data/e3/front/{d}.tif').convert('L'); tiles.append(im.resize((w//8,h//8)))
W=sum(t.width+6 for t in tiles); H=max(t.height for t in tiles)
out=Image.new('L',(W,H),128); x=0
for t in tiles: out.paste(t,(x,0)); x+=t.width+6
out.save('/tmp/altas.png')
