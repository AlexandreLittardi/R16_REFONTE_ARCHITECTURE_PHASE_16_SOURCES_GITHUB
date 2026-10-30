"""Module-edge gap and physical fixing inventory regression tests."""
import copy
import csv
import math
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from mounting import validate_plan, default_config
from mounting_edges import default_rules,validate_rules
from mounting_drawing import geometry
from mounting_joint_gap import suggested_layout_gaps, check_layout_capacity
from mounting_quantities import fixing_inventory,write_inventory_csv
from test_mounting_edges import grid


class GapAndBillTests(unittest.TestCase):
    def test_new_rule_backwards_compatible_and_persistent(self):
        app=grid()
        app.mounting_plan['edge_rules'].pop('joint_gap_mm')
        assert validate_plan(app.mounting_plan)['edge_rules']['joint_gap_mm']==0
        app.mounting_plan['edge_rules']['joint_gap_mm']=25.5
        assert validate_plan(app.mounting_plan)['edge_rules']['joint_gap_mm']==25.5
        for invalid in (-1,float('nan'),float('inf'),1001):
            bad=copy.deepcopy(app.mounting_plan['edge_rules']);bad['joint_gap_mm']=invalid
            with self.assertRaises(ValueError):validate_rules(bad)

    def test_grid_has_sixteen_or_more_contacts_but_shared_clamps_are_unique(self):
        app=grid(3,3)
        i=fixing_inventory(geometry(app),app.px_per_mm,50)
        self.assertEqual(i['points_by_kind'],{'edge':12,'intermediate':24})
        self.assertEqual(i['pieces_by_kind'],{'edge':12,'intermediate':12})
        self.assertEqual(i['pieces_total'],24)
        self.assertEqual(i['unpaired_intermediate'],0)
        self.assertEqual(len(i['shared_pairs']),12)

    def test_mismatch_reference_and_station_not_merged(self):
        app=grid(1,2)
        app.mounting_plan['edge_rules']['overrides']={'0-1':{'0':'edge'}}
        i=fixing_inventory(geometry(app),app.px_per_mm,50)
        self.assertEqual(i['shared_pairs'].__len__(),1)
        self.assertEqual(i['unpaired_intermediate'],1)
        app=grid(1,2)
        app.mounting_plan['panels']['0-1']['positions']={'0':700}
        i=fixing_inventory(geometry(app),app.px_per_mm,50)
        self.assertEqual(len(i['shared_pairs']),1)
        self.assertEqual(i['unpaired_intermediate'],2)

    def test_rotation_six_fixings_and_landscape(self):
        app=grid(1,2,angle=30)
        for c in app.mounting_plan['panels'].values():
            c['count']=6;c['top_offsets_mm']=[200,950,1750]
        i=fixing_inventory(geometry(app),app.px_per_mm,50)
        self.assertEqual(i['pieces_by_kind'],{'edge':6,'intermediate':3})
        app=grid(2,1,width=2000,height=1000)
        for c in app.mounting_plan['panels'].values():c['edge']='long'
        i=fixing_inventory(geometry(app),app.px_per_mm,50)
        self.assertEqual(i['pieces_by_kind']['intermediate'],2)

    def test_layout_axis_and_existing_gap_preservation(self):
        app=grid(1,2)
        app.model_settings={'module_gap_width_mm':7,'module_gap_length_mm':12}
        r=app.mounting_plan['edge_rules'];r['joint_gap_mm']=22
        self.assertEqual(suggested_layout_gaps(app,r),(22,12,True))
        for c in app.mounting_plan['panels'].values():c['edge']='short'
        self.assertEqual(suggested_layout_gaps(app,r),(7,22,True))
        r['enabled']=False
        self.assertEqual(suggested_layout_gaps(app,r),(7,12,False))

    def test_capacity_blocks_lost_panels(self):
        app=SimpleNamespace(panel_width_mm=1000,panel_height_mm=2000,px_per_mm=.1,
                            roof_zones=[dict(x1=0,y1=0,x2=300,y2=210,rows=1,cols=3,row_base=0,row_capacity=100)],
                            panels={(0,0):1,(0,1):2,(0,2):3})
        self.assertEqual(check_layout_capacity(app,0,0),[])
        self.assertEqual(check_layout_capacity(app,60,0),[(0,2)])

    def test_inventory_csv_records_parts_distinct_from_contacts(self):
        app=grid(1,2)
        with tempfile.TemporaryDirectory() as folder:
            result=write_inventory_csv(app,Path(folder)/'parts.csv')
            with open(Path(folder)/'parts.csv',encoding='utf-8-sig') as f:
                rows=list(csv.reader(f,delimiter=';'))
            self.assertEqual(rows[-2][-2:],['8','6'])
            self.assertEqual(result['pieces_total'],6)

if __name__=='__main__':unittest.main()
