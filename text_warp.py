"""Editable text warp presets using inverse mesh mapping and transparent fill."""
import math
from PIL import Image, ImageOps

STYLES=('Arc','Arch','Wave','Bulge')
MAX_PIXELS=40_000_000

def validate(settings):
    if not isinstance(settings,dict) or set(settings)-{'style','bend'}:raise ValueError('Invalid text warp settings.')
    if settings.get('style','Arc') not in STYLES:raise ValueError('Unknown warp style.')
    b=settings.get('bend',0)
    if isinstance(b,bool) or not isinstance(b,(int,float)) or not math.isfinite(b) or not -100<=b<=100:raise ValueError('Bend must be -100 to 100.')

def geometry(w,h,style,bend):
    """Return output dimensions and inverse coordinate mapping."""
    b=bend/100
    if style=='Arc':
        # Cap angle for tall text so the inner radius stays positive.
        angle=min(abs(b)*math.radians(120),w/(h*.6))
        r=w/angle;half=angle/2
        extent=(r+h/2)*math.sin(half)
        ymin=-h/2;ymax=r-(r-h/2)*math.cos(half)
        ow,oh=math.ceil(2*extent)+6,math.ceil(ymax-ymin)+6
        def inverse(x,y):
            xx=x-ow/2;yy=y+ymin-3
            return math.atan2(xx,r-yy)*r+w/2, r-math.hypot(xx,r-yy)+h/2
    elif style in ('Arch','Wave'):
        amp=w*.25*b
        def offset(x):
            t=x/w
            return -amp*4*t*(1-t) if style=='Arch' else amp*math.sin(2*math.pi*t)
        low,high=(min(0,-amp),max(0,-amp)) if style=='Arch' else (-abs(amp),abs(amp))
        ow,oh=w+6,h+math.ceil(high-low)+6
        def inverse(x,y):
            sx=x-3
            return sx,y+low-3-offset(sx)
    else:
        def factor(x):return 1+b*.65*math.sin(math.pi*max(0,min(1,x/w)))
        ow,oh=w+6,math.ceil(h*max(1,1+b*.65))+6
        def inverse(x,y):
            sx=x-3
            return sx,(y-oh/2)/factor(sx)+h/2
    if ow*oh>MAX_PIXELS:raise ValueError('Warped artwork exceeds the 40-million-pixel limit. Reduce its size or bend.')
    return ow,oh,inverse

def apply(image,settings):
    validate(settings);bend=settings.get('bend',0)
    if not bend:return image.copy()
    style=settings.get('style','Arc');source=image
    if style=='Arc' and bend<0:source=ImageOps.flip(source)
    ow,oh,inverse=geometry(image.width,image.height,style,bend)
    mesh=[]
    # Fine cells for small previews, bounded grid size for large print images.
    step=max(4,math.ceil(max(ow,oh)/512))
    for y in range(0,oh,step):
        bottom=min(oh,y+step)
        for x in range(0,ow,step):
            right=min(ow,x+step)
            quad=tuple(v for point in ((x,y),(x,bottom),(right,bottom),(right,y)) for v in inverse(*point))
            mesh.append(((x,y,right,bottom),quad))
    out=source.transform((ow,oh),Image.Transform.MESH,mesh,Image.Resampling.BICUBIC,fillcolor=(0,0,0,0))
    if style=='Arc' and bend<0:out=ImageOps.flip(out)
    return out
