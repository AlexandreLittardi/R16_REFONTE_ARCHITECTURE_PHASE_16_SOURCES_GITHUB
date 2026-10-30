"""Pure phase-7 Installation gesture and MRO ownership regressions."""
import unittest

from ui.gesture_hit_testing import zone_at_point, zone_resize_handle, dimension_label_at
from mixins.workspace_improvements import WorkspaceImprovementsMixin
from mixins.editor_interactions import EditorInteractionsMixin
from app import PVLayoutRibbonApp


class GestureGeometryTest(unittest.TestCase):
    def setUp(self):
        self.zones = [
            dict(x1=10., x2=50., y1=20., y2=70.),
            dict(x1=30., x2=90., y1=60., y2=100.),
        ]

    def test_first_zone_wins_in_overlap(self):
        self.assertEqual(zone_at_point(self.zones, 35, 65, 1), 0)

    def test_zoomed_reverse_coordinate_zone(self):
        reversed_zone = dict(x1=50, x2=10, y1=70, y2=20)
        self.assertEqual(zone_at_point([reversed_zone], 60, 100, 2), 0)

    def test_empty_and_outside_zone(self):
        self.assertIsNone(zone_at_point([], 30, 40, 1))
        self.assertIsNone(zone_at_point(self.zones, 9.99, 20, 1))

    def test_boundary_is_inclusive(self):
        self.assertEqual(zone_at_point(self.zones, 10, 20, 1), 0)
        self.assertEqual(zone_at_point(self.zones, 90, 100, 1), 1)

    def test_corner_names_and_priority(self):
        z = self.zones[0]
        self.assertEqual(zone_resize_handle(z, 20, 40, 2), 'resize_tl')
        self.assertEqual(zone_resize_handle(z, 100, 40, 2), 'resize_tr')
        self.assertEqual(zone_resize_handle(z, 20, 140, 2), 'resize_bl')
        self.assertEqual(zone_resize_handle(z, 100, 140, 2), 'resize_br')

    def test_handle_tolerance_in_canvas_pixels(self):
        z = self.zones[0]
        self.assertEqual(zone_resize_handle(z, 27.99, 40, 2), 'resize_tl')
        self.assertIsNone(zone_resize_handle(z, 28.01, 48.01, 2))

    def test_reversed_zone_handle(self):
        z = dict(x1=50, x2=10, y1=70, y2=20)
        self.assertEqual(zone_resize_handle(z, 20, 40, 2), 'resize_tl')

    def test_measure_last_label_on_top(self):
        measures = [dict(label=(10, 10)), dict(label=(10, 10))]
        self.assertEqual(dimension_label_at(measures, 20, 20, 2), 1)

    def test_measure_ignores_old_tuple_format(self):
        self.assertEqual(dimension_label_at([((1, 1), (2, 2)), dict(label=(15, 5))], 30, 10, 2), 1)

    def test_measure_hit_uses_strict_threshold(self):
        measures = [dict(label=(20, 20))]
        self.assertIsNone(dimension_label_at(measures, 20 + 58, 20, 1))
        self.assertEqual(dimension_label_at(measures, 20 + 57, 20, 1), 0)

    def test_empty_measure(self):
        self.assertIsNone(dimension_label_at([], 10, 10, 1))


class GestureOwnershipTest(unittest.TestCase):
    def test_passthrough_workspace_handlers_removed(self):
        self.assertNotIn('on_left_press', WorkspaceImprovementsMixin.__dict__)
        self.assertNotIn('on_left_drag', WorkspaceImprovementsMixin.__dict__)
        self.assertNotIn('on_left_release', WorkspaceImprovementsMixin.__dict__)

    def test_left_handlers_have_four_owners(self):
        from tools.report_mro import colliding_methods
        collisions = colliding_methods()
        for method in ('on_left_press', 'on_left_drag', 'on_left_release'):
            self.assertEqual(len(collisions[method]), 4)
        self.assertEqual(collisions['on_left_press'][0], 'MountingMixin')
        self.assertIn('EditorInteractionsMixin', collisions['on_left_press'])

    def test_editor_still_owns_installation(self):
        self.assertIn('on_left_press', EditorInteractionsMixin.__dict__)
        self.assertIn('on_left_drag', EditorInteractionsMixin.__dict__)
        self.assertIn('on_left_release', EditorInteractionsMixin.__dict__)


if __name__ == '__main__':
    unittest.main()
