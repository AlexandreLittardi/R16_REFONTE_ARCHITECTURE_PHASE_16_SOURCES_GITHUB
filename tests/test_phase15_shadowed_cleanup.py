"""Phase 15: MRO contracts for proven-inaccessible legacy overrides.

Only definitions hidden by a higher MRO implementation that does not call
super() were removed.  This guards both the cleanup and the live owners.
"""
import unittest

from app import PVLayoutRibbonApp


# (Removed class, method, live owner in the application's actual MRO)
SHADOWED_METHODS = (
    ('DiagramToolsMixin', '_diagram_node_size', 'DiagramEditorMixin'),
    ('DiagramToolsMixin', '_diagram_screen_node_size', 'DiagramEditorMixin'),
    ('DiagramToolsMixin', '_on_diagram_list_select', 'EditorInteractionsMixin'),
    ('ZoneToolsMixin', '_zone_rotate_rect', 'InstallationGeometryMixin'),
    ('ZoneToolsMixin', 'generate_panels_from_zones', 'InstallationGeometryMixin'),
    ('ZoneToolsMixin', 'delete_active_zone', 'InstallationGeometryMixin'),
    ('CableNetworkMixin', 'compute_all_cable_routes', 'TwoPoleCablesMixin'),
    ('CableNetworkMixin', 'compute_cable_length_mm', 'TwoPoleCablesMixin'),
    ('WorkspaceImprovementsMixin', '_install_energy_workspace', 'ProjectWorkspaceMixin'),
    ('UIBuildersMixin', '_show_help', 'WorkspaceImprovementsMixin'),
    ('UIBuildersMixin', '_build_tab_file_tools', 'SafeProjectMixin'),
    ('UIBuildersMixin', '_build_tab_layout_tools', 'SafeProjectMixin'),
    ('SelfConsumptionMixin', '_import_historical_weather', 'SafeProjectMixin'),
    ('SelfConsumptionMixin', '_download_historical_weather', 'SafeProjectMixin'),
)


class ShadowedOverridesCleanupTest(unittest.TestCase):
    def test_removed_definitions_do_not_reappear(self):
        classes = {klass.__name__: klass for klass in PVLayoutRibbonApp.__mro__}
        for old_class, name, _active in SHADOWED_METHODS:
            with self.subTest(old_class=old_class, method=name):
                self.assertNotIn(name, vars(classes[old_class]))

    def test_active_implementations_have_not_changed(self):
        for _old_class, name, active in SHADOWED_METHODS:
            with self.subTest(method=name, owner=active):
                owners = [klass.__name__ for klass in PVLayoutRibbonApp.__mro__
                          if name in vars(klass)]
                self.assertTrue(owners)
                self.assertEqual(owners[0], active)
                self.assertTrue(callable(getattr(PVLayoutRibbonApp, name)))


if __name__ == '__main__':
    unittest.main()
