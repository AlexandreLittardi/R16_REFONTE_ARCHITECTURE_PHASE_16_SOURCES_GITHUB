"""Pure copy-on-write commands for manual single-line diagram editing.

No Tkinter, project-file IO, camera state, or automatic electrical projection.
Only caller-supplied diagram nodes and links are changed.  Auto-generated
nodes remain editable for positioning; deleting them remains the legacy UI's
responsibility (they can be recreated by the topology projection).
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class DiagramEdit:
    nodes: dict
    links: list
    changed: bool


def _unchanged(nodes, links):
    return DiagramEdit(nodes, links, False)


def add_custom_node(nodes, links, node_id, label, *, selected=None,
                    style='solid', distance_m=0.0, x=420, y=40):
    """Create a custom node and, optionally, a link to the selected node."""
    if not isinstance(node_id, str) or not node_id.startswith('custom::') or node_id in nodes:
        return _unchanged(nodes, links)
    if not isinstance(label, str) or not label.strip():
        return _unchanged(nodes, links)
    if not all(isinstance(value, (float, int)) and isfinite(value)
               for value in (x, y, distance_m)) or distance_m < 0:
        return _unchanged(nodes, links)
    updated_nodes = deepcopy(nodes)
    updated_links = deepcopy(links)
    updated_nodes[node_id] = {'type': 'custom', 'label': label.strip(), 'x': x, 'y': y}
    if selected in nodes:
        updated_links.append({'a': selected, 'b': node_id, 'auto': False,
                              'style': style, 'distance_m': distance_m})
    return DiagramEdit(updated_nodes, updated_links, True)


def add_manual_link(nodes, links, start, end, *, style='solid', distance_m=0.0):
    """Append a deliberate manual link without touching automatic topology."""
    if (start == end or start not in nodes or end not in nodes
            or not isinstance(distance_m, (int, float))
            or not isfinite(distance_m) or distance_m < 0):
        return _unchanged(nodes, links)
    updated_links = deepcopy(links)
    updated_links.append({'a': start, 'b': end, 'auto': False,
                          'style': style, 'distance_m': distance_m})
    return DiagramEdit(nodes, updated_links, True)


def delete_nodes(nodes, links, selected):
    """Delete exactly selected IDs and their incident links; preserve everything else."""
    actual = set(selected or ()) & nodes.keys()
    if not actual:
        return _unchanged(nodes, links)
    updated_nodes = {key: deepcopy(node) for key, node in nodes.items() if key not in actual}
    updated_links = [deepcopy(link) for link in links
                     if link.get('a') not in actual and link.get('b') not in actual]
    return DiagramEdit(updated_nodes, updated_links, True)


def move_nodes(nodes, links, start_positions, dx, dy):
    """Absolute-delta drag from original model positions (no cumulative drift)."""
    if not start_positions or not all(isinstance(v, (int, float)) and isfinite(v)
                                       for v in (dx, dy)):
        return _unchanged(nodes, links)
    valid = {key: pos for key, pos in start_positions.items() if key in nodes}
    if not valid:
        return _unchanged(nodes, links)
    updated_nodes = None
    for key, (x, y) in valid.items():
        nx, ny = x + dx, y + dy
        if not all(isfinite(v) for v in (nx, ny)):
            return _unchanged(nodes, links)
        if nodes[key].get('x') != nx or nodes[key].get('y') != ny:
            if updated_nodes is None:
                updated_nodes = dict(nodes)
            updated_nodes[key] = dict(nodes[key])
            updated_nodes[key]['x'], updated_nodes[key]['y'] = nx, ny
    if updated_nodes is None:
        return _unchanged(nodes, links)
    return DiagramEdit(updated_nodes, links, True)


def position_nodes(nodes, links, positions):
    """Apply a computed layout atomically without changing link metadata."""
    if not positions:
        return _unchanged(nodes, links)
    updated_nodes = None
    for key, (x, y) in positions.items():
        if key not in nodes:
            continue
        if not all(isinstance(v, (int, float)) and isfinite(v) for v in (x, y)):
            return _unchanged(nodes, links)
        if nodes[key].get('x') != x or nodes[key].get('y') != y:
            if updated_nodes is None:
                updated_nodes = dict(nodes)
            updated_nodes[key] = dict(nodes[key])
            updated_nodes[key]['x'], updated_nodes[key]['y'] = x, y
    return DiagramEdit(updated_nodes, links, True) if updated_nodes is not None else _unchanged(nodes, links)
