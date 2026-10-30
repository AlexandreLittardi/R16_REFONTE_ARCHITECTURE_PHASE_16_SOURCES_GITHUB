"""Phase 3 contracts: pure string edits, explicit topology events and gesture intent."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from application.events import ElectricalTopologyChanged, EventBus
from domain.string_commands import add_panel, remove_panel, remove_at, reorder_panel
from mixins.safe_project import SafeProjectMixin
from mixins.project_integrity import ProjectIntegrityMixin
from mixins.stringing_tools import StringingToolsMixin
from mixins.equipment_tools import EquipmentToolsMixin
from ui.gesture_policy import LeftGesture, press_intent, drag_intent
from ui.tab_ids import TabId


class PureStringCommandTests(unittest.TestCase):
    def setUp(self):
        self.original = {'String 1': [(0,0),(0,1)], 'String 2': [(1,0)]}
        self.snapshot = copy.deepcopy(self.original)

    def tearDown(self):
        self.assertEqual(self.original, self.snapshot, 'input mutated')

    def test_add_to_new_string_and_detect_existing_owner(self):
        edit=add_panel(self.original,'String 3',(2,0))
        self.assertTrue(edit.changed)
        self.assertEqual(edit.strings['String 3'],[(2,0)])
        duplicate=add_panel(self.original,'String 2',(0,0))
        self.assertFalse(duplicate.changed)
        self.assertEqual(duplicate.owner,'String 1')
        self.assertIs(duplicate.strings,self.original)

    def test_remove_from_owning_string(self):
        edit=remove_panel(self.original,(1,0))
        self.assertEqual(edit.owner,'String 2')
        self.assertEqual(edit.strings['String 2'],[])
        self.assertEqual(self.original['String 2'],[(1,0)])
        self.assertFalse(remove_panel(self.original,(99,99)).changed)

    def test_order_and_remove_at_boundaries(self):
        swapped=reorder_panel(self.original,'String 1',0,+1)
        self.assertEqual(swapped.strings['String 1'],[(0,1),(0,0)])
        self.assertFalse(reorder_panel(self.original,'String 1',1,+1).changed)
        self.assertFalse(reorder_panel(self.original,'String 1',-1,+1).changed)
        edit=remove_at(self.original,'String 1',0)
        self.assertEqual(edit.strings['String 1'],[(0,1)])
        self.assertFalse(remove_at(self.original,'String 1',10).changed)


class GesturePolicyTests(unittest.TestCase):
    def test_press_routing(self):
        self.assertEqual(press_intent(TabId.INSTALLATION,path_mode='select_polygon',polygon_index=0), LeftGesture.INSTALLATION_POLYGON)
        self.assertEqual(press_intent(TabId.INSTALLATION,path_mode='select_polygon'), LeftGesture.INSTALLATION_CANVAS)
        self.assertEqual(press_intent(TabId.SINGLE_LINE), LeftGesture.DELEGATE)
        self.assertEqual(press_intent(TabId.MOUNTING), LeftGesture.DELEGATE)

    def test_drag_routing(self):
        self.assertEqual(drag_intent(TabId.INSTALLATION,polygon_drag_mode='vertex',polygon_index=0),LeftGesture.INSTALLATION_POLYGON)
        self.assertEqual(drag_intent(TabId.INSTALLATION),LeftGesture.INSTALLATION_CANVAS)
        self.assertEqual(drag_intent(TabId.SINGLE_LINE),LeftGesture.DELEGATE)
        self.assertEqual(drag_intent(TabId.STRINGING),LeftGesture.DELEGATE)


class ElectricalLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.bus=EventBus()
        self.events=[]
        self.bus.subscribe(self.events.append)

    def test_notify_emits_domain_event_once(self):
        obj=SimpleNamespace(_project_events=self.bus)
        ProjectIntegrityMixin._notify_wiring_change(obj,'mppt:assign')
        self.assertEqual(self.events,[ElectricalTopologyChanged('mppt:assign')])

    def test_bus_projects_before_render_and_batches_same_topology(self):
        data={
            'blocks':{'INV':{'mppt_count':1}},
            'strings':{'String 1':[(0,0)]},
            'string_mppt_assignment':{},
            'diagram_nodes':{'user::meter':{'type':'custom','label':'Meter','x':27,'y':19}},
            'diagram_links':[],
        }
        owner=SimpleNamespace(**copy.deepcopy(data),
            _diagram_signature=None, var_continuous_numbers=object(),
            _refresh_diagram_list=Mock(),diagram_list=object(), _restoring=False)
        def snapshot():
            return dict(blocks=owner.blocks,
                strings={k:[f'{r},{c}' for r,c in v] for k,v in owner.strings.items()},
                string_mppt_assignment=owner.string_mppt_assignment,
                diagram_nodes=owner.diagram_nodes,diagram_links=owner.diagram_links)
        owner._project_snapshot=snapshot
        owner._synchronize_diagram_projection=lambda:ProjectIntegrityMixin._synchronize_diagram_projection(owner)
        owner._queue_history=Mock()
        owner._project_events=EventBus()
        owner._project_events.subscribe(lambda e:SafeProjectMixin._on_domain_event(owner,e))
        ProjectIntegrityMixin._notify_wiring_change(owner,'string:add_panel')
        self.assertEqual(owner._refresh_diagram_list.call_count,1)
        self.assertEqual(owner.diagram_nodes['user::meter']['x'],27)
        ProjectIntegrityMixin._notify_wiring_change(owner,'string:add_panel')
        self.assertEqual(owner._refresh_diagram_list.call_count,1)
        owner.strings['String 1'].append((0,1))
        ProjectIntegrityMixin._notify_wiring_change(owner,'string:add_panel')
        self.assertEqual(owner._refresh_diagram_list.call_count,2)
        self.assertEqual(owner._queue_history.call_count,3)

    def test_string_ui_adapter_notifies_before_draw(self):
        calls=[]
        owner=SimpleNamespace(strings={'String 1':[]},active_string_id='String 1',manual_strings=set(),
            _update_string_listbox=lambda:calls.append('list'),
            _notify_wiring_change=lambda s:calls.append('event:'+s),
            draw_grid=lambda:calls.append('draw'))
        StringingToolsMixin.add_panel_to_string(owner,(0,0))
        self.assertEqual(owner.strings,{'String 1':[(0,0)]})
        self.assertEqual(calls,['list','event:string:add_panel','draw'])
        StringingToolsMixin.remove_panel_from_strings(owner,(0,0))
        self.assertEqual(owner.strings,{'String 1':[]})
        self.assertEqual(calls[-3:],['list','event:string:remove_panel','draw'])

    def test_mppt_adapter_notifies_on_actual_assignment_only(self):
        calls=[]
        owner=SimpleNamespace(strings={'S':[(0,0)]},blocks={'INV':{'max_strings_per_mppt':2}},
            string_mppt_assignment={},_notify_wiring_change=lambda s:calls.append(s))
        self.assertTrue(EquipmentToolsMixin._assign_string_to_mppt(owner,'S','INV',1))
        self.assertTrue(EquipmentToolsMixin._assign_string_to_mppt(owner,'S','INV',1))
        self.assertEqual(calls,['mppt:assign'])
        EquipmentToolsMixin._unassign_string_from_mppt(owner,'S')
        EquipmentToolsMixin._unassign_string_from_mppt(owner,'S')
        self.assertEqual(calls,['mppt:assign','mppt:unassign'])


if __name__=='__main__':
    unittest.main()
