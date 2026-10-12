import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine import Layer, Project, History, text_image
from text_warp import apply, validate, STYLES

class WarpTests(unittest.TestCase):
    def source(self):
        im=Image.new('RGBA',(120,24));im.paste((255,255,255,255),(4,4,116,20));return im
    def test_zero_is_exact_identity(self):
        im=self.source()
        for style in STYLES:self.assertEqual(apply(im,{'style':style,'bend':0}).tobytes(),im.tobytes())
    def test_each_preset_changes_shape_preserves_source_and_transparent_border(self):
        im=self.source();before=im.tobytes()
        for style in STYLES:
            for bend in (-65,65):
                out=apply(im,{'style':style,'bend':bend})
                self.assertEqual(out.mode,'RGBA');self.assertIsNotNone(out.getbbox());self.assertEqual(out.getpixel((0,0))[3],0);self.assertNotEqual(out.size,im.size);self.assertEqual(im.tobytes(),before)
    def test_arch_center_moves_relative_to_ends(self):
        im=self.source();out=apply(im,{'style':'Arch','bend':80})
        alpha=out.getchannel('A')
        center=alpha.crop((out.width//2,0,out.width//2+1,out.height)).getbbox()
        edge=alpha.crop((10,0,11,out.height)).getbbox()
        self.assertLess(center[1],edge[1])
    def test_negative_arch_reverses_shape(self):
        im=self.source();out=apply(im,{'style':'Arch','bend':-80});alpha=out.getchannel('A')
        center=alpha.crop((out.width//2,0,out.width//2+1,out.height)).getbbox();edge=alpha.crop((10,0,11,out.height)).getbbox()
        self.assertGreater(center[1],edge[1])
    def test_arc_tall_text_does_not_fold(self):
        out=apply(Image.new('RGBA',(20,100),'white'),{'style':'Arc','bend':100})
        self.assertIsNotNone(out.getbbox())
    def test_warp_save_open_export_and_history(self):
        meta={'text':'DPS','font_path':'','size':40,'color':'white'};im=text_image(**meta);p=Project(300,200,layers=[Layer('text',im,80,80,text=meta)]);h=History();h.push(p)
        p.layers[0].warp={'style':'Arc','bend':65}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'a.dps';p.save(path);q=Project.load(path);self.assertEqual(q.layers[0].warp,p.layers[0].warp);self.assertEqual(q.render().tobytes(),p.render().tobytes());q.export(Path(d)/'out.png')
            with Image.open(Path(d)/'out.png') as out:self.assertEqual(out.tobytes(),q.render().tobytes())
        p=h.undo(p);self.assertEqual(p.layers[0].warp,{})
    def test_text_remains_editable(self):
        meta={'text':'DPS','font_path':'','size':40,'color':'white'};l=Layer('text',text_image(**meta),text=meta,warp={'style':'Wave','bend':50});before=l.rendered().tobytes()
        meta['text']='STUDIO';l.image=text_image(**meta);l.width,l.height=l.image.size
        self.assertNotEqual(before,l.rendered().tobytes());self.assertEqual(l.warp['style'],'Wave')
    def test_invalid_settings(self):
        for s in [{'style':'Unknown'},{'bend':101},{'bend':float('nan')},{'bend':'25'}]:
            with self.assertRaises(ValueError):validate(s)

if __name__=='__main__':unittest.main()
