"""Phase 4: pure diagram edits must not couple the drawing to Tk or save IO."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from domain.diagram_commands import (
    add_custom_node, add_manual_link, delete_nodes, move_nodes, position_nodes)
from mixins.diagram_editor import DiagramEditorMixin
from mixins.editor_interactions import EditorInteractionsMixin


class DiagramCommandTests(unittest.TestCase):
    def setUp(self):
        self.nodes = {
            'inv::I': {'type': 'inverter', 'x': 10, 'y': 20, 'meta': {'manufacturer': 'x'}},
            'custom::1': {'type': 'custom', 'label': 'Meter', 'x': 25, 'y': 40},
            'str::S': {'type': 'string', 'x': 0, 'y': 0},
        }
        self.links = [
            {'a': 'str::S', 'b': 'inv::I', 'auto': True, 'extension': {'ref': 7}},
            {'a': 'inv::I', 'b': 'custom::1', 'auto': False, 'style': 'dashed', 'distance_m': 3},
        ]
        self.original_nodes = copy.deepcopy(self.nodes)
        self.original_links = copy.deepcopy(self.links)

    def tearDown(self):
        self.assertEqual(self.nodes, self.original_nodes)
        self.assertEqual(self.links, self.original_links)

    def test_custom_node_preserves_existing_geometry_and_link_extensions(self):
        result = add_custom_node(self.nodes, self.links, 'custom::2', '  Switchboard  ',
                                 selected='custom::1', style='dotted', distance_m=2.5)
        self.assertTrue(result.changed)
        self.assertEqual(result.nodes['custom::2']['label'], 'Switchboard')
        self.assertEqual(result.nodes['inv::I']['meta']['manufacturer'], 'x')
        self.assertEqual(result.links[0]['extension'], {'ref': 7})
        self.assertEqual(result.links[-1], {'a': 'custom::1', 'b': 'custom::2',
                                            'auto': False, 'style': 'dotted', 'distance_m': 2.5})
        self.assertFalse(add_custom_node(self.nodes,self.links,'custom::1','Duplicate').changed)
        self.assertFalse(add_custom_node(self.nodes,self.links,'custom::2',' ').changed)
        self.assertFalse(add_custom_node(self.nodes,self.links,'custom::2','Item',distance_m=-1).changed)

    def test_link_creation_validates_endpoints_without_rewriting_old_links(self):
        result = add_manual_link(self.nodes, self.links,'str::S','custom::1',distance_m=5.5)
        self.assertTrue(result.changed)
        self.assertEqual(len(result.links),3)
        self.assertEqual(result.links[0], self.links[0])
        for end,dist in (('absent',1),('custom::1',-1),('custom::1',float('nan'))):
            self.assertFalse(add_manual_link(self.nodes,self.links,'custom::1',end,distance_m=dist).changed)
        self.assertFalse(add_manual_link(self.nodes,self.links,'str::S','str::S').changed)

    def test_delete_multiple_nodes_and_preserve_unrelated_links(self):
        result = delete_nodes(self.nodes,self.links,{'custom::1','str::S','missing'})
        self.assertTrue(result.changed)
        self.assertEqual(set(result.nodes),{'inv::I'})
        self.assertEqual(result.links,[])
        self.assertFalse(delete_nodes(self.nodes,self.links,{'absent'}).changed)

    def test_move_absolute_delta_without_drift_or_partial_modification(self):
        origins={'inv::I':(10,20),'custom::1':(25,40)}
        first=move_nodes(self.nodes,self.links,origins,6,-4)
        second=move_nodes(first.nodes,first.links,origins,9,-1)
        self.assertEqual(second.nodes['inv::I']['x'],19)
        self.assertEqual(second.nodes['custom::1']['y'],39)
        self.assertEqual(second.nodes['inv::I']['meta'],{'manufacturer':'x'})
        self.assertIs(second.links,self.links)
        self.assertFalse(move_nodes(second.nodes,self.links,origins,9,-1).changed)
        self.assertFalse(move_nodes(self.nodes,self.links,origins,float('inf'),2).changed)

    def test_layout_command_ignores_missing_ids_and_is_atomic(self):
        result=position_nodes(self.nodes,self.links,{'inv::I':(100,200),'missing':(5,5)})
        self.assertTrue(result.changed)
        self.assertEqual(result.nodes['inv::I']['x'],100)
        self.assertFalse(position_nodes(self.nodes,self.links,{'inv::I':(10,20)}).changed)
        self.assertFalse(position_nodes(self.nodes,self.links,{'inv::I':(11,22),'custom::1':(3,float('nan'))}).changed)


class DiagramBoundaryTests(unittest.TestCase):
    def test_commit_is_two_snapshots_and_does_not_paint(self):
        nodes={'custom::1':{'type':'custom','x':1,'y':2}}
        owner=SimpleNamespace(diagram_nodes=nodes,diagram_links=[],_guard_ready=True,
                              _restoring=False,_diagram_layout_applied=object(),
                              _record_history=Mock(),draw_grid=Mock())
        edit=move_nodes(nodes,[],{'custom::1':(1,2)},4,5)
        self.assertTrue(DiagramEditorMixin._apply_diagram_edit(owner,edit))
        self.assertEqual(owner._record_history.call_count,2)
        self.assertEqual(owner.diagram_nodes['custom::1']['x'],5)
        owner.draw_grid.assert_not_called()
        self.assertFalse(DiagramEditorMixin._apply_diagram_edit(owner,edit.__class__(nodes,[],False)))
        self.assertEqual(owner._record_history.call_count,2)

    def test_delete_effective_ui_method_delegates_and_preserves_unrelated(self):
        nodes={'custom::1':{'x':1,'y':2},'custom::2':{'x':10,'y':20}}
        owner=SimpleNamespace(diagram_nodes=nodes,diagram_links=[],diagram_selected_nodes={'custom::1'},
                              diagram_selected_node='custom::1',_refresh_diagram_list=Mock(),draw_grid=Mock())
        owner._apply_diagram_edit=lambda edit: DiagramEditorMixin._apply_diagram_edit(owner,edit)
        self.assertTrue(EditorInteractionsMixin._delete_selected_diagram_node(owner) is None)
        self.assertEqual(set(owner.diagram_nodes),{'custom::2'})
        owner.draw_grid.assert_called_once()


if __name__ == '__main__':
    unittest.main()
