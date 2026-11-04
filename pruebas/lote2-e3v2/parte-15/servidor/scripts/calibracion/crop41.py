from PIL import Image
for did in ["6000000041"]:
    im=Image.open(f"/data/e3/front/{did}.tif").convert("L"); W,H=im.size
    x0,y0,x1,y1=(0.195,0.70,0.90,0.87)
    im.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H))).save(f"/tmp/crop_{did}_pie.png")
    im.resize((W//3,H//3)).save(f"/tmp/page_{did}.png")
    print(did,W,H)
