"""Shared physical domains for JSON and interactive engineering inputs."""
import math


def validate_physical_inputs(values):
    limits = {'panel_tilt_deg': (0, 90), 'panel_azimuth_deg': (0, 360),
              'pylon_opacity': (0, 1), 'panel_noct_c': (1, 100),
              'solar_hour': (0, 24), 'solar_utc_offset': (-14, 14),
              'panel_efficiency_pct': (0, 100), 'solar_latitude': (-90, 90),
              'solar_longitude': (-180, 180)}
    for key, (low, high) in limits.items():
        if key in values:
            value = float(values[key])
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f'{key}: must be between {low} and {high}.')
    for key in ('panel_width_mm', 'panel_height_mm', 'pylon_height_mm',
                'pylon_width_mm', 'panel_pmax_w'):
        if key in values and (not math.isfinite(float(values[key])) or float(values[key]) <= 0):
            raise ValueError(f'{key}: must be positive and finite.')
