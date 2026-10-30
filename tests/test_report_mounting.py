import copy
import json
from pathlib import Path
import tempfile
import unittest

import fitz
from mounting import empty_plan, validate_plan
from mounting_drawing import geometry
from project_store import serial, write_project, validate_project
from report_mounting import mounting_pages, motifs, PT_MM
from test_mounting_edges import grid


class MountingReportTests(unittest.TestCase):
    def test_motifs_use_effective_positions_types_and_sizes(self):
        app=grid();items=geometry(app);groups,assignment=motifs(items)
        self.assertEqual(len(assignment),9)
        # Left, middle and right sides have different effective profiles.
        self.assertEqual(len(groups),3)
        app.mounting_plan['panels']['1-1']['positions']['0']=500
        app.mounting_plan['edge_rules']['overrides']={'0-1':{'0':'edge'}}
        changed,mapping=motifs(geometry(app))
        self.assertEqual(len(changed),5)
        self.assertNotEqual(mapping['1-1'],mapping['2-1'])

    def test_pdf_is_vector_and_carries_live_associative_dimensions(self):
        app=grid(angle=23);app.project_name='Essai pose'
        app.mounting_plan['panels']['0-0']['positions']['0']=500
        app.mounting_plan['dimensions']=[dict(p1=[0,0],p2=[1,1],label=[-40,40],axis='aligned',
            ref1=dict(uid='0-0',kind='corner',index=0),ref2=dict(uid='0-0',kind='fixing',index=0))]
        original=copy.deepcopy(app.mounting_plan)
        with tempfile.TemporaryDirectory() as folder:
            pages=mounting_pages(app,folder)
            doc=fitz.open(Path(folder)/'mounting_general.pdf')
            self.assertIn('500.0 mm',doc[0].get_text())
            self.assertIn('GENERAL PLAN',doc[0].get_text())
            self.assertEqual(doc[0].get_images(),[])
            self.assertGreater(len(doc[0].get_drawings()),50)
            self.assertTrue(any('placement' in p['title'] for p in pages))
            self.assertTrue((Path(folder)/'mounting_M01.svg').exists())
        self.assertEqual(app.mounting_plan,original)

    def test_detail_uses_actual_axes_and_physical_footprints(self):
        app=grid(1,1)
        with tempfile.TemporaryDirectory() as folder:
            mounting_pages(app,folder)
            doc=fitz.open(Path(folder)/'mounting_M01.pdf');page=doc[0]
            text=page.get_text()
            self.assertIn('400.0',text);self.assertIn('160',text)
            # Read the stated scale and verify the real profile size in points.
            import re
            denom=float(re.search(r'1:([\d.]+)',text).group(1))
            expected=sorted((80*PT_MM/denom,160*PT_MM/denom))
            found=False
            for path in page.get_drawings():
                if path['fill'] and max(path['fill'])-min(path['fill'])<.002 and path['fill'][0]<.9:
                    actual=sorted((path['rect'].width,path['rect'].height))
                    found |= all(abs(a-b)<.02 for a,b in zip(actual,expected))
            self.assertTrue(found,'Fixing rectangles must have the stated physical size')

    def test_all_orientations_short_edges_and_twelve_fixings(self):
        for width,height in ((1000,2000),(2000,1000)):
            for edge in ('long','short'):
                app=grid(1,1,width=width,height=height)
                c=app.mounting_plan['panels']['0-0'];c.update(edge=edge,count=12,a_mm=100,b_mm=100)
                # Short edges need smaller footprints to fit six stations.
                for p in app.mounting_plan['edge_rules']['profiles'].values():p.update(length_mm=50,width_mm=40)
                with tempfile.TemporaryDirectory() as folder:
                    mounting_pages(app,folder)
                    doc=fitz.open(Path(folder)/'mounting_M01.pdf')
                    self.assertIn('F12',doc[0].get_text())
                    # All text, including rotated dimensions, stays on the sheet.
                    for b in doc[0].get_text('blocks'):
                        self.assertGreaterEqual(b[0],-1);self.assertGreaterEqual(b[1],-1)
                        self.assertLessEqual(b[2],743);self.assertLessEqual(b[3],351)

    def test_missing_geometry_is_explicit(self):
        app=grid();app.mounting_plan['panels'].pop('1-1')
        app.mounting_plan['dimensions']=[dict(p1=[0,0],p2=[0,1],label=[0,0],axis='aligned',
            ref1=dict(uid='deleted',kind='corner',index=0))]
        with tempfile.TemporaryDirectory() as folder:
            pages=mounting_pages(app,folder)
            issues=[p for p in pages if 'missing data' in p['title']]
            self.assertTrue(issues)
            self.assertIn('mounting not specified',str(issues))
            self.assertIn('missing dimension references',str(issues))
        app.px_per_mm=0
        self.assertIn('Calibrate',str(mounting_pages(app,'.')))
        app.mounting_plan=empty_plan();self.assertEqual(mounting_pages(app,'.'),[])

    def test_large_project_has_complete_paginated_schedule_and_atlas(self):
        app=grid(20,25,angle=17)
        with tempfile.TemporaryDirectory() as folder:
            pages=mounting_pages(app,folder)
            schedules=[p for p in pages if 'placement' in p['title']]
            ids=[r[0] for p in schedules for r in p['items'][0][2]]
            self.assertEqual(len(ids),500);self.assertEqual(len(set(ids)),500)
            self.assertTrue(list(Path(folder).glob('mounting_tile_*.pdf')))
            self.assertTrue(all(len(p['items'][0][2])<=18 for p in schedules))

    def test_complete_saved_plan_roundtrip(self):
        app=grid();plan=app.mounting_plan
        plan['template']=copy.deepcopy(plan['panels']['1-1'])
        plan['panels']['1-1']['positions']['0']=515.5
        plan['edge_rules']['overrides']={'1-1':{'0':'edge'}}
        plan['edge_rules']['max_gap_mm']=37.5
        plan['dimensions']=[dict(p1=[0,0],p2=[20,30],label=[22,-13],axis=axis,
            ref1=dict(uid='1-1',kind='corner',index=0),ref2=dict(uid='1-1',kind='fixing_corner',index=0),auto=True)
            for axis in ('horizontal','vertical','aligned')]
        data=dict(panel_width_mm=1000,panel_height_mm=2000,panels={f'{r},{c}':n for (r,c),n in app.panels.items()},
                  panel_uids={f'{r},{c}':u for (r,c),u in app.panel_uids.items()},mounting_plan=plan)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'project.json';write_project(path,data)
            loaded=validate_project(json.loads(path.read_text()))
            self.assertEqual(serial(loaded['mounting_plan']),serial(validate_plan(plan)))
            write_project(path,loaded,recovery=True)
            self.assertEqual(json.loads(path.read_text())['mounting_plan'],serial(validate_plan(plan)))


if __name__=='__main__':unittest.main()
