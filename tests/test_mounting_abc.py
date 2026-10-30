"""Six-clamp top-origin placement: two fixings per independently set A/B/C."""
import copy
import math
import tempfile
from pathlib import Path
import unittest

from mounting import (default_config, validate_config, validate_plan, fixings,
                      set_fixing_position, station_positions)
from mounting_drawing import geometry, construction_shapes
from mounting_installer import write_installer_pdf
from project_store import write_project, validate_project
from test_mounting import fixture


class SixTopOffsetsTests(unittest.TestCase):
    def abc(self):
        c=default_config(1303,2384)
        c.update(count=6,top_offsets_mm=[480,1150,1920])
        return validate_config(c)

    def test_independent_top_distances_and_paired_fixings(self):
        c=self.abc()
        self.assertEqual(station_positions(c),[480.,1150.,1920.])
        self.assertEqual([f['position_mm'] for f in fixings(c)],
                         [480,480,1150,1150,1920,1920])
        self.assertEqual([f['x'] for f in fixings(c)],[0,1303]*3)
        self.assertEqual([f['y'] for f in fixings(c)],[480,480,1150,1150,1920,1920])
        before=copy.deepcopy(c)
        moved=set_fixing_position(c,3,1200)
        self.assertEqual(c,before,'The edit must be transactional')
        self.assertEqual(validate_config(moved)['top_offsets_mm'],[480,1200,1920])
        self.assertEqual([f['position_mm'] for f in fixings(moved)][2:4],[1200,1200])
        moved=set_fixing_position(moved,0,520)
        self.assertEqual([f['position_mm'] for f in fixings(moved)][:2],[520,520])

    def test_invalid_abc_rejected_and_legacy_count6_unaffected(self):
        for abc in ([500,450,1500],[20,1000,1500],[500,1000,2380],
                    [500,520,1800],[500,1000],['a',1100,1900],
                    [float('nan'),1100,1900],[500,1100,float('inf')]):
            with self.subTest(abc=abc),self.assertRaises(ValueError):
                validate_config(dict(self.abc(),top_offsets_mm=abc))
        c=default_config(1303,2384)
        c.update(count=6,a_mm=490,b_mm=490)
        old=validate_config(c)
        self.assertEqual([f['position_mm'] for f in fixings(old)],
                         [490,490,1192,1192,1894,1894])
        self.assertNotIn('top_offsets_mm',old)
        with self.assertRaises(ValueError):validate_config(dict(self.abc(),count=4))

    def test_plan_roundtrip_and_live_dimensions(self):
        app=fixture()
        app.mounting_plan['panels']['one']=self.abc()
        original=copy.deepcopy(app.mounting_plan)
        serialized=validate_plan(original)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'abc.json'
            write_project(path,{'mounting_plan':serialized})
            import json
            loaded=validate_project(json.loads(path.read_text()))
            self.assertEqual(loaded['mounting_plan']['panels']['one']['top_offsets_mm'],[480,1150,1920])
        app.selected_panel_coords={(0,0)}
        shapes=construction_shapes(app,geometry(app),font=8,selected=app.selected_panel_coords)
        labels=[s['text'] for s in shapes if s['kind']=='text']
        for label in ('A = 480.0 mm','B = 1150.0 mm','C = 1920.0 mm'):
            self.assertIn(label,labels)
        app.mounting_plan['panels']['one']=set_fixing_position(self.abc(),4,1860)
        labels=[s['text'] for s in construction_shapes(app,geometry(app),font=8,selected=app.selected_panel_coords)
                if s['kind']=='text']
        self.assertIn('C = 1860.0 mm',labels)
        self.assertEqual(app.mounting_plan['dimensions'],[])

    def test_vector_installer_report_uses_top_distances(self):
        import fitz
        app=fixture()
        app.mounting_plan['panels']['one']=self.abc()
        app.mounting_plan['panels']['two']=self.abc()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'pose_abc.pdf'
            info=write_installer_pdf(app,path)
            self.assertEqual(info['fixing_points'],12)
            with fitz.open(str(path)) as doc:
                text=' '.join(page.get_text() for page in doc)
                self.assertIn('A=480',text)
                self.assertIn('B=1150',text)
                self.assertIn('C=1920',text)
                self.assertIn('TOP EDGE',text)
                self.assertIn('F6',text)


if __name__=='__main__':unittest.main()
