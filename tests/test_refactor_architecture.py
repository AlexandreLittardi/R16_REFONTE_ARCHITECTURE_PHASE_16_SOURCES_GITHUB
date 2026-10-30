"""Contracts established by architecture migration; no Tkinter required."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from application.events import EventBus, RoutingAreaChanged
from application.routing_commands import MoveRoutingArea
from application.undo_redo import LARGE_FIELDS, make_history_payload, history_signature
from domain.project_document import ProjectDocument
from domain.project_consistency import reconcile_panel_uids
from domain.routing_geometry import update_routing_area
from infrastructure.json_repository import ProjectRepository
from project_store import SCHEMA_VERSION
from ui.tab_ids import TabId, DRAWING_TABS, SHARED_CAMERA_TABS


class ProjectBoundaryTests(unittest.TestCase):
    def test_snapshot_defensively_copies_nested_values_in_both_directions(self):
        incoming={'schema_version':2,'roof_polygons':[{'points':[[0,0],[2,0],[2,2]]}],
                  'external_extension':{'tool':'not-to-be-dropped'}}
        doc=ProjectDocument(incoming)
        reference=doc.signature
        incoming['roof_polygons'][0]['points'][0][0]=200
        obtained=doc.snapshot(); obtained['roof_polygons'][0]['points'][0][1]=500
        self.assertEqual(doc.get('roof_polygons')[0]['points'][0],[0,0])
        self.assertEqual(doc.signature,reference)
        self.assertEqual(doc.get('external_extension'),{'tool':'not-to-be-dropped'})

    def test_replace_is_copy_on_write(self):
        before=ProjectDocument({'schema_version':2,'panels':{'0,0':1}})
        after=before.replace(panels={'0,0':99},new_extension=True)
        self.assertEqual(before.get('panels'),{'0,0':1})
        self.assertEqual(after.get('panels'),{'0,0':99})
        self.assertTrue(after.get('new_extension'))

    def test_schema_remains_v2(self):
        self.assertEqual(SCHEMA_VERSION,2)
        with self.assertRaises(ValueError):
            ProjectDocument({'schema_version':3})
        with self.assertRaises(TypeError):
            ProjectDocument([])

    def test_repository_preserves_unknown_fields_and_routes(self):
        repo=ProjectRepository()
        source=ProjectDocument({'schema_version':2,'project_name':'Roundtrip',
            'panels':{},'strings':{},'roof_polygons':[
                {'id':5,'points':[[0,0],[20,0],[20,10],[0,10]],'height_m':11}],
            'roof_image_offset':[14.3,-18.5],
            'cable_paths':[{'id':3,'points':[[1,2],[3,4]]}],
            'legacy_extension':{'nested':['retained']}})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'project.json'
            saved=repo.write(path,source)
            loaded=repo.read(path)
            self.assertEqual(loaded.get('roof_polygons'),source.get('roof_polygons'))
            self.assertEqual(loaded.get('cable_paths'),source.get('cable_paths'))
            self.assertEqual(loaded.get('roof_image_offset'),source.get('roof_image_offset'))
            self.assertEqual(loaded.get('legacy_extension'),source.get('legacy_extension'))
            self.assertEqual(saved['schema_version'],2)
            second=source.replace(project_name='Edited')
            repo.write(path,second)
            self.assertTrue(list((Path(folder)/'.backups').glob('project.json.*.bak')))

    def test_recovery_does_not_modify_existing_json(self):
        repo=ProjectRepository()
        with tempfile.TemporaryDirectory() as folder:
            main=Path(folder)/'site.json'
            orig=ProjectDocument({'project_name':'Initial'})
            repo.write(main,orig)
            blob=main.read_bytes()
            recovery=repo.recovery_path(main,'uid-1234',folder)
            repo.write(recovery,orig.replace(project_name='Recovery'),recovery=True)
            self.assertEqual(main.read_bytes(),blob)
            self.assertEqual(repo.read(recovery).get('project_name'),'Recovery')

    def test_repository_rejects_invalid_schema_without_changing_existing_file(self):
        repo=ProjectRepository()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'project.json'
            repo.write(path,ProjectDocument({'project_name':'Stable'}))
            original=path.read_bytes()
            with self.assertRaises(ValueError):
                repo.write(path,ProjectDocument({'schema_version':2,'panel_width_mm':-1}))
            self.assertEqual(path.read_bytes(),original)


class CommandAndEventsTests(unittest.TestCase):
    def setUp(self):
        self.areas=[{'id':1,'points':[(0,0),(10,0),(10,10),(0,10)],'height_m':11},
                    {'id':2,'points':[(20,0),(30,0),(30,10),(20,10)]}]

    def test_area_move_is_absolute_and_preserves_metadata(self):
        points=tuple(self.areas[0]['points'])
        result,events=MoveRoutingArea(0,points,4,-2).execute(self.areas)
        self.assertEqual(result[0]['points'][0],(4,-2))
        self.assertEqual(result[0]['height_m'],11)
        self.assertEqual(result[1],self.areas[1])
        self.assertEqual(self.areas[0]['points'][0],(0,0))
        self.assertEqual(events,(RoutingAreaChanged(0),))

    def test_vertex_drags_do_not_translate_other_points(self):
        result,_=MoveRoutingArea(0,tuple(self.areas[0]['points']),-1,2,vertex=1).execute(self.areas)
        self.assertEqual(result[0]['points'][1],(9,2))
        self.assertEqual(result[0]['points'][0],(0,0))

    def test_invalid_self_crossing_shape_rejected_without_mutation(self):
        before=copy.deepcopy(self.areas)
        # Moving the bottom-left vertex across the diagonal creates a crossing.
        result=update_routing_area(self.areas,0,self.areas[0]['points'],12,5,vertex=0)
        self.assertIsNone(result)
        self.assertEqual(self.areas,before)

    def test_no_op_command_has_no_event(self):
        result,events=MoveRoutingArea(0,tuple(self.areas[0]['points']),0,0).execute(self.areas)
        self.assertIsNone(result)
        self.assertEqual(events,())

    def test_events_can_be_subscribed_and_removed(self):
        bus=EventBus();observed=[]
        def listen(event):observed.append(event)
        bus.subscribe(listen);bus.subscribe(listen)
        bus.emit(RoutingAreaChanged(0));self.assertEqual(observed,[RoutingAreaChanged(0)])
        bus.unsubscribe(listen);bus.emit(RoutingAreaChanged(1))
        self.assertEqual(len(observed),1)

    def test_reconcile_identifiers_preserves_existing_values(self):
        old={(0,0):'A',(0,1):'B',(1,1):'obsolete'}
        updated=reconcile_panel_uids(old,{(0,0):1,(0,1):2,(0,2):3},id_factory=lambda:'C')
        self.assertEqual(updated,{(0,0):'A',(0,1):'B',(0,2):'C'})
        self.assertEqual(old[(1,1)],'obsolete')


class HistoryAndNavigationContracts(unittest.TestCase):
    def test_history_shares_large_unchanged_nested_payload(self):
        heavy={'samples':[{'x':i,'y':i*i} for i in range(100)]}
        first=make_history_payload({'panels':{'0,0':1},'shadow_simulation_results':heavy})
        second=make_history_payload({'panels':{'0,0':2},'shadow_simulation_results':heavy},first)
        self.assertIs(first['shadow_simulation_results'],second['shadow_simulation_results'])
        self.assertNotEqual(history_signature(first,{},None),history_signature(second,{},None))

    def test_history_snapshot_is_serializable(self):
        result=make_history_payload({'roof_polygons':[{'points':[(1,2),(3,4)]}],
                                     'hourly_pv_kwh':(1,2,3)})
        json.dumps(result)
        self.assertEqual(result['roof_polygons'][0]['points'],[[1,2],[3,4]])

    def test_zoom_only_does_not_modify_edit_history_signature(self):
        data={'panels':{'0,0':1}}
        self.assertEqual(history_signature(data,{'zoom_level':1.0},None),
                         history_signature(data,{'zoom_level':2.0},None))

    def test_selected_active_mro_implementations_survive_cleanup(self):
        from app import PVLayoutRibbonApp
        from mixins.diagram_editor import DiagramEditorMixin
        from mixins.responsive_ui import ResponsiveUIMixin
        from mixins.safe_project import SafeProjectMixin
        from mixins.diagram_tools import DiagramToolsMixin
        from mixins.project_workspace import ProjectWorkspaceMixin
        from mixins.ui_builders import UIBuildersMixin
        for name,owner in (('_draw_diagram',DiagramEditorMixin),
                           ('_export_engineering_report',SafeProjectMixin),
                           ('_build_root_scroller',ResponsiveUIMixin)):
            winner=next(cls for cls in PVLayoutRibbonApp.__mro__ if name in vars(cls))
            self.assertIs(winner,owner)
        self.assertNotIn('_draw_diagram',vars(DiagramToolsMixin))
        self.assertNotIn('_export_engineering_report',vars(ProjectWorkspaceMixin))
        self.assertNotIn('_build_root_scroller',vars(UIBuildersMixin))

    def test_tab_identity_matches_existing_ui_indices(self):
        self.assertEqual([int(i) for i in TabId],list(range(11)))
        self.assertIn(TabId.MOUNTING,DRAWING_TABS)
        self.assertNotIn(TabId.MOUNTING,SHARED_CAMERA_TABS)
        self.assertIn(TabId.CABLING,SHARED_CAMERA_TABS)
        self.assertNotIn(TabId.SPREADSHEET,DRAWING_TABS)


if __name__=='__main__':
    unittest.main()
