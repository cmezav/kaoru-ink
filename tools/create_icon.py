"""Draw original Kaoru Ink icon using Pillow (no external assets)."""
from pathlib import Path
from PIL import Image, ImageDraw,ImageFilter
import numpy as np
base=Path(__file__).resolve().parents[1]/'assets'
base.mkdir(exist_ok=True)
N=512
YY,XX=np.mgrid[:N,:N]
# dark indigo gradient with a violet bloom
r=np.clip(22+20*(YY/N)+26*np.exp(-((XX-365)**2+(YY-140)**2)/95000),0,255)
g=np.clip(17+12*(YY/N)+7*np.exp(-((XX-365)**2+(YY-140)**2)/95000),0,255)
b=np.clip(38+38*(YY/N)+33*np.exp(-((XX-365)**2+(YY-140)**2)/95000),0,255)
img=Image.fromarray(np.stack([r,g,b,np.full_like(r,255)],axis=-1).astype('uint8'),'RGBA')
mask=Image.new('L',(N,N));d=ImageDraw.Draw(mask);d.rounded_rectangle((10,10,502,502),radius=115,fill=255)
img.putalpha(mask)
# pen stroke shadow
fx=Image.new('RGBA',(N,N));fd=ImageDraw.Draw(fx)
points=[(116,369),(132,376),(156,365),(183,387),(217,390),(254,373),(296,382),(332,370),(351,360)]
fd.line(points,fill=(245,167,206,100),width=31,joint='curve')
fx=fx.filter(ImageFilter.GaussianBlur(16));img=Image.alpha_composite(img,fx)
d=ImageDraw.Draw(img)
d.line(points,fill=(236,145,195,255),width=20,joint='curve')
d.line([(118,365),(168,380),(211,384),(257,370),(296,374),(334,364)],fill=(255,220,175,255),width=8,joint='curve')
# iconic angled silver pencil with warm tip, nib at x=350,y=350
pencil=[(193,96),(234,74),(391,247),(353,289)]
d.polygon(pencil,fill=(221,200,251,255))
d.polygon([(205,97),(227,87),(376,252),(358,273)],fill=(251,232,255,255))
d.polygon([(193,96),(209,85),(368,262),(353,288)],fill=(133,101,179,255))
d.polygon([(353,288),(391,247),(404,298),(350,346)],fill=(251,208,167,255))
d.polygon([(350,346),(404,298),(384,327)],fill=(233,167,129,255))
d.polygon([(350,346),(363,312),(379,329)],fill=(33,24,51,255))
# eraser gold cap
d.polygon([(185,99),(210,79),(235,73),(244,91),(204,127)],fill=(230,160,126,255))
d.line([(194,101),(235,82)],fill=(255,217,189,255),width=6)
# tiny glint around tip
d.ellipse((351,345,362,356), fill=(255,229,174,255))
img.save(base/'icon.png')
img.save(base/'icon.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(base/'icon.png')
