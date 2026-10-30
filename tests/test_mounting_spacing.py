"""Generic local-axis clearances, no project-specific drawing constants."""
import math
from pathlib import Path
import tempfile
import unittest
from mounting_spacing import nearest_gaps
from mounting_drawing import write_svg
from mounting_installer import write_installer_pdf
from test_mounting import fixture


def panel(x,y,w,h,angle=0):
    t=math.radians(angle);c,s=math.cos(t),math.sin(t)
    return [(x+u*c-v*s,y+u*s+v*c) for u,v in ((0,0),(w,0),(w,h),(0,h))]


class MonochromeInstallerTests(unittest.TestCase):
    def test_right_bottom_clearance_generic(self):
        boxes={'a':{'number':1,'poly':panel(0,0,123,250)},
               'b':{'number':2,'poly':panel(134,0,123,250)},
               'c':{'number':3,'poly':panel(0,265,123,250)},
               'd':{'number':4,'poly':panel(450,450,123,250)}}
        gaps=nearest_gaps(boxes,.1)
        self.assertEqual(gaps['a']['u'][0],2)
        self.assertAlmostEqual(gaps['a']['u'][1],110)
        self.assertEqual(gaps['a']['v'][0],3)
        self.assertAlmostEqual(gaps['a']['v'][1],150)
        self.assertIsNone(gaps['d']['u'])
        self.assertIsNone(gaps['d']['v'])

    def test_rotation_and_oblique_not_guessed(self):
        t=31
        def r(dx,dy):
            a=math.radians(t)
            return dx*math.cos(a)-dy*math.sin(a), dx*math.sin(a)+dy*math.cos(a)
        x,y=r(99+13,0)
        boxes={'one':{'number':1,'poly':panel(0,0,99,211,t)},
               'two':{'number':2,'poly':panel(x,y,99,211,t)}}
        gaps=nearest_gaps(boxes,.2)
        self.assertAlmostEqual(gaps['one']['u'][1],65,places=4)
        self.assertIsNone(gaps['one']['v'])
        boxes['two']['poly']=panel(x,y,99,211,t+12)
        self.assertIsNone(nearest_gaps(boxes,.2)['one']['u'])

    def test_white_background_vector_export_pdf_schedule(self):
        import fitz
        app=fixture()
        app.roof_pil_img=object()  # should never be accessed in Montage
        with tempfile.TemporaryDirectory() as d:
            svg=Path(d)/'mono.svg'
            write_svg(app,svg)
            text=svg.read_text()
            self.assertNotIn('<image',text)
            self.assertNotIn('#8650b3',text)
            self.assertNotIn('#ec713e',text)
            pdf=Path(d)/'mono.pdf'
            result=write_installer_pdf(app,pdf)
            self.assertGreaterEqual(result['pages'],6)
            with fitz.open(pdf) as doc:
                content=' '.join(p.get_text() for p in doc)
                self.assertIn('MODULE-TO-MODULE GAPS',content)
                self.assertIn('197.0',content)  # fixture: gap = (150-130.3)/.1
                self.assertIn('CLAMP CONTACT COORDINATES',content)

if __name__=='__main__':unittest.main()
