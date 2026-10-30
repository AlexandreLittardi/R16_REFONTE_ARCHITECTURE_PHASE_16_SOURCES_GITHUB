"""Pure cable drawing commands, independent of Tkinter and project widgets."""

from math import isfinite
from domain.geometry_validation import valid_polygon


def add_temporary_vertex(points, point):
    """Return a new list including the clicked point; never mutate the input."""
    x, y = point
    if not all(isinstance(v, (int, float)) and isfinite(v) for v in (x, y)):
        raise ValueError("Cable drawing point must contain finite coordinates")
    return [*points, (x, y)]


def create_routing_area(areas, points):
    """Build an area in the existing local JSON schema or return None."""
    if not valid_polygon(points):
        return None
    # Preserve the legacy ID policy; saved projects may refer to these IDs.
    return {"id": len(areas) + 1, "points": [tuple(p) for p in points]}


def create_cable_path(paths, points):
    """Build an open polyline preserving the existing ID allocation behavior."""
    if len(points) < 2:
        return None
    if any(len(p) != 2 or not all(isinstance(v, (int, float)) and isfinite(v) for v in p)
           for p in points):
        return None
    return {"id": max((int(path.get("id", 0)) for path in paths), default=0) + 1,
            "points": [tuple(p) for p in points]}
