"""Read-only hit tests for Installation canvas gestures.

Coordinates are in *canvas* pixels after Tk scroll offsets, with ``zoom``
matching the projection used by the existing roof renderer. These utilities
never modify the roof model and can be tested without a Tk window.
"""


def zone_at_point(zones, x, y, zoom):
    """First matching roof zone, preserving the legacy list-first hit order."""
    for index, zone in enumerate(zones):
        x1, x2 = sorted((zone["x1"] * zoom, zone["x2"] * zoom))
        y1, y2 = sorted((zone["y1"] * zoom, zone["y2"] * zoom))
        if x1 <= x <= x2 and y1 <= y <= y2:
            return index
    return None


def zone_resize_handle(zone, x, y, zoom, tolerance=8):
    """Name of the matching corner, or None. Corners take legacy priority."""
    x1, x2 = sorted((zone["x1"] * zoom, zone["x2"] * zoom))
    y1, y2 = sorted((zone["y1"] * zoom, zone["y2"] * zoom))
    corners = (
        ("resize_tl", x1, y1),
        ("resize_tr", x2, y1),
        ("resize_bl", x1, y2),
        ("resize_br", x2, y2),
    )
    for name, hx, hy in corners:
        if abs(x - hx) <= tolerance and abs(y - hy) <= tolerance:
            return name
    return None


def dimension_label_at(measures, x, y, zoom, x_tolerance=58, y_tolerance=15):
    """Last visible dimension label at a canvas point, for drag selection."""
    for index in range(len(measures) - 1, -1, -1):
        measure = measures[index]
        if not isinstance(measure, dict):
            continue
        lx, ly = measure["label"]
        if abs(x - lx * zoom) < x_tolerance and abs(y - ly * zoom) < y_tolerance:
            return index
    return None
