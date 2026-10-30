"""Tk-free contracts for obstacle and gather-point edit commands (phase 16)."""
import math
import unittest

from domain.site_edit_commands import (
    image_point, obstacle_from_reference, zone_with_height,
    zone_with_manual_gather, reset_zone_gather_points,
)


class SiteEditsTest(unittest.TestCase):
    def test_point_keeps_image_pixel_coordinates(self):
        self.assertEqual(image_point(5, '7.25'), (5., 7.25))

    def test_reference_offset_uses_pixels_per_millimetre(self):
        self.assertEqual(obstacle_from_reference((100, 200), 12.5, -8, 2),
                         (125., 184.))

    def test_invalid_scale_and_non_finite_values_rejected(self):
        for scale in (0, -1, float('nan'), float('inf')):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                obstacle_from_reference((0, 0), 1, 2, scale)
        with self.assertRaises(ValueError):
            obstacle_from_reference(None, 1, 2, 1)
        with self.assertRaises(ValueError):
            image_point(float('nan'), 2)
        with self.assertRaises(ValueError):
            obstacle_from_reference((0, 0), math.inf, 1, 2)

    def test_zone_height_does_not_mutate_metadata(self):
        zone = {'id': 1, 'z_mm': 0, 'installer_info': {'priority': 'A'}}
        edited = zone_with_height(zone, 500)
        self.assertEqual(edited['z_mm'], 500.)
        self.assertEqual(zone['z_mm'], 0)
        self.assertEqual(edited['installer_info'], {'priority': 'A'})
        self.assertIsNot(edited, zone)

    def test_height_nan_does_not_change_zone(self):
        zone = {'id': 1, 'z_mm': 123}
        with self.assertRaises(ValueError):
            zone_with_height(zone, float('nan'))
        self.assertEqual(zone['z_mm'], 123)

    def test_manual_gather_preserves_zone_and_source(self):
        zone = {'id': 2, 'gather_point': (1, 2), 'label': 'Roof 2'}
        edited = zone_with_manual_gather(zone, (30, 40))
        self.assertEqual(edited['gather_point'], (30., 40.))
        self.assertTrue(edited['gather_point_manual'])
        self.assertEqual(edited['label'], 'Roof 2')
        self.assertEqual(zone['gather_point'], (1, 2))

    def test_reset_all_gather_points_is_copy_on_write(self):
        zones = [
            {'id': 1, 'gather_point_manual': True, 'gather_point': (12, 30), 'x1': 40},
            {'id': 2, 'gather_point_manual': False, 'metadata': {'x': 2}},
        ]
        reset = reset_zone_gather_points(zones)
        self.assertEqual(len(reset), 2)
        self.assertTrue(zones[0]['gather_point_manual'])
        self.assertEqual(zones[0]['gather_point'], (12, 30))
        self.assertNotIn('gather_point', reset[0])
        self.assertFalse(reset[0]['gather_point_manual'])
        self.assertEqual(reset[0]['x1'], 40)
        self.assertEqual(reset[1]['metadata'], {'x': 2})
        self.assertIsNot(reset[0], zones[0])


if __name__ == '__main__':
    unittest.main()
