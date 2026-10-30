import copy
import csv
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from mounting import empty_plan,default_config,validate_plan
from mounting_drawing import geometry,write_schedule,write_svg,resolve_point
from mounting_edges import default_rules,validate_rules


def grid(rows=3,cols=3,gap=20,angle=0,width=1000,height=2000):
    app=SimpleNamespace(panels={},panel_uids={},panel_width_mm=width,panel_height_mm=height,
        px_per_mm=.1,roof_zones=[{}],roof_polygons=[],roof_pil_img=None,project_name='Bordures',mounting_plan=empty_plan())
    polygons={};a=math.radians(angle)
    def rotate(x,y):return (.1*(x*math.cos(a)-y*math.sin(a)),.1*(x*math.sin(a)+y*math.cos(a)))
    for r in range(rows):
        for c in range(cols):
            coord=(r,c);uid=f'{r}-{c}';x,y=c*(width+gap),r*(height+gap)
            app.panels[coord]=r*cols+c+1;app.panel_uids[coord]=uid
            polygons[coord]=[rotate(x,y),rotate(x+width,y),rotate(x+width,y+height),rotate(x,y+height)]
            app.mounting_plan['panels'][uid]=default_config(width,height)
    app._panel_rect=lambda coord:polygons[coord]
    rules=app.mounting_plan['edge_rules'];rules['enabled']=True
    rules['profiles']['intermediate'].update(reference='MID-100',length_mm=100,width_mm=60)
    rules['profiles']['edge'].update(reference='END-160',length_mm=160,width_mm=80)
    return app


