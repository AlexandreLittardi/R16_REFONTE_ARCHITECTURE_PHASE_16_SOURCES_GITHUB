"""Phase 5 contracts: data repairs are planned at edit/IO boundaries, not paint."""
import unittest

from domain.reconciliation_plan import ReconciliationPlan, plan_reconciliation
from mixins.safe_project import SafeProjectMixin


class ReconciliationPlanTests(unittest.TestCase):
    def plan(self, **overrides):
        data=dict(panel_coords={(1, 2)},uid_coords={(1, 2)},
                  shadow_has_result=False,shadow_source=None,current_shadow_source=None,
                  topology_signature='same',diagram_signature='same')
        data.update(overrides)
        return plan_reconciliation(**data)

    def test_clean_plan_requires_no_repair(self):
        self.assertEqual(self.plan(), ReconciliationPlan(False,False,False))
        self.assertFalse(self.plan().needed)

    def test_panel_ids_are_matched_by_coordinate_not_number(self):
        plan=self.plan(panel_coords={(1,2),(1,3)},uid_coords={(1,2)})
        self.assertTrue(plan.panel_ids)
        self.assertFalse(plan.wiring)

    def test_deleted_panel_invalidates_uids(self):
        self.assertTrue(self.plan(panel_coords=set()).panel_ids)

    def test_stale_shadow_result_only_with_stored_data(self):
        self.assertFalse(self.plan(shadow_source='old',current_shadow_source='new').shadow_result)
        self.assertTrue(self.plan(shadow_has_result=True,shadow_source='old',
                                  current_shadow_source='new').shadow_result)
        self.assertFalse(self.plan(shadow_has_result=True,shadow_source='new',
                                   current_shadow_source='new').shadow_result)

    def test_topology_mismatch_triggers_projection(self):
        self.assertTrue(self.plan(topology_signature='new').wiring)

    def test_all_repairs_are_independent(self):
        p=self.plan(panel_coords={(4,1)},uid_coords={(1,2)},
                    shadow_has_result=True,shadow_source='old',current_shadow_source='new',
                    topology_signature='new')
        self.assertEqual(p,ReconciliationPlan(True,True,True))
        self.assertTrue(p.needed)

    def test_safe_project_draw_has_no_reconciliation_call(self):
        from inspect import getsource
        self.assertNotIn('_reconcile_project_state(',getsource(SafeProjectMixin.draw_grid))
        self.assertNotIn('panel_uids',getsource(SafeProjectMixin.draw_grid))


if __name__=='__main__':
    unittest.main()
