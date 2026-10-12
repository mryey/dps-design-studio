"""Local RGBA project engine. No network or executable project content."""
import base64
import copy
import io
import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from adjustments import apply as apply_adjustments, validate as validate_adjustments
from text_warp import apply as apply_warp, validate as validate_warp, geometry as warp_geometry
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

MAX_PIXELS = 40_000_000
MAX_PROJECT_BYTES = 100_000_000

def dimensions(w, h):
    if not isinstance(w, int) or not isinstance(h, int) or w < 1 or h < 1 or w*h > MAX_PIXELS:
        raise ValueError('Dimensions must be positive whole pixels, at most 40 million pixels total.')

def atomic_write(path, content):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

@dataclass
class Layer:
    name: str
    image: Image.Image
    x: float = 0
    y: float = 0
    width: int = 0
    height: int = 0
    angle: float = 0
    opacity: float = 1
    visible: bool = True
    locked: bool = False
    flip_x: bool = False
    flip_y: bool = False
    text: dict | None = None
    adjustments: dict = field(default_factory=dict)
    warp: dict = field(default_factory=dict)

    def __post_init__(self):
        self.image = self.image.convert('RGBA')
        if not self.width: self.width = self.image.width
        if not self.height: self.height = self.image.height

    def rendered(self, scale=1):
        im = self.image.resize((max(1, round(self.width*scale)), max(1, round(self.height*scale))), Image.Resampling.LANCZOS)
        im = apply_adjustments(im, self.adjustments)
        if self.text: im = apply_warp(im, self.warp)
        if self.flip_x: im = ImageOps.mirror(im)
        if self.flip_y: im = ImageOps.flip(im)
        if self.angle: im = im.rotate(self.angle, Image.Resampling.BICUBIC, expand=True)
        if self.opacity < 1: im.putalpha(im.getchannel('A').point(lambda a: round(a*self.opacity)))
        return im

def text_image(text, font_path, size, color):
    if not text.strip(): raise ValueError('Enter some text.')
    if not 1 <= size <= 2000: raise ValueError('Font size must be 1–2000 pixels.')
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default(size=size)
    bbox = ImageDraw.Draw(Image.new('RGBA', (1,1))).multiline_textbbox((0,0), text, font=font)
    w, h = max(1, bbox[2]-bbox[0]+8), max(1, bbox[3]-bbox[1]+8)
    dimensions(w,h)
    im = Image.new('RGBA', (w,h))
    ImageDraw.Draw(im).multiline_text((4-bbox[0],4-bbox[1]), text, font=font, fill=color)
    return im

@dataclass
class Project:
    width: int = 3600
    height: int = 4200
    dpi: int = 300
    layers: list = field(default_factory=list)

    def validate(self):
        dimensions(self.width,self.height)
        if not isinstance(self.dpi,int) or not 1 <= self.dpi <= 1200: raise ValueError('DPI must be 1–1200.')
        if len(self.layers)>100: raise ValueError('Maximum 100 layers.')
        for l in self.layers:
            dimensions(l.width,l.height)
            validate_adjustments(l.adjustments)
            validate_warp(l.warp)
            if l.text and l.warp.get("bend",0):warp_geometry(l.width,l.height,l.warp.get("style","Arc"),l.warp["bend"])
            if not all(math.isfinite(v) for v in (l.x,l.y,l.angle,l.opacity)): raise ValueError('Invalid layer values.')
            if not 0<=l.opacity<=1: raise ValueError('Invalid opacity.')

    def render(self, scale=1):
        self.validate()
        out=Image.new('RGBA',(max(1,round(self.width*scale)),max(1,round(self.height*scale))))
        for l in self.layers:
            if not l.visible: continue
            im=l.rendered(scale)
            # x/y identify the unrotated top-left; rotate about the layer center.
            x=round((l.x+l.width/2)*scale-im.width/2)
            y=round((l.y+l.height/2)*scale-im.height/2)
            out.alpha_composite(im,(x,y))
        return out

    def save(self,path):
        self.validate()
        layers=[]
        for l in self.layers:
            b=io.BytesIO(); l.image.save(b,format='PNG')
            d={k:v for k,v in vars(l).items() if k!='image'}
            d['image']=base64.b64encode(b.getvalue()).decode('ascii'); layers.append(d)
        data=json.dumps(dict(format='DPS-STUDIO',version=1,width=self.width,height=self.height,dpi=self.dpi,layers=layers)).encode()
        if len(data)>MAX_PROJECT_BYTES: raise ValueError('Project exceeds the 100 MB limit.')
        atomic_write(path,data)

    @classmethod
    def load(cls,path):
        if Path(path).stat().st_size>MAX_PROJECT_BYTES: raise ValueError('Project exceeds the 100 MB limit.')
        d=json.loads(Path(path).read_text(encoding='utf8'))
        if d.get('format')!='DPS-STUDIO' or d.get('version')!=1: raise ValueError('Not a supported DPS project.')
        p=cls(d['width'],d['height'],d['dpi']); p.validate()
        if not isinstance(d['layers'],list) or len(d['layers'])>100: raise ValueError('Invalid layer list.')
        for raw in d['layers']:
            raw=dict(raw)
            blob=base64.b64decode(raw.pop('image'),validate=True)
            with Image.open(io.BytesIO(blob)) as im:
                dimensions(im.width,im.height); image=im.convert('RGBA')
            p.layers.append(Layer(image=image,**raw))
        p.validate(); return p

    def export(self,path):
        b=io.BytesIO(); self.render().save(b,format='PNG',dpi=(self.dpi,self.dpi)); atomic_write(path,b.getvalue())

    def crop(self,left,top,right,bottom):
        if not all(isinstance(v,int) for v in (left,top,right,bottom)) or not 0<=left<right<=self.width or not 0<=top<bottom<=self.height:
            raise ValueError('Crop coordinates must be inside the canvas.')
        self.width,self.height=right-left,bottom-top
        for l in self.layers: l.x-=left; l.y-=top

class History:
    def __init__(self): self.undo_stack=[]; self.redo_stack=[]
    def push(self,p):
        self.undo_stack.append(copy.deepcopy(p)); self.undo_stack=self.undo_stack[-12:]; self.redo_stack.clear()
    def undo(self,p):
        if not self.undo_stack: return p
        self.redo_stack.append(copy.deepcopy(p)); return self.undo_stack.pop()
    def redo(self,p):
        if not self.redo_stack: return p
        self.undo_stack.append(copy.deepcopy(p)); return self.redo_stack.pop()
