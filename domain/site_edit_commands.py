"""Tk-free immutable edits for obstacle registration and cabling gather points.

Coordinates remain in roof-image pixels and zone elevations in millimetres.
The functions do not silently normalise or discard unrelated project metadata.
"""
import math


def _finite(value, label):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f'{label} must be finite')
    return number


def image_point(x, y):
    return (_finite(x, 'X coordinate'), _finite(y, 'Y coordinate'))


def obstacle_from_reference(reference, dx_mm, dy_mm, px_per_mm):
    if reference is None:
        raise ValueError('A reference point is required')
    rx, ry = image_point(*reference)
    scale = _finite(px_per_mm, 'Scale')
    if scale <= 0:
        raise ValueError('Scale must be positive')
    return image_point(rx + _finite(dx_mm, 'Delta X') * scale,
                       ry + _finite(dy_mm, 'Delta Y') * scale)


def zone_with_height(zone, height_mm):
    updated = dict(zone)
    updated['z_mm'] = _finite(height_mm, 'Zone height')
    return updated


def zone_with_manual_gather(zone, point):
    updated = dict(zone)
    updated['gather_point'] = image_point(*point)
    updated['gather_point_manual'] = True
    return updated


def reset_zone_gather_points(zones):
    result = []
    for zone in zones:
        updated = dict(zone)
        updated['gather_point_manual'] = False
        updated.pop('gather_point', None)
        result.append(updated)
    return result
