import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine import Project, Layer, History, text_image

class EngineTests(unittest.TestCase):
    def test_export_transparency_dimensions_dpi_and_layer_order(self):
        p=Project(30,20,300,[Layer('red',Image.new('RGBA',(10,10),'red'),5,5),Layer('blue',Image.new('RGBA',(5,5),'blue'),5,5)])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'out.png';p.export(path)
            with Image.open(path) as im:
                self.assertEqual(im.size,(30,20));self.assertEqual(im.getpixel((0,0)),(0,0,0,0));self.assertEqual(im.getpixel((6,6)),(0,0,255,255));self.assertAlmostEqual(im.info['dpi'][0],300,places=1)
    def test_save_open_preserves_pixels_and_properties(self):
        p=Project(40,30,150,[Layer('art',Image.new('RGBA',(8,5),(0,90,180,200)),3,4,16,10,angle=32,opacity=.5,locked=True,flip_x=True)])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'order.dps';p.save(path);q=Project.load(path)
            self.assertEqual(p.render().tobytes(),q.render().tobytes());self.assertTrue(q.layers[0].locked);self.assertEqual(q.dpi,150)
    def test_history_after_transform(self):
        p=Project(20,20,layers=[Layer('art',Image.new('RGBA',(2,2),'white'))]);h=History();h.push(p);p.layers[0].x=8
        p=h.undo(p);self.assertEqual(p.layers[0].x,0);p=h.redo(p);self.assertEqual(p.layers[0].x,8)
    def test_hidden_and_opacity(self):
        p=Project(5,5,layers=[Layer('a',Image.new('RGBA',(5,5),'red'),opacity=.5)])
        self.assertEqual(p.render().getpixel((0,0))[3],128);p.layers[0].visible=False;self.assertEqual(p.render().getbbox(),None)
    def test_crop_shifts_layers_and_clips_export(self):
        p=Project(20,20,layers=[Layer('a',Image.new('RGBA',(10,10),'red'),5,5)]);p.crop(6,6,12,12)
        self.assertEqual(p.render().size,(6,6));self.assertEqual(p.render().getpixel((0,0)),(255,0,0,255));self.assertEqual(p.layers[0].x,-1)
    def test_flip_preserves_source_and_changes_output(self):
        im=Image.new('RGBA',(2,1));im.putpixel((0,0),(255,0,0,255));l=Layer('a',im,flip_x=True)
        self.assertEqual(l.rendered().getpixel((1,0)),(255,0,0,255));self.assertEqual(l.image.getpixel((0,0)),(255,0,0,255))
    def test_text_raster_is_embedded_and_can_reopen(self):
        meta=dict(text='DPS',font_path='',size=40,color='#ffffff');im=text_image(**meta);p=Project(200,100,layers=[Layer('DPS',im,text=meta)])
        self.assertIsNotNone(im.getbbox())
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'text.dps';p.save(path);q=Project.load(path);self.assertEqual(q.layers[0].text,meta);self.assertEqual(p.render().tobytes(),q.render().tobytes())
    def test_invalid_project_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'order.dps';p=Project(10,10);p.save(path);before=path.read_bytes();p.width=-1
            with self.assertRaises(ValueError):p.save(path)
            self.assertEqual(path.read_bytes(),before)
    def test_large_canvas_rejected(self):
        with self.assertRaises(ValueError):Project(6600,36000).validate()
    def test_rotation_and_negative_position(self):
        p=Project(10,10,layers=[Layer('a',Image.new('RGBA',(6,2),'red'),-1,0,angle=90)])
        self.assertIsNotNone(p.render().getbbox());self.assertEqual(p.render().size,(10,10))

if __name__=='__main__':unittest.main()
