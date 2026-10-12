"""Non-destructive RGB layer adjustments. Alpha is preserved exactly."""
import math
from PIL import Image, ImageOps, ImageColor

ORDER = ('curves', 'levels', 'hue_saturation', 'invert', 'threshold', 'gradient_map')

def number(value,low,high,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError(f"{label} must be a number.")
    value=float(value)
    if not math.isfinite(value) or not low<=value<=high:raise ValueError(f'{label} must be {low}–{high}.')
    return value

def curve_lut(points):
    if not isinstance(points,list) or not 2<=len(points)<=32:raise ValueError('Curves need 2–32 points.')
    if any(not isinstance(p,(list,tuple)) or len(p)!=2 for p in points):raise ValueError('Each curve point needs input and output.')
    points=[(number(p[0],0,255,'Curve input'),number(p[1],0,255,'Curve output')) for p in points]
    if points[0][0]!=0 or points[-1][0]!=255 or any(a[0]>=b[0] for a,b in zip(points,points[1:])):
        raise ValueError('Curve inputs must increase, starting at 0 and ending at 255.')
    lut=[];j=0
    for x in range(256):
        while j<len(points)-2 and x>points[j+1][0]:j+=1
        a,b=points[j],points[j+1];lut.append(round(a[1]+(x-a[0])*(b[1]-a[1])/(b[0]-a[0])))
    return lut

def validate(settings):
    if not isinstance(settings,dict) or set(settings)-set(ORDER):raise ValueError('Unknown adjustment settings.')
    for name,c in settings.items():
        if not isinstance(c,dict):raise ValueError('Invalid adjustment settings.')
        if not isinstance(c.get('enabled',False),bool):raise ValueError('Invalid adjustment switch.')
        if name=='curves':
            for channel in ('rgb','r','g','b'):curve_lut(c.get(channel,[[0,0],[255,255]]))
        elif name=='levels':
            black=number(c.get('black',0),0,254,'Input black');white=number(c.get('white',255),1,255,'Input white')
            if black>=white:raise ValueError('Input black must be below input white.')
            number(c.get('gamma',1),.1,10,'Gamma')
            lo=number(c.get('out_black',0),0,255,'Output black');hi=number(c.get('out_white',255),0,255,'Output white')
            if lo>hi:raise ValueError('Output black must not exceed output white.')
        elif name=='hue_saturation':
            number(c.get('hue',0),-180,180,'Hue');number(c.get('saturation',0),-100,100,'Saturation')
        elif name=='threshold':number(c.get('value',128),0,255,'Threshold')
        elif name=='gradient_map':
            for key,default in [('shadow','#000000'),('highlight','#ffffff')]:
                color=ImageColor.getrgb(c.get(key,default))
                if len(color)!=3:raise ValueError('Gradient colors must be RGB colors without alpha.')

def apply(image,settings):
    validate(settings)
    if not any(c.get('enabled',False) for c in settings.values()):return image.copy()
    alpha=image.getchannel('A');rgb=image.convert('RGB')
    for name in ORDER:
        c=settings.get(name,{})
        if not c.get('enabled',False):continue
        if name=='curves':
            rgb=rgb.point(curve_lut(c.get('rgb',[[0,0],[255,255]]))*3)
            rgb=rgb.point(sum((curve_lut(c.get(ch,[[0,0],[255,255]])) for ch in ('r','g','b')),[]))
        elif name=='levels':
            black,white=c.get('black',0),c.get('white',255);gamma=c.get('gamma',1)
            lo,hi=c.get('out_black',0),c.get('out_white',255)
            lut=[round(lo+(hi-lo)*min(1,max(0,(x-black)/(white-black)))**(1/gamma)) for x in range(256)]
            rgb=rgb.point(lut*3)
        elif name=='hue_saturation':
            hue,sat=c.get('hue',0),c.get('saturation',0)
            if hue or sat:
                h,s,v=rgb.convert('HSV').split()
                h=h.point([(x+round(hue*255/360))%256 for x in range(256)])
                s=s.point([min(255,round(x*(1+sat/100))) for x in range(256)])
                rgb=Image.merge('HSV',(h,s,v)).convert('RGB')
        elif name=='invert':rgb=ImageOps.invert(rgb)
        elif name=='threshold':
            rgb=rgb.convert('L').point([255 if x>=c.get('value',128) else 0 for x in range(256)]).convert('RGB')
        elif name=='gradient_map':
            shadow=ImageColor.getrgb(c.get('shadow','#000000'));highlight=ImageColor.getrgb(c.get('highlight','#ffffff'));gray=rgb.convert('L')
            rgb=Image.merge('RGB',tuple(gray.point([round(a+(b-a)*x/255) for x in range(256)]) for a,b in zip(shadow,highlight)))
    rgb.putalpha(alpha);return rgb
