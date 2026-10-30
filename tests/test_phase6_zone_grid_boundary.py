"""Phase 6: stable domain grid signature and explicit edit/paint boundary."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from domain.zone_grid_state import zone_grid_signature
from mixins.installation_geometry import InstallationGeometryMixin
from mixins.shadow_geometry import ShadowGeometryMixin


def zone(**overrides):
    data = dict(id=1, x1=20.0, y1=30.0, x2=5000.0, y2=5500.0,
                align_x='Centre', align_y='Centre', angle_deg=0)
    data.update(overrides)
    return data


class ZoneAdapter(InstallationGeometryMixin):
    def __init__(self):
        self.px_per_mm = 1.0
        self.panel_width_mm = 1000.0
        self.panel_height_mm = 1700.0
        self.model_settings = {'module_gap_width_mm': 20.0,
                               'module_gap_length_mm': 30.0,
                               'edge_clearance_mm': 0.0}
        self.roof_zones = [zone()]
        self.remaps = []

    def _remap_zone_rows(self, start, capacity, dest):
        self.remaps.append((start, capacity, dest))


class Phase6ZoneTests(unittest.TestCase):
    def test_signature_pure(self):
        zones = [zone()]
        before = copy.deepcopy(zones)
        signature = zone_grid_signature(zones, {}, 1.0, 1000.0, 1700.0)
        self.assertEqual(before, zones)
        self.assertEqual(signature,
                         zone_grid_signature(zones, {}, 1.0, 1000.0, 1700.0))

    def test_signature_ignores_non_geometry_metadata(self):
        zones = [zone()]
        first = zone_grid_signature(zones, {}, 1.0, 1000.0, 1700.0)
        zones[0]['installation_height_m'] = 12.0
        zones[0]['notes'] = 'unrelated metadata'
        self.assertEqual(first, zone_grid_signature(zones, {}, 1.0, 1000.0, 1700.0))

    def test_legacy_gap_aliases_remain_supported(self):
        zones = [zone()]
        a = zone_grid_signature(zones, {'module_gap_width_mm': 20}, 1, 1000, 1700)
        b = zone_grid_signature(zones, {'module_gap_x_mm': 20}, 1, 1000, 1700)
        self.assertEqual(a, b)

    def test_grid_calculation_idempotent(self):
        app = ZoneAdapter()
        self.assertTrue(app._recalculate_zone_grids())
        before = copy.deepcopy(app.roof_zones)
        self.assertEqual(app.roof_zones[0]['cols'], 4)
        self.assertEqual(app.roof_zones[0]['rows'], 3)
        with patch('zone_registry.allocate_ranges', side_effect=AssertionError('duplicated range allocation')):
            for _ in range(200):
                self.assertFalse(app._recalculate_zone_grids())
        self.assertEqual(app.roof_zones, before)

    def test_recompute_on_geometry_and_gap_changes(self):
        app = ZoneAdapter()
        app._recalculate_zone_grids()
        before = app.roof_zones[0]['cols']
        app.roof_zones[0]['x2'] = 3600.0
        self.assertTrue(app._recalculate_zone_grids())
        self.assertLess(app.roof_zones[0]['cols'], before)
        app.model_settings['module_gap_width_mm'] = 100.0
        self.assertTrue(app._recalculate_zone_grids())
        self.assertEqual(app.roof_zones[0]['gap_width_mm'], 100.0)

    def test_recompute_when_derived_value_modified(self):
        app = ZoneAdapter()
        app._recalculate_zone_grids()
        app.roof_zones[0]['rows'] = -5
        self.assertTrue(app._recalculate_zone_grids())
        self.assertEqual(app.roof_zones[0]['rows'], 3)

    def test_replacement_of_zone_is_detected(self):
        app = ZoneAdapter()
        app._recalculate_zone_grids()
        app.roof_zones = [zone()]
        self.assertTrue(app._recalculate_zone_grids())
        self.assertIn('row_base', app.roof_zones[0])

    def test_uncalibrated_layout_not_mutated(self):
        app = ZoneAdapter()
        app.px_per_mm = 0.0
        before = copy.deepcopy(app.roof_zones)
        self.assertFalse(app._recalculate_zone_grids())
        self.assertEqual(app.roof_zones, before)

    def test_panel_geometry_query_does_not_allocate_ranges(self):
        class GeometryProbe(ShadowGeometryMixin):
            def _recalculate_zone_grids(self):
                raise AssertionError('geometry query mutated layout')
        app = GeometryProbe()
        app.px_per_mm = 1.0
        app.panel_width_mm = 1000.0
        app.panel_height_mm = 1700.0
        app.roof_zones = [dict(zone(), rows=1, cols=2, row_base=0,
                               offset_x_mm=0, offset_y_mm=0,
                               gap_x_mm=20, gap_y_mm=30)]
        app.cell_size_px = 10
        app._zone_rotate_rect = lambda z, x1, y1, x2, y2: [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        before = copy.deepcopy(app.roof_zones)
        polygon = app._panel_rect((0, 0))
        self.assertEqual(len(polygon), 4)
        self.assertEqual(app.roof_zones, before)


if __name__ == '__main__':
    unittest.main()
