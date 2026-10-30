import copy
import csv
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

from mounting import (empty_plan, default_config, validate_config, validate_plan,
                      axes, fixings, transform, inverse, dimension_geometry, resize_fixings)
from mounting_drawing import geometry, scene, resolve_point, write_svg, write_schedule
from project_store import validate_project, write_project


def example():
    c=default_config(1303,2384);c.update(a_mm=490,b_mm=490)
    return validate_config(c)


def fixture():
    app=SimpleNamespace(panels={(0,0):1,(0,1):2},panel_uids={(0,0):'one',(0,1):'two'},
        panel_width_mm=1303,panel_height_mm=2384,px_per_mm=.1,roof_pil_img=None,
        roof_polygons=[],roof_zones=[{}],mounting_plan=empty_plan(),project_name='Montage & <essai>')
    app._panel_rect=lambda coord:[(coord[1]*150,0),(coord[1]*150+130.3,0),(coord[1]*150+130.3,238.4),(coord[1]*150,238.4)]
    app.mounting_plan['panels']={'one':example(),'two':example()}
    return app


class MountingTests(unittest.TestCase):
    def test_four_fixings_and_asymmetric_retracts(self):
        c=example();c['b_mm']=510
        self.assertEqual([f['position_mm'] for f in fixings(c)],[490,490,1874,1874])

    def test_station_count(self):
        for count in (4,6,8,10,12):
            c=example();c['count']=count;c=validate_config(c)
            fs=fixings(c);self.assertEqual(len(fs),count)
            self.assertAlmostEqual(fs[-1]['position_mm'],1894)

    def test_landscape_and_short_edges(self):
        for w,h in ((1303,2384),(2384,1303)):
            for edge in ('long','short'):
                c=default_config(w,h);c['edge']=edge;c=validate_config(c)
                length,cross,along_y=axes(c)
                self.assertEqual(length,max(w,h) if edge=='long' else min(w,h))
                self.assertEqual(fixings(c)[1]['y' if along_y else 'x'],c['a_mm'])

    def test_invalid_geometry(self):
        for change in ({'a_mm':-1},{'b_mm':10},{'a_mm':2000},{'count':5},{'count':4.0},
                       {'a_mm':float('nan')},{'width_mm':0},{'clamp_width_mm':2000}):
            with self.subTest(change=change),self.assertRaises(ValueError):validate_config(dict(example(),**change))

    def test_manual_overrides_validated(self):
        c=example();c['positions']={'0':600};c=validate_config(c)
        self.assertEqual(fixings(c)[0]['position_mm'],600)
        for p in ({'0':5},{'8':500},{'0':1890},{'0':float('inf')}):
            c=example();c['positions']=p
            with self.assertRaises(ValueError):validate_config(c)

    def test_transform_rotation_and_inverse(self):
        angle=math.radians(37);w,h=1303,2384;scale=.12
        def r(x,y):return (220+scale*(x*math.cos(angle)-y*math.sin(angle)),300+scale*(x*math.sin(angle)+y*math.cos(angle)))
        poly=[r(0,0),r(w,0),r(w,h),r(0,h)]
        for point in ((0,0),(1303,2384),(0,490),(1303,1894)):
            mapped=transform(poly,w,h,point)
            self.assertAlmostEqual(mapped[0],r(*point)[0])
            self.assertAlmostEqual(mapped[1],r(*point)[1])
            local=inverse(poly,w,h,mapped)
            for a,b in zip(point,local):self.assertAlmostEqual(a,b)

    def test_dimensions_axes(self):
        for axis,expected in (('aligned',5),('horizontal',3),('vertical',4)):
            a,b,length=dimension_geometry((10,20),(13,24),(40,80),axis)
            self.assertAlmostEqual(length,expected)
            self.assertAlmostEqual(math.dist(a,b),expected)

    def test_missing_and_invalid_state(self):
        self.assertEqual(validate_project({})['mounting_plan'],empty_plan())
        for state in ({},[],{'version':2},dict(empty_plan(),dimensions=[{'axis':'aligned'}])):
            with self.assertRaises(ValueError):validate_plan(state)

    def test_round_trip_local_project(self):
        app=fixture();data={'panel_width_mm':1303,'panel_height_mm':2384,'panels':{'0,0':1,'0,1':2},
            'panel_uids':{'0,0':'one','0,1':'two'},'mounting_plan':app.mounting_plan}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'project.json';written=write_project(path,data)
            import json
            reloaded=validate_project(json.loads(path.read_text()))
            self.assertEqual(reloaded['mounting_plan'],written['mounting_plan'])

    def test_associative_fixing_dimension(self):
        app=fixture();ref=dict(uid='one',kind='fixing',index=0)
        d=dict(p1=(0,0),ref1=ref)
        self.assertEqual(resolve_point(d,1,geometry(app)),(0.,49.))
        app.mounting_plan['panels']['one']['positions']['0']=600
        self.assertAlmostEqual(resolve_point(d,1,geometry(app))[1],60.)
        app.panels.pop((0,0))
        self.assertIsNone(resolve_point(d,1,geometry(app)))

    def test_stale_module_dimensions(self):
        app=fixture();app.panel_height_mm=2300
        self.assertTrue(all(i['issue'] and not i['fixings'] for i in geometry(app).values()))

    def test_svg_export_all_modules_and_dimension_units(self):
        app=fixture();app.mounting_plan['dimensions'].append(dict(p1=(0,0),p2=(130.3,0),label=(65.15,-20),axis='aligned'))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'plan.svg';write_svg(app,path)
            tree=ET.parse(path);root=tree.getroot()
            self.assertTrue(root.attrib['width'].endswith('mm'))
            text=' '.join(tree.getroot().itertext())
            labels=[p for p in root.iter() if p.get('data-role')=='panel-number']
            self.assertEqual([p.text for p in labels],['1','2'])
            self.assertTrue(all(p.get('font-weight')=='bold' for p in labels))
            self.assertIn('1303.0 mm',text)
            self.assertIn('Montage & <essai>',text)

    def test_csv_schedule_coordinates_and_quantity(self):
        app=fixture()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixings.csv';write_schedule(app,path)
            with path.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f,delimiter=';'))
            self.assertEqual(len(rows),9)
            self.assertEqual(float(rows[1][4]),0)
            self.assertEqual(float(rows[1][5]),490)
            self.assertAlmostEqual(float(rows[-1][4]),2803)

    def test_source_config_unmodified(self):
        c=example();old=copy.deepcopy(c);validate_config(c);fixings(c)
        self.assertEqual(c,old)

    def test_resize_keeps_positions_and_other_panels(self):
        app=fixture();app.mounting_plan['panels']['one']['positions']['0']=600
        old=copy.deepcopy(app.mounting_plan)
        updated=resize_fixings(old,['one'],350,180)
        self.assertEqual(updated['panels']['one']['positions'],{'0':600.})
        for key in ('a_mm','b_mm','count','edge'):
            self.assertEqual(updated['panels']['one'][key],old['panels']['one'][key])
        self.assertEqual(updated['panels']['two'],old['panels']['two'])
        self.assertEqual(app.mounting_plan,old)
        self.assertEqual(updated['panels']['one']['clamp_length_mm'],350)
        self.assertEqual(updated['panels']['one']['clamp_width_mm'],180)

    def test_resize_is_atomic_on_invalid_target(self):
        app=fixture();app.mounting_plan['panels']['two']['a_mm']=100
        old=copy.deepcopy(app.mounting_plan)
        with self.assertRaises(ValueError):resize_fixings(app.mounting_plan,['one','two'],350,180)
        self.assertEqual(app.mounting_plan,old)

    def test_footprint_dimensions_at_scale_after_rotation(self):
        app=fixture();app.mounting_plan=resize_fixings(app.mounting_plan,['one','two'],350,180)
        original=app._panel_rect
        angle=math.radians(29)
        def rotated(coord):return [(x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)) for x,y in original(coord)]
        app._panel_rect=rotated
        for item in geometry(app).values():
            f=item['fixings'][0];poly=f['world_polygon']
            self.assertAlmostEqual(math.dist(poly[0],poly[1])/app.px_per_mm,180)
            self.assertAlmostEqual(math.dist(poly[1],poly[2])/app.px_per_mm,350)
            centers=tuple(sum(p[i] for p in poly)/4 for i in (0,1))
            for a,b in zip(centers,f['point']):self.assertAlmostEqual(a,b)

    def test_corner_dimensions_follow_footprint_resize(self):
        app=fixture()
        d=dict(p1=(0,0),p2=(0,0),label=(0,0),axis='aligned',
            ref1=dict(uid='one',kind='fixing_corner',index=0),ref2=dict(uid='one',kind='fixing_corner',index=1))
        app.mounting_plan['dimensions']=[d]
        app.mounting_plan=resize_fixings(app.mounting_plan,['one'],350,180)
        validate_plan(app.mounting_plan)
        items=geometry(app)
        self.assertAlmostEqual(math.dist(resolve_point(d,1,items),resolve_point(d,2,items))/app.px_per_mm,180)
        app.mounting_plan=resize_fixings(app.mounting_plan,['one'],400,200)
        items=geometry(app)
        self.assertAlmostEqual(math.dist(resolve_point(d,1,items),resolve_point(d,2,items))/app.px_per_mm,200)

    def test_resized_footprint_in_svg_and_csv(self):
        app=fixture();app.mounting_plan=resize_fixings(app.mounting_plan,['one','two'],350,180)
        with tempfile.TemporaryDirectory() as d:
            svg=Path(d)/'plan.svg';write_svg(app,svg)
            root=ET.parse(svg).getroot()
            polygons=[p for p in root if p.tag.endswith('polygon') and p.get('fill')=='#888888']
            self.assertEqual(len(polygons),8)
            points=[tuple(map(float,p.split(','))) for p in polygons[0].get('points').split()]
            self.assertAlmostEqual(math.dist(points[0],points[1])/app.px_per_mm,180)
            self.assertAlmostEqual(math.dist(points[1],points[2])/app.px_per_mm,350)
            schedule=Path(d)/'fixings.csv';write_schedule(app,schedule)
            with schedule.open(encoding='utf-8-sig') as f:rows=list(csv.reader(f,delimiter=';'))
            self.assertTrue(all(float(r[6])==350 and float(r[7])==180 for r in rows[1:]))


if __name__=='__main__':unittest.main()
