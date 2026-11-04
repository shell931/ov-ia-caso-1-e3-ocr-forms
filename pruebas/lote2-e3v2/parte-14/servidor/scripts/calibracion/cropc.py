from PIL import Image
import sys
ids=sys.argv[1].split(','); x0,y0,x1,y1=map(float,sys.argv[2].split(','))
tiles=[]
for did in ids:
    im=Image.open(f"/data/e3/front/{did}.tif").convert("L"); W,H=im.size
    c=im.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H))); tiles.append(c)
w=max(t.width for t in tiles); h=sum(t.height+8 for t in tiles)
out=Image.new("L",(w,h),128); y=0
for t in tiles: out.paste(t,(0,y)); y+=t.height+8
out.save("/tmp/tilesc.png")
