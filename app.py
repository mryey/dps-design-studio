"""DPS Design Studio — native offline desktop editor, foundation release."""
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageOps
from engine import Project, Layer, History, text_image, dimensions
from adjustment_dialog import AdjustmentDialog
from warp_dialog import WarpDialog

class Studio:
    def __init__(self,root):
        self.root=root; self.project=Project(); self.history=History(); self.selected=None; self.path=None; self.dirty=False; self.drag=None
        root.title('DPS Design Studio • Foundation'); root.geometry('1240x820'); root.minsize(900,650)
        style=ttk.Style(); style.theme_use('clam')
        bar=ttk.Frame(root,padding=10); bar.pack(fill='x')
        ttk.Label(bar,text='DPS  DESIGN STUDIO',font=('Segoe UI',17,'bold')).pack(side='left',padx=(0,24))
        for name,fn in [('New',self.new),('Open',self.open),('Save',self.save),('Import image',self.import_image),('Add text',self.add_text),('Export PNG',self.export)]:
            ttk.Button(bar,text=name,command=lambda f=fn:self.safe(f)).pack(side='left',padx=3)
        body=ttk.Frame(root); body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=12,width=170); left.pack(side='left',fill='y')
        for name,fn in [('Undo',self.undo),('Redo',self.redo),('Canvas size',self.canvas_size),('Crop canvas',self.crop),('Duplicate layer',self.duplicate),('Flip horizontal',lambda:self.flip('flip_x')),('Flip vertical',lambda:self.flip('flip_y')),('Edit text',self.edit_text),('Adjustments',self.adjustments),('Warp text',self.warp_text),('Delete layer',self.delete)]:
            ttk.Button(left,text=name,command=lambda f=fn:self.safe(f)).pack(fill='x',pady=4)
        ttk.Label(left,text='Drag unlocked layers\nto position artwork.\n\nCheckerboard means\ntransparent pixels.\n\nCanvas fits to window.\nExport uses full size.',justify='left').pack(pady=25)
        self.canvas=tk.Canvas(body,bg='#242830',highlightthickness=0); self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.canvas.bind('<Button-1>',self.down); self.canvas.bind('<B1-Motion>',self.motion); self.canvas.bind('<ButtonRelease-1>',self.up)
        side=ttk.Frame(body,padding=12,width=260); side.pack(side='right',fill='y')
        ttk.Label(side,text='LAYERS • top first',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.list=tk.Listbox(side,height=9,exportselection=False,width=31); self.list.pack(fill='x',pady=8); self.list.bind('<<ListboxSelect>>',self.pick)
        row=ttk.Frame(side);row.pack(fill='x')
        for title,fn in [('↑',lambda:self.reorder(1)),('↓',lambda:self.reorder(-1)),('Show/hide',lambda:self.toggle('visible')),('Lock',lambda:self.toggle('locked'))]:
            ttk.Button(row,text=title,command=lambda f=fn:self.safe(f)).pack(side='left')
        self.fields={}
        for key,label in [('name','Name'),('x','X (pixels)'),('y','Y (pixels)'),('width','Width (inches)'),('height','Height (inches)'),('angle','Rotation (degrees)'),('opacity','Opacity (%)')]:
            ttk.Label(side,text=label).pack(anchor='w',pady=(9,0)); v=tk.StringVar();self.fields[key]=v;ttk.Entry(side,textvariable=v).pack(fill='x')
        ttk.Button(side,text='Apply layer changes',command=lambda:self.safe(self.apply)).pack(fill='x',pady=12)
        self.info=ttk.Label(side,text='',wraplength=235);self.info.pack(anchor='w')
        self.status=tk.StringVar();ttk.Label(root,textvariable=self.status,padding=8).pack(fill='x')
        root.protocol('WM_DELETE_WINDOW',self.close)
        for key,fn in [('<Control-s>',self.save),('<Control-o>',self.open),('<Control-z>',self.undo),('<Control-y>',self.redo)]:
            root.bind(key,lambda e,f=fn:self.shortcut(e,f))
        self.refresh()

    def shortcut(self,event,fn):
        if isinstance(event.widget,(tk.Entry,ttk.Entry,tk.Text)): return
        self.safe(fn);return 'break'
    def safe(self,fn):
        try: fn()
        except Exception as e: messagebox.showerror('DPS Design Studio',str(e))
    def change(self): self.history.push(self.project);self.dirty=True
    def layer(self):
        if self.selected is None or not 0<=self.selected<len(self.project.layers): raise ValueError('Select a layer first.')
        return self.project.layers[self.selected]
    def editable(self):
        l=self.layer()
        if l.locked: raise ValueError('Unlock this layer first.')
        return l
    def confirm(self):
        if not self.dirty:return True
        answer=messagebox.askyesnocancel('Unsaved project','Save your changes before continuing?')
        if answer is None:return False
        if answer:return self.save()
        return True
    def close(self):
        if self.confirm():self.root.destroy()
    def new(self):
        if not self.confirm():return
        self.project=Project();self.history=History();self.selected=None;self.path=None;self.dirty=False;self.refresh()
    def open(self):
        if not self.confirm():return
        path=filedialog.askopenfilename(filetypes=[('DPS projects','*.dps')])
        if not path:return
        p=Project.load(path);self.project=p;self.path=path;self.history=History();self.selected=None;self.dirty=False;self.refresh()
    def save(self):
        path=self.path or filedialog.asksaveasfilename(defaultextension='.dps',filetypes=[('DPS project','*.dps')])
        if not path:return False
        self.project.save(path);self.path=path;self.dirty=False;self.refresh();return True
    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('Transparent PNG','*.png')])
        if path:
            self.project.export(path);messagebox.showinfo('Export complete',f'Saved full-resolution transparent PNG.\n{self.project.width} × {self.project.height} pixels at {self.project.dpi} DPI.\nHidden layers are excluded.')
    def import_image(self):
        path=filedialog.askopenfilename(filetypes=[('Artwork','*.png *.jpg *.jpeg')])
        if not path:return
        if len(self.project.layers)>=100:raise ValueError('Maximum 100 layers.')
        with Image.open(path) as im:
            dimensions(im.width,im.height);im=ImageOps.exif_transpose(im).convert('RGBA')
        ratio=min(1,self.project.width/im.width,self.project.height/im.height)
        w,h=max(1,round(im.width*ratio)),max(1,round(im.height*ratio))
        self.change();self.project.layers.append(Layer(Path(path).stem,im,(self.project.width-w)/2,(self.project.height-h)/2,w,h));self.selected=len(self.project.layers)-1;self.refresh()
    def text_dialog(self,existing=None):
        top=tk.Toplevel(self.root);top.title('Text layer');top.transient(self.root);top.grab_set()
        meta=existing.text if existing else {}; result=[]; values={}
        for key,label,default in [('text','Text',meta.get('text','THE FIRE THAT REMEMBERS')),('size','Font size (pixels)',meta.get('size',160)),('font_path','Font file (optional .ttf/.otf)',meta.get('font_path','')),('color','Color (#hex)',meta.get('color','#000000'))]:
            ttk.Label(top,text=label).pack(anchor='w',padx=16,pady=(10,0));v=tk.StringVar(value=str(default));values[key]=v;ttk.Entry(top,textvariable=v,width=55).pack(padx=16)
        def font():
            p=filedialog.askopenfilename(parent=top,filetypes=[('Fonts','*.ttf *.otf')])
            if p:values['font_path'].set(p)
        def color():
            c=colorchooser.askcolor(parent=top)[1]
            if c:values['color'].set(c)
        ttk.Button(top,text='Choose font file',command=font).pack(pady=5);ttk.Button(top,text='Choose color',command=color).pack()
        def accept():
            try:
                d={k:v.get() for k,v in values.items()};d['size']=int(d['size']);im=text_image(**d);result.append((d,im));top.destroy()
            except Exception as e:messagebox.showerror('Text',str(e),parent=top)
        ttk.Button(top,text='Apply text',command=accept).pack(pady=16);self.root.wait_window(top);return result[0] if result else None
    def add_text(self):
        if len(self.project.layers)>=100:raise ValueError('Maximum 100 layers.')
        r=self.text_dialog()
        if not r:return
        d,im=r;self.change();self.project.layers.append(Layer(d['text'][:40],im,text=d));self.selected=len(self.project.layers)-1;self.refresh()
    def edit_text(self):
        l=self.editable()
        if not l.text:raise ValueError('This is an image layer. Select a text layer.')
        r=self.text_dialog(l)
        if r:
            d,im=r;self.change();l.text=d;l.image=im;l.width,l.height=im.size;l.name=d['text'][:40];self.refresh()
    def warp_text(self):
        l=self.editable()
        if not l.text:raise ValueError("Select a text layer to use Warp text.")
        dialog=WarpDialog(self.root,l)
        if dialog.result is not None:
            p=copy.deepcopy(self.project);p.layers[self.selected].warp=dialog.result;p.validate()
            self.change();self.project=p;self.refresh()

    def adjustments(self):
        l=self.editable();dialog=AdjustmentDialog(self.root,l)
        if dialog.result is not None:
            self.change();l.adjustments=dialog.result;self.refresh()

    def undo(self):
        if self.history.undo_stack:self.project=self.history.undo(self.project);self.dirty=True;self.selected=None;self.refresh()
    def redo(self):
        if self.history.redo_stack:self.project=self.history.redo(self.project);self.dirty=True;self.selected=None;self.refresh()
    def canvas_size(self):
        w=simpledialog.askfloat('Canvas','Width in inches:',initialvalue=self.project.width/self.project.dpi,minvalue=.01,maxvalue=120)
        if w is None:return
        h=simpledialog.askfloat('Canvas','Height in inches:',initialvalue=self.project.height/self.project.dpi,minvalue=.01,maxvalue=120)
        if h is None:return
        dpi=simpledialog.askinteger('Canvas','DPI:',initialvalue=self.project.dpi,minvalue=1,maxvalue=1200)
        if dpi is None:return
        width,height=round(w*dpi),round(h*dpi);dimensions(width,height)
        self.change();self.project.width,self.project.height,self.project.dpi=width,height,dpi;self.refresh()
    def crop(self):
        s=simpledialog.askstring('Crop canvas','Enter left, top, right, bottom in pixels.\nLayers stay editable; canvas bounds trim the export.',initialvalue=f'0, 0, {self.project.width}, {self.project.height}')
        if not s:return
        bounds=tuple(int(x.strip()) for x in s.split(','));p=copy.deepcopy(self.project);p.crop(*bounds);self.change();self.project=p;self.refresh()
    def duplicate(self):
        l=self.layer()
        if len(self.project.layers)>=100:raise ValueError('Maximum 100 layers.')
        self.change();l=copy.deepcopy(l);l.name+=' copy';l.x+=40;l.y+=40;self.project.layers.append(l);self.selected=len(self.project.layers)-1;self.refresh()
    def delete(self):
        self.editable();self.change();del self.project.layers[self.selected];self.selected=None;self.refresh()
    def flip(self,key):
        l=self.editable();self.change();setattr(l,key,not getattr(l,key));self.refresh()
    def toggle(self,key):
        l=self.layer();self.change();setattr(l,key,not getattr(l,key));self.refresh()
    def reorder(self,delta):
        self.editable();i=self.selected;j=i+delta
        if not 0<=j<len(self.project.layers):return
        self.change();self.project.layers[i],self.project.layers[j]=self.project.layers[j],self.project.layers[i];self.selected=j;self.refresh()
    def pick(self,event):
        s=self.list.curselection()
        if s:self.selected=len(self.project.layers)-1-s[0];self.populate();self.draw()
    def apply(self):
        l=self.editable();d={k:v.get() for k,v in self.fields.items()};candidate=copy.deepcopy(l)
        candidate.name=d['name'][:100]
        for k in ('x','y','angle'):setattr(candidate,k,float(d[k]))
        for k in ('width','height'):setattr(candidate,k,round(float(d[k])*self.project.dpi))
        candidate.opacity=float(d['opacity'])/100
        p=copy.deepcopy(self.project);p.layers[self.selected]=candidate;p.validate();self.change();self.project=p;self.refresh()
    def populate(self):
        if self.selected is None:
            for v in self.fields.values():v.set('')
            self.info.config(text='Select a layer to edit its properties.');return
        l=self.layer()
        for k,v in self.fields.items():
            n=getattr(l,k)
            if k in ('width','height'):n=round(n/self.project.dpi,4)
            elif k=='opacity':n=round(n*100,1)
            v.set(str(n))
        resolution=min(l.image.width/(l.width/self.project.dpi),l.image.height/(l.height/self.project.dpi))
        warning='\nBelow canvas target; check supplier requirements.' if resolution<self.project.dpi else ''
        self.info.config(text=f'Effective source resolution: {resolution:.0f} PPI{warning}\n'+('Locked' if l.locked else 'Unlocked'))
    def refresh(self):
        self.list.delete(0,'end')
        for l in reversed(self.project.layers):self.list.insert('end',('◉ ' if l.visible else '○ ')+('🔒 ' if l.locked else '')+l.name)
        if self.selected is not None and self.selected<len(self.project.layers):self.list.selection_set(len(self.project.layers)-1-self.selected)
        else:self.selected=None
        self.populate();self.draw();self.root.title(('● ' if self.dirty else '')+'DPS Design Studio • '+(Path(self.path).name if self.path else 'Untitled'))
        self.status.set(f'{self.project.width/self.project.dpi:g} × {self.project.height/self.project.dpi:g} inches  |  {self.project.width} × {self.project.height} pixels  |  {self.project.dpi} DPI  |  {len(self.project.layers)} layers  |  Local workspace')
    def draw(self):
        cw,ch=max(100,self.canvas.winfo_width()),max(100,self.canvas.winfo_height())
        self.scale=min((cw-40)/self.project.width,(ch-40)/self.project.height)
        w,h=max(1,round(self.project.width*self.scale)),max(1,round(self.project.height*self.scale));self.origin=((cw-w)/2,(ch-h)/2)
        bg=Image.new('RGBA',(w,h),'#ffffff');d=ImageDraw.Draw(bg)
        for y in range(0,h,16):
            for x in range(0,w,16):
                if (x//16+y//16)%2:d.rectangle((x,y,x+15,y+15),fill='#dce0e5')
        bg.alpha_composite(self.project.render(self.scale));self.preview=ImageTk.PhotoImage(bg);self.canvas.delete('all');self.canvas.create_image(*self.origin,image=self.preview,anchor='nw')
        if self.selected is not None:
            l=self.layer();im=l.rendered(self.scale);cx=self.origin[0]+(l.x+l.width/2)*self.scale;cy=self.origin[1]+(l.y+l.height/2)*self.scale
            self.canvas.create_rectangle(cx-im.width/2,cy-im.height/2,cx+im.width/2,cy+im.height/2,outline='#12a5d6',width=2)
    def down(self,e):
        x=(e.x-self.origin[0])/self.scale;y=(e.y-self.origin[1])/self.scale
        for i in range(len(self.project.layers)-1,-1,-1):
            l=self.project.layers[i]
            if not l.visible:continue
            # Test the transformed preview alpha, without allocating full-resolution transforms.
            im=l.rendered(self.scale);px=round((x-l.x-l.width/2)*self.scale+im.width/2);py=round((y-l.y-l.height/2)*self.scale+im.height/2)
            if 0<=px<im.width and 0<=py<im.height and im.getpixel((px,py))[3]>10:
                self.selected=i;self.refresh()
                if not l.locked:self.drag=(e.x,e.y,l.x,l.y,False)
                return
        self.selected=None;self.refresh()
    def motion(self,e):
        if not self.drag:return
        ex,ey,x,y,started=self.drag
        if not started:self.change();self.drag=(ex,ey,x,y,True)
        l=self.layer();l.x=x+(e.x-ex)/self.scale;l.y=y+(e.y-ey)/self.scale;self.draw()
    def up(self,e):
        self.drag=None;self.refresh()

if __name__=='__main__':
    root=tk.Tk();Studio(root);root.mainloop()
