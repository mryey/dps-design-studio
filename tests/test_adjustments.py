import tempfile
import unittest
from pathlib import Path
from PIL import Image
from adjustments import apply, curve_lut, validate, ORDER
from engine import Project, Layer, History

class AdjustmentTests(unittest.TestCase):
    def image(self,pixels):
        im=Image.new('RGBA',(len(pixels),1));im.putdata(pixels);return im
    def test_invert_exact_and_alpha(self):
        im=self.image([(10,80,200,77),(50,60,70,0)])
        self.assertEqual(list(apply(im,{'invert':{'enabled':True}}).getdata()),[(245,175,55,77),(205,195,185,0)])
    def test_threshold_boundary(self):
        im=self.image([(127,127,127,100),(128,128,128,200)])
        self.assertEqual(list(apply(im,{'threshold':{'enabled':True,'value':128}}).getdata()),[(0,0,0,100),(255,255,255,200)])
    def test_levels_clipping_and_midpoint(self):
        im=self.image([(20,20,20,255),(120,120,120,255),(220,220,220,255)])
        c={'enabled':True,'black':20,'white':220,'gamma':1,'out_black':10,'out_white':210}
        self.assertEqual([p[0] for p in apply(im,{'levels':c}).getdata()],[10,110,210])
    def test_levels_gamma_brightens(self):
        im=self.image([(64,64,64,255)])
        self.assertAlmostEqual(apply(im,{'levels':{'enabled':True,'gamma':2}}).getpixel((0,0))[0],128,delta=1)
    def test_curve_anchor_and_channel(self):
        self.assertEqual(curve_lut([[0,0],[128,200],[255,255]])[128],200)
        im=self.image([(128,128,128,90)])
        out=apply(im,{'curves':{'enabled':True,'r':[[0,0],[128,200],[255,255]]}})
        self.assertEqual(out.getpixel((0,0)),(200,128,128,90))
    def test_hue_red_to_green(self):
        im=self.image([(255,0,0,155)])
        r,g,b,a=apply(im,{'hue_saturation':{'enabled':True,'hue':120}}).getpixel((0,0))
        self.assertLess(r,8);self.assertGreater(g,247);self.assertLess(b,8);self.assertEqual(a,155)
    def test_saturation_minus_100_is_neutral(self):
        im=self.image([(100,200,50,155)])
        r,g,b,a=apply(im,{'hue_saturation':{'enabled':True,'saturation':-100}}).getpixel((0,0))
        self.assertEqual(r,g);self.assertEqual(g,b);self.assertEqual(a,155)
    def test_gradient_endpoints_and_midpoint(self):
        im=self.image([(0,0,0,90),(255,255,255,100),(128,128,128,110)])
        out=apply(im,{'gradient_map':{'enabled':True,'shadow':'#ff0000','highlight':'#0000ff'}})
        self.assertEqual(list(out.getdata()),[(255,0,0,90),(0,0,255,100),(127,0,128,110)])
    def test_all_defaults_identity(self):
        im=self.image([(10,40,190,123)])
        self.assertEqual(apply(im,{name:{'enabled':True} for name in ORDER if name not in ('invert','threshold','gradient_map')}).tobytes(),im.tobytes())
    def test_all_adjustments_preserve_source_and_alpha(self):
        im=self.image([(10,20,30,0),(40,50,60,77),(70,80,90,255)]);before=im.tobytes()
        for name in ORDER:
            out=apply(im,{name:{'enabled':True}})
            self.assertEqual(out.getchannel('A').tobytes(),im.getchannel('A').tobytes());self.assertEqual(im.tobytes(),before)
    def test_settings_roundtrip_export_and_undo(self):
        l=Layer('a',self.image([(10,20,30,100)]));p=Project(1,1,layers=[l]);h=History();h.push(p);l.adjustments={'invert':{'enabled':True}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'a.dps';p.save(path);q=Project.load(path);self.assertEqual(q.layers[0].adjustments,l.adjustments)
            q.export(Path(d)/'out.png')
            with Image.open(Path(d)/'out.png') as im:self.assertEqual(im.getpixel((0,0)),(245,235,225,100))
        p=h.undo(p);self.assertEqual(p.render().getpixel((0,0)),(10,20,30,100))
    def test_reject_invalid_settings(self):
        for c in [{'levels':{'black':200,'white':100}},{'levels':{'gamma':0}},{'curves':{'rgb':[[0,0],[0,255]]}},{'hue_saturation':{'hue':float('nan')}},{'gradient_map':{'shadow':'not a color'}},{'threshold':{'value':'128'}}]:
            with self.assertRaises(ValueError):validate(c)
    def test_fixed_order_invert_before_threshold(self):
        im=self.image([(100,100,100,255)])
        out=apply(im,{'threshold':{'enabled':True},'invert':{'enabled':True}})
        self.assertEqual(out.getpixel((0,0)),(255,255,255,255))
    def test_old_project_without_adjustments_opens(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'old.dps';Project(1,1,layers=[Layer('a',self.image([(1,2,3,255)]))]).save(path)
            raw=json.loads(path.read_text());raw['layers'][0].pop('adjustments');path.write_text(json.dumps(raw))
            self.assertEqual(Project.load(path).render().getpixel((0,0)),(1,2,3,255))

if __name__=='__main__':unittest.main()
