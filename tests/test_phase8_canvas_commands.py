"""Phase 8: schema-compatible Installation and Cabling edit boundaries."""
import copy
import math
import unittest

from domain.installation_edits import (
    new_zone, resize_zone, translate_zones, ZONE_RECT_FIELDS)
from domain.cabling_edits import (
    add_temporary_vertex, create_cable_path, create_routing_area)
from mixins.canvas_grid import CanvasGridMixin
from mixins.paths_tools import PathsToolsMixin


class InstallationEditCommandsTest(unittest.TestCase):
    def test_move_multiple_zones_absolute_not_incremental(self):
        start = {0: (10, 20, 110, 220), 2: (35, 75, 55, 95)}
        frozen = copy.deepcopy(start)
        first = translate_zones(start, 5, -3)
        second = translate_zones(start, 7, -1)
        self.assertEqual(first[0], dict(x1=15, y1=17, x2=115, y2=217))
        self.assertEqual(second[0], dict(x1=17, y1=19, x2=117, y2=219))
        self.assertEqual(second[2], dict(x1=42, y1=74, x2=62, y2=94))
        self.assertEqual(start, frozen)

    def test_move_preserves_original_vertex_order(self):
        fields = translate_zones({4: (40, 60, 10, 20)}, -5, 3)[4]
        self.assertEqual(tuple(fields[k] for k in ZONE_RECT_FIELDS), (35, 63, 5, 23))

    def test_all_four_handles_absolute(self):
        initial = (100, 200, 300, 400)
        expected = {
            'resize_tl': (110, 220, 300, 400),
            'resize_tr': (100, 220, 310, 400),
            'resize_bl': (110, 200, 300, 420),
            'resize_br': (100, 200, 310, 420),
        }
        for handle, coords in expected.items():
            with self.subTest(handle=handle):
                fields = resize_zone(initial, handle, 10, 20, zoom=1, px_per_mm=2)
                self.assertEqual(tuple(fields[k] for k in ZONE_RECT_FIELDS), coords)
                self.assertEqual(fields['w_mm'], (coords[2] - coords[0]) / 2)
                self.assertEqual(fields['h_mm'], (coords[3] - coords[1]) / 2)

    def test_minimum_15_screen_pixels_not_image_pixels(self):
        fields = resize_zone((0, 0, 100, 100), 'resize_tl', 200, 200, zoom=2, px_per_mm=1)
        self.assertEqual((fields['x1'], fields['y1']), (92.5, 92.5))

    def test_without_scale_physical_dimensions_remain_unchanged(self):
        fields = resize_zone((0, 0, 100, 100), 'resize_br', 10, 20, zoom=1, px_per_mm=0)
        self.assertNotIn('w_mm', fields)
        self.assertNotIn('h_mm', fields)

    def test_no_partial_update_on_invalid_drag(self):
        original = {0: (0, 0, 100, 100)}
        with self.assertRaises(ValueError):
            translate_zones(original, math.nan, 4)
        self.assertEqual(original, {0: (0, 0, 100, 100)})
        with self.assertRaises(ValueError):
            resize_zone((0, 0, 100, 100), 'bad', 10, 20, zoom=1, px_per_mm=1)

    def test_new_zone_keeps_saved_schema(self):
        zone = new_zone((100, 250), (20, 40), zone_id=6, px_per_mm=2,
                        align_x='Right', align_y='Bottom')
        self.assertEqual(zone, {
            'id': 6, 'x1': 20, 'y1': 40, 'x2': 100, 'y2': 250,
            'w_mm': 40, 'h_mm': 105, 'align_x': 'Dro.', 'align_y': 'Bas'})

    def test_zero_scale_keeps_pixel_dimensions(self):
        zone = new_zone((0, 0), (50, 35), zone_id=1, px_per_mm=0,
                        align_x='Left', align_y='Top')
        self.assertEqual((zone['w_mm'], zone['h_mm']), (50, 35))


class CablingEditCommandsTest(unittest.TestCase):
    def test_append_vertex_does_not_mutate_previous_list(self):
        existing = [(10., 20.)]
        added = add_temporary_vertex(existing, [35., 55.])
        self.assertEqual(existing, [(10., 20.)])
        self.assertEqual(added, [(10., 20.), (35., 55.)])

    def test_invalid_temporary_vertex_is_rejected(self):
        with self.assertRaises(ValueError):
            add_temporary_vertex([(0, 0)], (float('inf'), 10))

    def test_valid_polygon_preserves_geometry_and_id_policy(self):
        points = [[0, 0], [100, 0], [100, 75], [0, 75]]
        original = copy.deepcopy(points)
        area = create_routing_area([{'id': 1, 'points': [(0, 0), (1, 0), (0, 1)]}], points)
        self.assertEqual(area['id'], 2)
        self.assertEqual(area['points'], [(0, 0), (100, 0), (100, 75), (0, 75)])
        self.assertEqual(original, points)

    def test_self_intersecting_polygon_is_not_created(self):
        self.assertIsNone(create_routing_area([], [(0, 0), (10, 10), (0, 10), (10, 0)]))

    def test_cable_path_next_id_and_metadata_unchanged(self):
        paths = [{'id': 2, 'points': [(1, 1), (2, 2)], 'owner': 'A'},
                 {'id': 9, 'points': [(3, 3), (5, 3)], 'owner': 'B'}]
        old = copy.deepcopy(paths)
        created = create_cable_path(paths, [[0, 0], [10, 30]])
        self.assertEqual(created, {'id': 10, 'points': [(0, 0), (10, 30)]})
        self.assertEqual(paths, old)

    def test_cable_path_minimum_two_vertices(self):
        self.assertIsNone(create_cable_path([], []))
        self.assertIsNone(create_cable_path([], [(5, 5)]))

    def test_reject_malformed_path_without_mutation(self):
        paths = [{'id': 5, 'points': [(1, 2), (3, 4)]}]
        self.assertIsNone(create_cable_path(paths, [(5, 6), (float('nan'), 7)]))
        self.assertEqual(len(paths), 1)


class GestureOwnershipRegressionTest(unittest.TestCase):
    def test_canvas_delegates_path_gestures(self):
        self.assertIn('_handle_path_canvas_press', PathsToolsMixin.__dict__)
        self.assertIn('_handle_path_canvas_right_press', PathsToolsMixin.__dict__)
        self.assertNotIn('_handle_path_canvas_press', CanvasGridMixin.__dict__)


if __name__ == '__main__':
    unittest.main()
