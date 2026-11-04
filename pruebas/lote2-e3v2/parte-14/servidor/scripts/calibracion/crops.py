from PIL import Image
import sys
ids=sys.argv[1].split(','); x1=float(sys.argv[2])
tiles=[]
for did in ids:
    im=Image.open(f"/data/e3/front/{did}.tif").convert("L"); W,H=im.size
    c=im.crop((int(0.195*W),int(0.70*H),int(x1*W),int(0.87*H)))
    c=c.resize((c.width//2,c.height//2)); tiles.append(c)
w=max(t.width for t in tiles); h=sum(t.height+6 for t in tiles)
out=Image.new("L",(w,h),255); y=0
for t in tiles: out.paste(t,(0,y)); y+=t.height+6
out.save("/tmp/tiles.png")