class MountingEdgesTests(unittest.TestCase):
    def test_outer_and_inner_edges_on_same_panel(self):
        items=geometry(grid())
        self.assertEqual([f['kind'] for f in items['1-0']['fixings']],['edge','intermediate','edge','intermediate'])
        self.assertEqual([f['kind'] for f in items['1-1']['fixings']],['intermediate']*4)
        fs=[f for item in items.values() for f in item['fixings']]
        self.assertEqual(sum(f['kind']=='edge' for f in fs),12)
        self.assertEqual(sum(f['kind']=='intermediate' for f in fs),24)

    def test_boundary_panels_and_terminal_clamps_are_distinct(self):
        items=geometry(grid())
        self.assertEqual(sum(item['is_boundary'] for item in items.values()),8)
        self.assertTrue(items['0-1']['is_boundary'])
        self.assertTrue(all(f['kind']=='intermediate' for f in items['0-1']['fixings']))
        self.assertFalse(items['1-1']['is_boundary'])

    def test_hole_is_an_exposed_edge(self):
        app=grid();app.panels.pop((1,1));items=geometry(app)
        self.assertTrue(all(f['kind']=='edge' for f in items['1-0']['fixings']))
        self.assertTrue(all(f['kind']=='edge' for f in items['1-2']['fixings']))

    def test_rotation_and_landscape(self):
        for angle,width,height in ((31,1000,2000),(0,2000,1000),(73,2000,1000)):
            with self.subTest(angle=angle,width=width):
                items=geometry(grid(angle=angle,width=width,height=height))
                self.assertFalse(any(item['issue'] for item in items.values()))
                self.assertEqual(sum(f['kind']=='edge' for item in items.values() for f in item['fixings']),12)

    def test_short_side_mounting(self):
        app=grid()
        for c in app.mounting_plan['panels'].values():c['edge']='short'
        items=geometry(app)
        self.assertEqual(sum(f['kind']=='edge' for item in items.values() for f in item['fixings']),12)
        self.assertTrue(all(f['kind']=='intermediate' for f in items['1-0']['fixings']))

    def test_maximum_gap_and_isolated_panel(self):
        app=grid(gap=100)
        self.assertTrue(all(f['kind']=='edge' for item in geometry(app).values() for f in item['fixings']))
        self.assertTrue(all(f['kind']=='edge' for f in geometry(grid(1,1))['0-0']['fixings']))

    def test_partial_neighbor_is_checked_at_each_fixing(self):
        app=grid(1,2)
        original=app._panel_rect
        app._panel_rect=lambda coord:[(x,y+100) for x,y in original(coord)] if coord==(0,1) else original(coord)
        fs=geometry(app)['0-0']['fixings']
        self.assertEqual(fs[1]['kind'],'edge')
        self.assertEqual(fs[3]['kind'],'intermediate')

    def test_manual_override_and_geometry_are_saved(self):
        app=grid();rules=app.mounting_plan['edge_rules']
        rules['overrides']={'1-1':{'0':'edge'}}
        item=geometry(app)['1-1'];f=item['fixings'][0]
        self.assertEqual(f['kind'],'edge');self.assertTrue(f['forced'])
        self.assertEqual(f['automatic_kind'],'intermediate')
        self.assertEqual(f['reference'],'END-160')
        self.assertAlmostEqual(math.dist(f['world_polygon'][1],f['world_polygon'][2])/.1,160)
        self.assertEqual(validate_plan(app.mounting_plan)['edge_rules'],rules)

    def test_missing_neighbors_recalculate_and_ignore_unmounted_status(self):
        app=grid();app.mounting_plan['panels'].pop('1-0')
        self.assertEqual(geometry(app)['1-1']['fixings'][0]['kind'],'intermediate')
        app.panels.pop((1,0))
        self.assertEqual(geometry(app)['1-1']['fixings'][0]['kind'],'edge')

    def test_legacy_plan_remains_uniform(self):
        app=grid();app.mounting_plan.pop('edge_rules')
        app.mounting_plan=validate_plan(app.mounting_plan)
        self.assertFalse(app.mounting_plan['edge_rules']['enabled'])
        self.assertTrue(all(f['kind']=='standard' and f['length_mm']==50 for item in geometry(app).values() for f in item['fixings']))

    def test_invalid_profile_and_mixed_footprints(self):
        for change in ({'length_mm':-1},{'width_mm':float('nan')},{'reference':''}):
            r=default_rules();r['profiles']['edge'].update(change)
            with self.assertRaises(ValueError):validate_rules(r)
        app=grid();app.mounting_plan['edge_rules']['profiles']['edge']['length_mm']=900
        self.assertTrue(geometry(app)['1-0']['issue'])
        self.assertFalse(geometry(app)['1-1']['issue'])

    def test_svg_and_csv_export_effective_types_and_sizes(self):
        app=grid()
        with tempfile.TemporaryDirectory() as d:
            csvpath=Path(d)/'fixings.csv';write_schedule(app,csvpath)
            with csvpath.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f,delimiter=';'))
            end=[r for r in rows[1:] if r[9]=='End'];mid=[r for r in rows[1:] if r[9]=='Intermediate']
            self.assertEqual(len(end),12);self.assertEqual(len(mid),24)
            self.assertTrue(all(float(r[6])==160 and float(r[7])==80 and r[10]=='END-160' for r in end))
            svg=Path(d)/'plan.svg';write_svg(app,svg)
            text=svg.read_text();self.assertIn('END-160',text);self.assertIn('MID-100',text);self.assertIn('fill="#202020"',text)

    def test_corner_dimensions_follow_automatic_type_changes(self):
        app=grid();d=dict(ref1=dict(uid='1-1',kind='fixing_corner',index=0),ref2=dict(uid='1-1',kind='fixing_corner',index=1),p1=(0,0),p2=(0,0))
        items=geometry(app)
        self.assertAlmostEqual(math.dist(resolve_point(d,1,items),resolve_point(d,2,items))/.1,60)
        app.panels.pop((1,0));items=geometry(app)
        self.assertAlmostEqual(math.dist(resolve_point(d,1,items),resolve_point(d,2,items))/.1,80)


if __name__=='__main__':unittest.main()
