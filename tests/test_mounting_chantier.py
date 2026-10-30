"""Regression tests for installer datum, live dimensions and vector handoff."""
import csv
import tempfile
from pathlib import Path
import unittest
from mounting import default_site,validate_site,validate_plan
from mounting_drawing import geometry,construction_shapes,site_origin,write_schedule
from mounting_installer import write_installer_pdf
from test_mounting import fixture


class InstallerTests(unittest.TestCase):
    def test_datum_roundtrip_and_legacy_migration(self):
        app=fixture()
        self.assertEqual(validate_plan(app.mounting_plan)['site'],default_site())
        app.mounting_plan['site'].update(origin=[50.,100.],roof_reference='IPE 160',
                                         support_reference='Pannes',revision='B')
        self.assertEqual(validate_plan(app.mounting_plan)['site']['origin'],[50.,100.])
        self.assertEqual(site_origin(app)[0],(50,100))
        for bad in (['x',2],[float('inf'),3],[1],{0:10}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_site({'origin':bad})

    def test_cotes_are_live_and_not_synthetically_stored(self):
        app=fixture();items=geometry(app)
        app.selected_panel_coords={(0,0)}
        before=construction_shapes(app,items,font=8,selected=app.selected_panel_coords)
        labels=lambda seq:[s['text'] for s in seq if s['kind']=='text']
        self.assertIn('X champ = 2803.0 mm',labels(before))
        self.assertIn('Y champ = 2384.0 mm',labels(before))
        self.assertIn('490.0 mm',labels(before))
        original=len(app.mounting_plan['dimensions'])
        app.mounting_plan['panels']['one']['positions']['0']=600
        after=construction_shapes(app,geometry(app),font=8,selected=app.selected_panel_coords)
        self.assertIn('600.0 mm',labels(after))
        self.assertEqual(original,len(app.mounting_plan['dimensions']))

    def test_csv_datum_and_missing_origin_warning(self):
        app=fixture()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'pose.csv';write_schedule(app,path)
            with path.open(encoding='utf-8-sig') as stream:rows=list(csv.reader(stream,delimiter=';'))
            self.assertEqual(rows[1][-1],'NO - TEMPORARY')
            app.mounting_plan['site']['origin']=[20.,40.]
            write_schedule(app,path)
            with path.open(encoding='utf-8-sig') as stream:rows=list(csv.reader(stream,delimiter=';'))
            self.assertAlmostEqual(float(rows[1][13]),-200.)
            self.assertAlmostEqual(float(rows[1][14]),90.)
            self.assertEqual(rows[1][-1],'Yes')

    def test_pdf_complete_a3_and_many_fixings(self):
        import fitz
        app=fixture();app.mounting_plan['site']['origin']=[0.,0.]
        app.mounting_plan['site']['roof_reference']='Toit zone A'
        for config in app.mounting_plan['panels'].values():config['count']=12
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'dossier.pdf'
            summary=write_installer_pdf(app,path)
            self.assertEqual(summary['fixing_points'],24)
            doc=fitz.open(str(path))
            self.assertGreaterEqual(len(doc),5)
            self.assertEqual(round(doc[0].rect.width),1191)
            content=' '.join(p.get_text() for p in doc)
            self.assertIn('Toit zone A',content)
            self.assertIn('F12',content)
            self.assertIn('CLAMP CONTACT COORDINATES',content)
            doc.close()


if __name__=='__main__':unittest.main()
