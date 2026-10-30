"""Editing/hiding visual dimension labels must not alter survey geometry."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mounting import validate_plan,fixings
from mounting_drawing import geometry,construction_shapes,annotations,scene,write_svg
from mounting_installer import write_installer_pdf
from report_mounting import motifs
from mixins.mounting_ui import MountingMixin
from test_mounting import fixture


def label(shapes, dim_id):
    return next(s['text'] for s in shapes if s.get('dim_id')==dim_id and s['kind']=='text')


class EditingHarness(MountingMixin):
    def __init__(self):
        app=fixture()
        self.__dict__.update(app.__dict__)
        self.selected_panel_coords={(0,0)}
        self._mounting_items=geometry(self)
        self._mounting_selected_dimension=None
        self._mounting_selected_live_dimension='field:x'
        self._mounting_selected_fixing=None
        self.zoom_level=1.
        self.root=None
        self.calls=[]
    def _mounting_active(self):return True
    def _record_history(self):self.calls.append('history')
    def _queue_history(self):self.calls.append('queue')
    def _draw_mounting_annotations(self):self.calls.append('redraw')
    def _mounting_update_status(self):self.calls.append('status')
    def draw_grid(self):self.calls.append('grid')


class LabelTests(unittest.TestCase):
    def test_override_save_restore_hide_and_calculations(self):
        app=fixture()
        app.selected_panel_coords={(0,0)}
        original=copy.deepcopy(app.mounting_plan['panels'])
        before=construction_shapes(app,geometry(app),selected=app.selected_panel_coords)
        self.assertEqual(label(before,'field:x'),'X champ = 2803.0 mm')
        app.mounting_plan['dimension_labels']['field:x']='Longueur hors tout (voir implantation)'
        app.mounting_plan['dimension_labels']['panel:one:chain:0:0']='Retrait A - axe pince'
        after=construction_shapes(app,geometry(app),selected=app.selected_panel_coords)
        self.assertEqual(label(after,'field:x'),'Longueur hors tout (voir implantation)')
        self.assertEqual(label(after,'panel:one:chain:0:0'),'Retrait A - axe pince')
        self.assertEqual(app.mounting_plan['panels'],original)
        roundtrip=validate_plan(app.mounting_plan)
        self.assertEqual(roundtrip['dimension_labels'],app.mounting_plan['dimension_labels'])
        app.mounting_plan['hidden_dimensions']=['field:x','panel:one:chain:0:0']
        shapes=construction_shapes(app,geometry(app),selected=app.selected_panel_coords)
        self.assertFalse(any(s.get('dim_id') in app.mounting_plan['hidden_dimensions'] for s in shapes))
        self.assertEqual(app.mounting_plan['panels'],original)
        self.assertEqual([f['position_mm'] for f in fixings(app.mounting_plan['panels']['one'])],
                         [f['position_mm'] for f in fixings(original['one'])])

    def test_local_project_file_preserves_label_and_hidden_dimension(self):
        from project_store import write_project,validate_project
        import json
        app=fixture()
        app.mounting_plan['dimension_labels']['field:x']='COTE A CONTROLER'
        app.mounting_plan['hidden_dimensions']=['field:y']
        app.mounting_plan['dimensions'].append(dict(p1=(0,0),p2=(100,0),
            label=(50,-10),axis='aligned',text_override='AXE COTE'))
        data={'panel_width_mm':1303,'panel_height_mm':2384,'panels':{'0,0':1,'0,1':2},
              'panel_uids':{'0,0':'one','0,1':'two'},'mounting_plan':app.mounting_plan}
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'chantier.json'
            write_project(file,data)
            loaded=validate_project(json.loads(file.read_text(encoding='utf-8')))
            plan=loaded['mounting_plan']
            self.assertEqual(plan['dimension_labels']['field:x'],'COTE A CONTROLER')
            self.assertIn('field:y',plan['hidden_dimensions'])
            self.assertEqual(plan['dimensions'][0]['text_override'],'AXE COTE')
            self.assertEqual(plan['panels'],validate_plan(app.mounting_plan)['panels'])

    def test_manual_associative_dimension_override(self):
        app=fixture()
        d=dict(p1=(0,0),p2=(100,0),label=(50,-30),axis='aligned',text_override='Référence pose')
        app.mounting_plan['dimensions']=[d]
        shapes=annotations(app.mounting_plan,geometry(app),.1)
        self.assertEqual(next(s['text'] for s in shapes if s['kind']=='text'),'Référence pose')
        self.assertEqual(validate_plan(app.mounting_plan)['dimensions'][0]['label'],(50,-30))
        for bad in ('','A'*161,'a\nb',27):
            with self.subTest(bad=bad):
                invalid=copy.deepcopy(app.mounting_plan)
                invalid['dimensions'][0]['text_override']=bad
                with self.assertRaises(ValueError):validate_plan(invalid)
        for invalid_value in ('','x'*161,'bad\rlabel',12):
            with self.subTest(value=invalid_value):
                invalid=copy.deepcopy(app.mounting_plan)
                invalid['dimension_labels']={'field:y':invalid_value}
                with self.assertRaises(ValueError):validate_plan(invalid)

    def test_edit_reset_and_delete_on_interaction_do_not_change_geometry(self):
        app=EditingHarness()
        original=copy.deepcopy(app.mounting_plan['panels'])
        with patch('mixins.mounting_ui.simpledialog.askstring',return_value='Repère de chantier H1'):
            self.assertEqual(app._mounting_edit_dimension_label(),'break')
        self.assertEqual(app.mounting_plan['dimension_labels']['field:x'],'Repère de chantier H1')
        self.assertEqual(app.mounting_plan['panels'],original)
        app._mounting_reset_dimension_label()
        self.assertNotIn('field:x',app.mounting_plan['dimension_labels'])
        app._mounting_delete()
        self.assertIn('field:x',app.mounting_plan['hidden_dimensions'])
        self.assertEqual(app.mounting_plan['panels'],original)
        app._mounting_restore_dimensions()
        self.assertEqual(app.mounting_plan['hidden_dimensions'],[])
        app.mounting_plan['dimensions']=[dict(p1=(0,0),p2=(100,0),label=(50,-30),axis='aligned')]
        app._mounting_selected_dimension=0;app._mounting_selected_live_dimension=None
        with patch('mixins.mounting_ui.simpledialog.askstring',return_value='Axe de référence'):
            app._mounting_edit_dimension_label()
        self.assertEqual(app.mounting_plan['dimensions'][0]['text_override'],'Axe de référence')
        self.assertEqual(app.mounting_plan['dimensions'][0]['p2'],(100,0))
        app._mounting_delete()
        self.assertEqual(app.mounting_plan['dimensions'],[])
        self.assertEqual(app.mounting_plan['panels'],original)

    def test_pdf_svg_overrides_and_distinct_motifs(self):
        import fitz
        app=fixture()
        app.mounting_plan['dimension_labels']['field:x']='COTE CHANTIER GENERALE'
        app.mounting_plan['dimension_labels']['panel:one:chain:0:0']='RETRAIT AXE CUSTOM P1'
        app.mounting_plan['dimension_labels']['panel:two:chain:0:0']='RETRAIT AXE CUSTOM P2'
        app.mounting_plan['hidden_dimensions'].append('field:y')
        groups,_=motifs(geometry(app),app.mounting_plan)
        self.assertEqual(len(groups),2)
        app.selected_panel_coords={(0,0)}
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            svg=folder/'drawing.svg';pdf=folder/'drawing.pdf'
            write_svg(app,svg)
            self.assertIn('COTE CHANTIER GENERALE',svg.read_text())
            self.assertNotIn('Y champ = ',svg.read_text())
            write_installer_pdf(app,pdf)
            doc=fitz.open(pdf)
            texts=' '.join(page.get_text() for page in doc)
            self.assertIn('COTE CHANTIER GENERALE',texts)
            self.assertIn('RETRAIT AXE CUSTOM P1',texts)
            self.assertIn('RETRAIT AXE CUSTOM P2',texts)
            self.assertEqual(len(groups),2)
            doc.close()

if __name__=='__main__':unittest.main()
