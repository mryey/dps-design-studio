import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
from text_warp import apply, validate, STYLES

class WarpDialog:
    def __init__(self,parent,layer):
        self.result=None;self.pending=None
        self.top=tk.Toplevel(parent);self.top.title('Warp text — '+layer.name);self.top.transient(parent);self.top.grab_set();self.top.protocol('WM_DELETE_WINDOW',self.cancel)
        ttk.Label(self.top,text='WARP TEXT',font=('Segoe UI',14,'bold'),padding=12).pack()
        row=ttk.Frame(self.top,padding=12);row.pack(fill='x')
        self.style=tk.StringVar(value=layer.warp.get('style','Arc'));self.bend=tk.DoubleVar(value=layer.warp.get('bend',0))
        ttk.Label(row,text='Style').pack(anchor='w');ttk.Combobox(row,textvariable=self.style,values=STYLES,state='readonly').pack(fill='x')
        ttk.Label(row,text='Bend (-100 to 100)').pack(anchor='w',pady=(12,0));ttk.Scale(row,from_=-100,to=100,variable=self.bend).pack(fill='x');ttk.Entry(row,textvariable=self.bend,width=12).pack()
        self.preview=tk.Canvas(self.top,width=560,height=320,bg='#242830',highlightthickness=0);self.preview.pack(padx=12)
        self.error=tk.StringVar();ttk.Label(self.top,textvariable=self.error,foreground='#aa2222',wraplength=540).pack()
        ttk.Label(self.top,text='Positive and negative bend give opposite shapes. Zero removes warp.\nText stays editable. Size fields refer to the text before warp.',padding=12).pack()
        buttons=ttk.Frame(self.top,padding=12);buttons.pack(fill='x');ttk.Button(buttons,text='Reset',command=lambda:self.bend.set(0)).pack(side='left');ttk.Button(buttons,text='Cancel',command=self.cancel).pack(side='right');ttk.Button(buttons,text='Apply',command=self.accept).pack(side='right',padx=8)
        # Use the layer's displayed proportions and existing adjustments in the preview.
        from adjustments import apply as adjust
        scale=min(1,460/layer.width,160/layer.height)
        self.source=adjust(layer.image.resize((max(1,round(layer.width*scale)),max(1,round(layer.height*scale))),Image.Resampling.LANCZOS),layer.adjustments)
        for v in (self.style,self.bend):v.trace_add('write',lambda *args:self.schedule())
        self.update();parent.wait_window(self.top)
    def settings(self):
        d={'style':self.style.get(),'bend':self.bend.get()};validate(d);return d
    def schedule(self):
        if self.pending:self.top.after_cancel(self.pending)
        self.pending=self.top.after(120,self.update)
    def update(self):
        self.pending=None
        try:
            im=apply(self.source,self.settings());im.thumbnail((540,300),Image.Resampling.LANCZOS)
            bg=Image.new('RGBA',im.size,'white');d=ImageDraw.Draw(bg)
            for y in range(0,im.height,12):
                for x in range(0,im.width,12):
                    if (x//12+y//12)%2:d.rectangle((x,y,x+11,y+11),fill='#dce0e5')
            bg.alpha_composite(im);self.photo=ImageTk.PhotoImage(bg);self.preview.delete('all');self.preview.create_image(280,160,image=self.photo);self.error.set('')
        except Exception as e:self.error.set(str(e))
    def cancel(self):
        if self.pending:self.top.after_cancel(self.pending)
        self.top.destroy()
    def accept(self):
        try:self.result=self.settings()
        except Exception as e:messagebox.showerror('Warp text',str(e),parent=self.top);return
        self.cancel()
