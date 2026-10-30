"""Pure editor operation for routing-area polygons in original image px."""
from copy import deepcopy
from domain.geometry_validation import valid_polygon


def update_routing_area(areas, index, initial_points, dx, dy, vertex=None):
    """Return a new area list after an absolute drag from original points.

    Invalid polygons return None, not a partly mutated list. Coordinates are
    image pixels, not screen coordinates or millimetres. Remaining area records
    preserve all metadata (height, labels, IDs, ...).
    """
    if not 0 <= index < len(areas):
        raise IndexError('Routing-area index outside existing areas.')
    points = [tuple(point) for point in initial_points]
    if vertex is None:
        candidate = [(x + dx, y + dy) for x, y in points]
    else:
        if not 0 <= vertex < len(points):
            raise IndexError('Routing-area vertex outside existing polygon.')
        candidate = list(points)
        x, y = candidate[vertex]
        candidate[vertex] = (x + dx, y + dy)
    if not valid_polygon(candidate):
        return None
    changed = list(areas)
    item = deepcopy(areas[index])
    item['points'] = candidate
    changed[index] = item
    return changed
