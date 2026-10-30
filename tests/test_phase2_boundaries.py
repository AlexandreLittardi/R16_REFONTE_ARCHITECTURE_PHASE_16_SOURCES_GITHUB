"""Contracts for the Phase 2 electrical projection and layout row remapping."""
import copy
import unittest
from types import SimpleNamespace

from application.diagram_projection import diagram_projection, wiring_signature
from domain.layout_remap import remap_address, remap_zone_state
from mixins.project_integrity import ProjectIntegrityMixin
from mixins.safe_project import SafeProjectMixin
from project_validation import sync_diagram


class DiagramProjectionTests(unittest.TestCase):
    def setUp(self):
        self.project = {
            'blocks': {'INV-1': {'mppt_count': 2}},
            'strings': {'String 1': ['0,0', '0,1'], 'String 2': ['1,0']},
            'string_mppt_assignment': {
                'String 1': {'block': 'INV-1', 'mppt': 1},
                'String 2': {'block': 'INV-1', 'mppt': 2}},
            'diagram_nodes': {
                'str::String 1': {'type': 'string', 'label': 'Custom label', 'x': 123, 'y': 456},
                'junction': {'type': 'custom', 'label': 'J', 'x': 20, 'y': 30}},
            'diagram_links': [{'a': 'junction', 'b': 'str::String 1', 'auto': False},
                              {'a': 'junction', 'b': 'junction', 'auto': False}],
        }

    def test_projection_matches_existing_diagram_algorithm(self):
        before = copy.deepcopy(self.project)
        expected = sync_diagram(copy.deepcopy(before))
        nodes, links = diagram_projection(self.project)
        self.assertEqual(nodes, expected['diagram_nodes'])
        self.assertEqual(links, expected['diagram_links'])

    def test_projection_preserves_caller_and_manual_device(self):
        before = copy.deepcopy(self.project)
        nodes, links = diagram_projection(self.project)
        nodes['junction']['x'] = 999
        links.append({'a': 'x', 'b': 'y'})
        self.assertEqual(self.project, before)
        self.assertEqual(self.project['diagram_nodes']['junction']['x'], 20)

    def test_custom_positions_remain_stable(self):
        nodes, links = diagram_projection(self.project)
        self.assertEqual((nodes['str::String 1']['x'], nodes['str::String 1']['y']), (123,456))
        self.assertIn({'a':'junction','b':'junction','auto':False}, links)
        self.assertEqual(len([n for n in nodes if n.startswith('mppt::')]), 2)

    def test_diagram_signature_compatible_with_legacy(self):
        project=self.project
        self.assertEqual(wiring_signature(project['strings'],project['string_mppt_assignment'],project['blocks']),
                         repr((project['strings'],project['string_mppt_assignment'],project['blocks'])))

    def test_unchanged_topology_does_not_recalculate(self):
        p=self.project
        calls=[]
        owner=SimpleNamespace(strings=p['strings'],string_mppt_assignment=p['string_mppt_assignment'],
            blocks=p['blocks'],diagram_nodes=p['diagram_nodes'],diagram_links=p['diagram_links'],
            var_continuous_numbers=object(), _diagram_signature=None,
            _project_snapshot=lambda:copy.deepcopy(p), _refresh_diagram_list=lambda:calls.append(True),
            diagram_list=object())
        self.assertTrue(ProjectIntegrityMixin._synchronize_diagram_projection(owner))
        nodes=owner.diagram_nodes
        self.assertFalse(ProjectIntegrityMixin._synchronize_diagram_projection(owner))
        self.assertIs(nodes,owner.diagram_nodes)
        self.assertEqual(len(calls),1)
        owner.strings['String 2'].append('1,1')
        self.assertTrue(ProjectIntegrityMixin._synchronize_diagram_projection(owner))
        self.assertEqual(len(calls),2)

    def test_integrity_mixin_has_no_hidden_draw_grid_override(self):
        from mixins.project_integrity import ProjectIntegrityMixin
        from app import PVLayoutRibbonApp
        self.assertNotIn('draw_grid', vars(ProjectIntegrityMixin))
        chain=[cls.__name__ for cls in PVLayoutRibbonApp.__mro__ if 'draw_grid' in vars(cls)]
        self.assertEqual(chain, ['SafeProjectMixin','MountingMixin','CanvasGridMixin'])

    def test_missing_widgets_skip_projection(self):
        owner=SimpleNamespace(diagram_nodes={},_diagram_signature=None)
        self.assertFalse(ProjectIntegrityMixin._synchronize_diagram_projection(owner))

    def test_project_reconciliation_skips_while_uninitialized(self):
        calls=[]
        owner=SimpleNamespace(_guard_ready=False,
            _synchronize_diagram_projection=lambda:calls.append('diagram'))
        self.assertFalse(SafeProjectMixin._reconcile_project_state(owner))
        self.assertEqual(calls,[])

    def test_project_reconciliation_commits_shadow_uids_and_wiring(self):
        calls=[]
        owner=SimpleNamespace(_guard_ready=True,
            _synchronize_diagram_projection=lambda:calls.append('diagram'),
            _shadow_signature=lambda:'new',
            shadow_result={'source_signature':'old'},
            panel_uids={(0,0):'uid-stable',(9,9):'old'},
            panels={(0,0):1,(0,1):2},
            strings={'A':[(0,0)]},string_mppt_assignment={},blocks={},
            _diagram_signature=None)
        self.assertTrue(SafeProjectMixin._reconcile_project_state(owner))
        self.assertEqual(owner.shadow_result,{})
        self.assertEqual(owner.panel_uids[(0,0)],'uid-stable')
        self.assertNotIn((9,9),owner.panel_uids)
        self.assertEqual(set(owner.panel_uids),{(0,0),(0,1)})
        self.assertEqual(calls,['diagram'])



