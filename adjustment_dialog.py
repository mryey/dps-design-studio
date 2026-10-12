"""Tabbed adjustment controls with a local preview; Cancel leaves the layer unchanged."""
import copy
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from PIL import Image, ImageTk, ImageDraw
from adjustments import apply, validate, curve_lut, ORDER

class AdjustmentDialog:
    def __init__(self,parent,layer):
        self.result=None;self.layer=layer;self.pending=None;self.values={};self.enabled={}
        self.top=tk.Toplevel(parent);self.top.title('Layer adjustments — '+layer.name);self.top.transient(parent);self.top.grab_set()
        self.top.protocol('WM_DELETE_WINDOW',self.cancel)
        ttk.Label(self.top,text='Editable per-layer adjustments • Original artwork is preserved',padding=12).pack()
        body=ttk.Frame(self.top);body.pack(fill='both',expand=True,padx=12)
        notebook=ttk.Notebook(body);notebook.pack(side='left',fill='both',expand=True)
        titles=['Curves','Levels','Hue / Saturation','Invert','Threshold','Gradient Map'];self.tabs={}
        for name,title in zip(ORDER,titles):
            f=ttk.Frame(notebook,padding=12);notebook.add(f,text=title);self.tabs[name]=f
            v=tk.BooleanVar(value=layer.adjustments.get(name,{}).get('enabled',False));self.enabled[name]=v
            ttk.Checkbutton(f,text='Enable '+title,variable=v,command=self.schedule).pack(anchor='w',pady=(0,10))
        self.curve_channel=tk.StringVar(value='rgb');self.curves={}
        for ch in ('rgb','r','g','b'):
            pts=layer.adjustments.get('curves',{}).get(ch,[[0,0],[255,255]])
            self.curves[ch]=tk.StringVar(value='; '.join(f'{x:g},{y:g}' for x,y in pts))
        f=self.tabs['curves'];ttk.Label(f,text='Channel').pack(anchor='w');select=ttk.Combobox(f,textvariable=self.curve_channel,values=['rgb','r','g','b'],state='readonly');select.pack(fill='x');select.bind('<<ComboboxSelected>>',lambda e:self.select_curve())
        self.graph=tk.Canvas(f,width=280,height=280,bg='#242830',highlightthickness=0);self.graph.pack(pady=8);self.graph.bind('<Button-1>',self.curve_click);self.graph.bind('<Button-3>',self.curve_remove)
        self.curve_entry=ttk.Entry(f,width=42);self.curve_entry.pack(fill='x')
        ttk.Label(f,text='Click graph to add/update a point.\nRight-click near a point to remove it.\nCoordinates: input,output; input,output\nStraight segments connect points.',justify='left').pack(anchor='w',pady=8)
        for v in self.curves.values():v.trace_add('write',lambda *a:self.schedule())
        self.select_curve()
        for key,label,default,low,high in [('black','Input black',0,0,254),('gamma','Midtone gamma',1,.1,10),('white','Input white',255,1,255),('out_black','Output black',0,0,255),('out_white','Output white',255,0,255)]:self.control('levels',key,label,default,low,high)
        self.control('hue_saturation','hue','Hue shift (degrees)',0,-180,180);self.control('hue_saturation','saturation','Saturation (%)',0,-100,100)
        ttk.Label(self.tabs['invert'],text='Inverts RGB colors.\nTransparency stays unchanged.').pack(anchor='w')
        self.control('threshold','value','Black / white cutoff',128,0,255)
        for key,label,default in [('shadow','Shadow color','#000000'),('highlight','Highlight color','#ffffff')]:
            f=self.tabs['gradient_map'];ttk.Label(f,text=label).pack(anchor='w');v=tk.StringVar(value=layer.adjustments.get('gradient_map',{}).get(key,default));self.values['gradient_map',key]=v
            ttk.Entry(f,textvariable=v).pack(fill='x');ttk.Button(f,text='Choose '+label.lower(),command=lambda k=key:self.color(k)).pack(pady=6);v.trace_add('write',lambda *a:self.schedule())
        ttk.Label(self.tabs['gradient_map'],text='Two-color map based on luminance.').pack(anchor='w')
        side=ttk.Frame(body,padding=12);side.pack(side='right',fill='y');ttk.Label(side,text='Combined preview').pack();self.preview=ttk.Label(side);self.preview.pack(pady=8)
        self.error=tk.StringVar();ttk.Label(side,textvariable=self.error,wraplength=260,foreground='#aa2222').pack()
        ttk.Label(side,text='Order: Curves → Levels →\nHue/Saturation → Invert →\nThreshold → Gradient Map.\n\nPreview is reduced in size.\nExport applies the same settings\nat full resolution.',justify='left').pack(pady=12)
        row=ttk.Frame(self.top,padding=12);row.pack(fill='x');ttk.Button(row,text='Reset all',command=self.reset).pack(side='left');ttk.Button(row,text='Cancel',command=self.cancel).pack(side='right');ttk.Button(row,text='Apply',command=self.accept).pack(side='right',padx=8)
        self.source=layer.image.copy();self.source.thumbnail((280,320),Image.Resampling.LANCZOS);self.update_preview();parent.wait_window(self.top)
    def control(self,name,key,label,default,low,high):
        f=self.tabs[name];ttk.Label(f,text=label).pack(anchor='w',pady=(8,0));v=tk.DoubleVar(value=self.layer.adjustments.get(name,{}).get(key,default));self.values[name,key]=v
        row=ttk.Frame(f);row.pack(fill='x');ttk.Scale(row,from_=low,to=high,variable=v,command=lambda x:self.schedule()).pack(side='left',fill='x',expand=True);ttk.Entry(row,textvariable=v,width=9).pack(side='right');v.trace_add('write',lambda *a:self.schedule())
    def color(self,key):
        c=colorchooser.askcolor(parent=self.top)[1]
        if c:self.values['gradient_map',key].set(c)
    def select_curve(self):
        self.curve_entry.config(textvariable=self.curves[self.curve_channel.get()]);self.draw_curve()
    def points(self,ch):
        return [[float(x.strip()) for x in p.split(',')] for p in self.curves[ch].get().split(';')]
    def draw_curve(self):
        self.graph.delete('all');self.graph.create_line(12,268,268,12,fill='#666666')
        try:
            pts=self.points(self.curve_channel.get());curve_lut(pts)
            coords=[n for x,y in pts for n in (12+x,268-y)];self.graph.create_line(*coords,fill='#43c5ef',width=2)
            for x,y in pts:self.graph.create_oval(9+x,265-y,15+x,271-y,fill='white')
        except (ValueError,IndexError):pass
    def curve_click(self,e):
        try:pts=self.points(self.curve_channel.get());curve_lut(pts)
        except (ValueError,IndexError):pts=[[0,0],[255,255]]
        x=max(0,min(255,e.x-12));y=max(0,min(255,268-e.y));nearest=min(range(len(pts)),key=lambda i:abs(pts[i][0]-x))
        if abs(pts[nearest][0]-x)<=8:pts[nearest][1]=y
        elif len(pts)<32:pts.append([x,y]);pts.sort()
        self.curves[self.curve_channel.get()].set('; '.join(f'{a:g},{b:g}' for a,b in pts));self.enabled['curves'].set(True);self.schedule()
    def curve_remove(self,e):
        try:
            pts=self.points(self.curve_channel.get());x=e.x-12;i=min(range(len(pts)),key=lambda i:abs(pts[i][0]-x))
            if 0<i<len(pts)-1 and abs(pts[i][0]-x)<=10:del pts[i];self.curves[self.curve_channel.get()].set('; '.join(f'{a:g},{b:g}' for a,b in pts))
        except (ValueError,IndexError):pass
    def settings(self):
        d={name:{'enabled':v.get()} for name,v in self.enabled.items()}
        for (name,key),v in self.values.items():d[name][key]=v.get()
        for ch in self.curves:d['curves'][ch]=self.points(ch)
        validate(d);return d
    def schedule(self):
        if self.pending:self.top.after_cancel(self.pending)
        self.pending=self.top.after(120,self.update_preview)
    def update_preview(self):
        self.pending=None;self.draw_curve()
        if not hasattr(self,'source'):return
        try:
            im=apply(self.source,self.settings());bg=Image.new('RGBA',im.size,'white');draw=ImageDraw.Draw(bg)
            for y in range(0,im.height,12):
                for x in range(0,im.width,12):
                    if (x//12+y//12)%2:draw.rectangle((x,y,x+11,y+11),fill='#dce0e5')
            bg.alpha_composite(im);self.photo=ImageTk.PhotoImage(bg);self.preview.config(image=self.photo);self.error.set('')
        except Exception as e:self.error.set(str(e))
    def reset(self):
        for v in self.enabled.values():v.set(False)
        for v in self.curves.values():v.set('0,0; 255,255')
        defaults={'black':0,'white':255,'gamma':1,'out_black':0,'out_white':255,'hue':0,'saturation':0,'value':128,'shadow':'#000000','highlight':'#ffffff'}
        for (name,key),v in self.values.items():v.set(defaults[key])
        self.schedule()
    def cancel(self):
        if self.pending:self.top.after_cancel(self.pending)
        self.top.destroy()
    def accept(self):
        try:self.result=copy.deepcopy(self.settings())
        except Exception as e:messagebox.showerror('Adjustments',str(e),parent=self.top);return
        self.cancel()
