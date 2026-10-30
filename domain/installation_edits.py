"""Pure Installation Area geometry, independent of Tkinter and rendering.

Mouse interactions work in *unscaled image pixels*.  These helpers compute
proposed changes from the original gesture snapshot, never from the previous
mouse move.  Callers commit returned fields to the project at an edit boundary.
"""

from math import isfinite


ZONE_RECT_FIELDS = ("x1", "y1", "x2", "y2")
_RESIZE_HANDLES = frozenset(("resize_tl", "resize_tr", "resize_bl", "resize_br"))


def _finite(*values):
    if not all(isinstance(value, (int, float)) and isfinite(value) for value in values):
        raise ValueError("Coordinates and dimensions must be finite numbers")


def translate_zones(original_rects, dx, dy):
    """Return {index: geometry} for a multi-zone drag, preserving other keys.

    ``original_rects`` is the gesture-start snapshot, not mutable project data.
    """
    _finite(dx, dy)
    result = {}
    for index, bounds in original_rects.items():
        if len(bounds) != 4:
            raise ValueError("Zone rectangle must have four coordinates")
        x1, y1, x2, y2 = bounds
        _finite(x1, y1, x2, y2)
        result[index] = dict(zip(ZONE_RECT_FIELDS, (x1 + dx, y1 + dy, x2 + dx, y2 + dy)))
    return result


def resize_zone(original_rect, handle, dx, dy, *, zoom, px_per_mm):
    """Return geometry and physical dimensions for an absolute corner drag.

    This mirrors the pre-refactor 15-screen-pixel minimum and the existing
    ``w_mm``/``h_mm`` behavior for scaled and unscaled projects.
    """
    if handle not in _RESIZE_HANDLES:
        raise ValueError("Unknown resize handle")
    if len(original_rect) != 4:
        raise ValueError("Zone rectangle must have four coordinates")
    x1, y1, x2, y2 = original_rect
    _finite(x1, y1, x2, y2, dx, dy, zoom, px_per_mm)
    if zoom <= 0:
        raise ValueError("Zoom must be positive")
    min_dim = 15 / zoom
    if handle == "resize_tl":
        nx1, ny1 = min(x1 + dx, x2 - min_dim), min(y1 + dy, y2 - min_dim)
        nx2, ny2 = x2, y2
    elif handle == "resize_tr":
        nx1, ny1 = x1, min(y1 + dy, y2 - min_dim)
        nx2, ny2 = max(x2 + dx, x1 + min_dim), y2
    elif handle == "resize_bl":
        nx1, ny1 = min(x1 + dx, x2 - min_dim), y1
        nx2, ny2 = x2, max(y2 + dy, y1 + min_dim)
    else:
        nx1, ny1 = x1, y1
        nx2, ny2 = max(x2 + dx, x1 + min_dim), max(y2 + dy, y1 + min_dim)
    changes = dict(zip(ZONE_RECT_FIELDS, (nx1, ny1, nx2, ny2)))
    if px_per_mm > 0:
        changes["w_mm"] = abs(nx2 - nx1) / px_per_mm
        changes["h_mm"] = abs(ny2 - ny1) / px_per_mm
    return changes


def new_zone(start, end, *, zone_id, px_per_mm, align_x, align_y):
    """Construct a new roof zone using the saved project schema."""
    x0, y0 = start
    x1, y1 = end
    _finite(x0, y0, x1, y1, px_per_mm)
    w, h = abs(x1 - x0), abs(y1 - y0)
    return {
        "id": zone_id,
        "x1": min(x0, x1), "y1": min(y0, y1),
        "x2": max(x0, x1), "y2": max(y0, y1),
        "w_mm": w / px_per_mm if px_per_mm > 0 else w,
        "h_mm": h / px_per_mm if px_per_mm > 0 else h,
        "align_x": {"Left": "Gau.", "Center": "Centre", "Right": "Dro."}[align_x],
        "align_y": {"Top": "Haut", "Center": "Centre", "Bottom": "Bas"}[align_y],
    }
