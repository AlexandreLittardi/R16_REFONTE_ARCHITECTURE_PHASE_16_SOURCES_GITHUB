"""Single physical clamp per valid pair, on canvas, in PDF, in SVG and exports."""
import copy
import csv
import math
import tempfile
from pathlib import Path
import unittest

from mounting import validate_plan
from mounting_drawing import geometry, scene, write_svg
from mounting_quantities import fixing_inventory, move_linked_stations, write_physical_schedule_csv
from report_mounting import overview
from mounting_installer import write_installer_pdf
from test_mounting_edges import grid


class SharedPhysicalClampTests(unittest.TestCase):
    def inventory(self,app):
        return fixing_inventory(geometry(app),app.px_per_mm,
            app.mounting_plan['edge_rules']['max_gap_mm'])

    def test_one_middle_clamp_per_two_frames_even_with_gap(self):
        for gap in (0,12,25,40):
            with self.subTest(gap=gap):
                app=grid(1,2,gap=gap)
                items=geometry(app);inv=self.inventory(app)
                self.assertEqual(inv['points_total'],8)
                self.assertEqual(inv['pieces_total'],6)
                self.assertEqual(len(inv['shared_pairs']),2)
                self.assertEqual(len(inv['physical_fixings']),6)
                scene_items=scene(app,items,construction=False,inventory=inv)
                footprints=[s for s in scene_items if s.get('role')=='physical_clamp']
                self.assertEqual(len(footprints),6)
                self.assertEqual(sum(s.get('shared',False) for s in footprints),2)
                for f in inv['physical_fixings']:
                    if not f['shared']:continue
                    self.assertEqual(len(f['contacts']),2)
                    self.assertAlmostEqual(f['point'][0],.1*(1000+gap/2),places=6)
                    self.assertAlmostEqual(sum(p[0] for p in f['world_polygon'])/4,f['point'][0],places=6)

    def test_six_fixings_a_b_c_and_rotated_panels(self):
        for angle in (0,33,72):
            with self.subTest(angle=angle):
                app=grid(1,2,gap=25,angle=angle)
                for c in app.mounting_plan['panels'].values():
                    c['count']=6;c['top_offsets_mm']=[250,900,1750]
                inv=self.inventory(app)
                self.assertEqual(inv['points_total'],12)
                self.assertEqual(inv['pieces_total'],9)
                self.assertEqual(sum(p['shared'] for p in inv['physical_fixings']),3)
                for pair in inv['shared_pairs']:
                    a,b=pair['a'],pair['b']
                    self.assertNotEqual(a[0],b[0])

    def test_mismatch_stays_separate_not_artificially_merged(self):
        app=grid(1,2,gap=20)
        app.mounting_plan['panels']['0-1']['positions']['0']=700
        inv=self.inventory(app)
        self.assertEqual(inv['pieces_total'],7)
        self.assertEqual(sum(p['shared'] for p in inv['physical_fixings']),1)
        app=grid(1,2,gap=50)
        # A 40 mm wide clamp cannot physically bridge a 50 mm joint.
        app.mounting_plan['edge_rules']['profiles']['intermediate']['width_mm']=40
        inv=self.inventory(app)
        self.assertEqual(inv['pieces_total'],8)
        self.assertEqual(inv['unpaired_intermediate'],4)

    def test_svg_and_pdf_same_count_as_inventory(self):
        app=grid(1,2,gap=25);inv=self.inventory(app)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'mount.svg'
            write_svg(app,path)
            svg=path.read_text(encoding='utf-8')
            self.assertEqual(svg.count('data-role="physical-clamp"'),inv['pieces_total'])
            self.assertEqual(svg.count('data-contacts="0-0:F2;0-1:F1"'),1)
            drawing,_=overview(app,geometry(app),'Helvetica',inventory=inv)
            # A filled gray polygon per physical clamp (panel faces are white).
            import reportlab.graphics.shapes as shapes
            clamps=[s for s in drawing.contents if isinstance(s,shapes.Polygon) and s.fillColor and
                    s.fillColor.red <.8 and s.fillColor.green <.8 and s.fillColor.blue <.8]
            self.assertEqual(len(clamps),inv['pieces_total'])
            pdf_path=Path(d)/'installation.pdf'
            write_installer_pdf(app,pdf_path)
            import fitz
            pdf=fitz.open(pdf_path)
            entire='\n'.join(page.get_text() for page in pdf)
            self.assertIn('PHYSICAL CLAMP COORDINATES',entire)
            self.assertIn('P1/F2 + P2/F1',entire)
            self.assertIn('6 estimated physical clamps',entire)
            pdf.close()

    def test_unique_csv_contains_exactly_one_row_per_part(self):
        app=grid(1,2,gap=25)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'physical.csv';inv=write_physical_schedule_csv(app,path)
            with path.open(encoding='utf-8-sig') as file: rows=list(csv.reader(file,delimiter=';'))
            self.assertEqual(len(rows)-1,inv['pieces_total'])
            self.assertEqual(sum(row[8]=='Yes' for row in rows[1:]),2)
            self.assertTrue(all('P' in row[7] for row in rows[1:]))
            self.assertAlmostEqual(float(next(row[5] for row in rows[1:] if row[8]=='Yes')),1012.5)

    def test_linked_move_propagates_through_six_attachment_array(self):
        app=grid(1,3,gap=25)
        for c in app.mounting_plan['panels'].values():
            c['count']=6;c['top_offsets_mm']=[250,900,1750]
        items=geometry(app);inv=self.inventory(app)
        before=copy.deepcopy(app.mounting_plan)
        updated=move_linked_stations(items,app.mounting_plan,inv,'0-0',3,950.)
        self.assertEqual(before['panels']['0-0']['top_offsets_mm'],[250,900,1750])
        self.assertEqual([c['top_offsets_mm'] for c in updated['panels'].values()],[[250,950,1750]]*3)
        new_items=geometry(app,updated)
        anew=fixing_inventory(new_items,app.px_per_mm,50)
        self.assertEqual(anew['pieces_total'],12)
        self.assertEqual(len(anew['shared_pairs']),6)
        self.assertEqual(validate_plan(updated)['panels']['0-1']['top_offsets_mm'][1],950.)

    def test_select_shared_clamp_and_edit_keeps_both_panels_aligned(self):
        from mixins.mounting_ui import MountingMixin
        app=grid(1,2,gap=25)
        app._mounting_items=geometry(app)
        app._mounting_inventory=self.inventory(app)
        app.selected_panel_coords={(0,1)}
        piece=next(f for f in app._mounting_inventory['physical_fixings'] if f['shared'])
        # Select the clamp at its actual joint center, not at one frame edge.
        uid,index=MountingMixin._mounting_hit_fixing(app,piece['point'])
        self.assertEqual(uid,'0-1')
        MountingMixin._mounting_move_station(app,uid,index,600)
        self.assertEqual(app.mounting_plan['panels']['0-0']['positions']['1'],600)
        self.assertEqual(app.mounting_plan['panels']['0-1']['positions']['0'],600)
        anew=fixing_inventory(geometry(app),app.px_per_mm,50)
        self.assertEqual(anew['pieces_total'],6)
        self.assertEqual(len(anew['shared_pairs']),2)

    def test_invalid_linked_move_does_not_modify_source(self):
        app=grid(1,2,gap=25)
        before=copy.deepcopy(app.mounting_plan)
        with self.assertRaises(ValueError):
            move_linked_stations(geometry(app),app.mounting_plan,self.inventory(app),'0-0',1,1990.)
        self.assertEqual(app.mounting_plan,before)


if __name__=='__main__':unittest.main()