class LayoutRemapTests(unittest.TestCase):
    def test_address_interval_is_half_open(self):
        self.assertEqual(remap_address((100,4),100,3,600),(600,4))
        self.assertEqual(remap_address((102,4),100,3,600),(602,4))
        self.assertEqual(remap_address((103,4),100,3,600),(103,4))
        self.assertEqual(remap_address((99,4),100,3,600),(99,4))

    def test_remap_all_domains_without_changing_input(self):
        original=dict(
            panels={(100,0):10,(100,1):11,(8,0):12},
            panel_blocks={(100,1):'A'},
            panel_orientations={(100,0):90},
            panel_uids={(100,0):'uid-1',(8,0):'uid-2'},
            layout_geometry={'100,0':'hash1','8,0':'hash2'},
            strings={'S1':[(100,1),(8,0)],'S2':[(100,0)]},
            selected_panel_coords={(100,0),(8,0)})
        before=copy.deepcopy(original)
        output=remap_zone_state(100,4,450,**original)
        self.assertEqual(original,before)
        self.assertEqual(output['panels'],{(450,0):10,(450,1):11,(8,0):12})
        self.assertEqual(output['panel_uids'][(450,0)],'uid-1')
        self.assertEqual(output['layout_geometry'],{'450,0':'hash1','8,0':'hash2'})
        self.assertEqual(output['strings']['S1'],[(450,1),(8,0)])
        self.assertEqual(output['selected_panel_coords'],{(450,0),(8,0)})
        self.assertEqual(output['panel_blocks'],{(450,1):'A'})
        self.assertEqual(output['panel_orientations'],{(450,0):90})

    def test_inverse_remap_round_trip_for_disjoint_ranges(self):
        model=dict(panels={(100,1):1,(101,2):2,(200,5):3},
                   strings={'S':[(100,1),(200,5)]},
                   panel_uids={(100,1):'A',(101,2):'B',(200,5):'C'})
        forward=remap_zone_state(100,3,900,**model)
        back=remap_zone_state(900,3,100,**forward)
        self.assertEqual(back,model)

    def test_missing_optional_fields_remain_absent(self):
        self.assertEqual(remap_zone_state(0,1,100),{})
        self.assertEqual(remap_zone_state(0,1,100,strings={}),{'strings':{}})


if __name__=='__main__':
    unittest.main()
