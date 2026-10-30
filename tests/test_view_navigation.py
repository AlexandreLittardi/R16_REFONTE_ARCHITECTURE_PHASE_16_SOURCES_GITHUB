"""View transforms never alter survey or diagram model coordinates."""
import unittest
from types import SimpleNamespace

from view_navigation import place_viewport, zoom_view
from mixins.zone_tools import ZoneToolsMixin
from PIL import Image


class StubCanvas:
    def __init__(self):
        self.width, self.height = 840, 620
        self.left = self.top = 0.
        self.region = (0.,0.,2400.,1500.)
    def winfo_width(self): return self.width
    def winfo_height(self): return self.height
    def canvasx(self, x): return self.left + x
    def canvasy(self, y): return self.top + y
    def bbox(self, tag): return (80.,-50.,1300.,800.)
    def configure(self, **kw):
        if 'scrollregion' in kw:self.region=kw['scrollregion']
    def xview_moveto(self, fraction):
        self.left=self.region[0]+fraction*(self.region[2]-self.region[0])
    def yview_moveto(self, fraction):
        self.top=self.region[1]+fraction*(self.region[3]-self.region[1])


class ViewNavigationTests(unittest.TestCase):
    def test_negative_origins_and_nonzero_scrollregion_preserve_world_anchor(self):
        c=StubCanvas()
        for left,top in [(300.,-430.),(-900.,120.),(3700.,2900.),(-3000.,-2000.)]:
            place_viewport(c,left,top)
            self.assertAlmostEqual(c.canvasx(0),left)
            self.assertAlmostEqual(c.canvasy(0),top)
            self.assertLessEqual(c.region[0],left)
            self.assertGreaterEqual(c.region[2],left+c.width)

    def test_zoom_world_point_is_stationary_and_model_unmodified(self):
        canvas=StubCanvas()
        model={'x':430.,'y':120.}
        m=SimpleNamespace(canvas=canvas,zoom_level=1.,cell_size_px=40,
            _auto_fit=True, _get_active_tab_index=lambda:7)
        def redraw():place_viewport(canvas,canvas.canvasx(0),canvas.canvasy(0),
                                     (0.,0.,1500*m.zoom_level,1100*m.zoom_level))
        m.draw_grid=redraw
        place_viewport(canvas,250.,115.)
        for zoom in (2.,.5,3.,.03,1.,4.):
            before=(canvas.canvasx(210)/m.zoom_level,canvas.canvasy(165)/m.zoom_level)
            zoom_view(m,zoom,210,165)
            after=(canvas.canvasx(210)/m.zoom_level,canvas.canvasy(165)/m.zoom_level)
            self.assertAlmostEqual(before[0],after[0],places=8)
            self.assertAlmostEqual(before[1],after[1],places=8)
            self.assertEqual(model,{'x':430.,'y':120.})
            self.assertFalse(m._auto_fit)

    def test_photo_crop_bounded_at_high_zoom(self):
        canvas=StubCanvas()
        m=SimpleNamespace(roof_pil_img=Image.new('RGB',(6000,4000)),canvas=canvas)
        canvas.left,canvas.top=3000.,2500.
        box=ZoneToolsMixin._installation_photo_crop(m,4.,offset=(0.,0.))
        self.assertLess((box[2]-box[0])*4, canvas.width+500)
        self.assertLess((box[3]-box[1])*4, canvas.height+500)
        self.assertIsNone(ZoneToolsMixin._installation_photo_crop(m,.1,offset=(0.,0.)))


if __name__=='__main__':unittest.main()
