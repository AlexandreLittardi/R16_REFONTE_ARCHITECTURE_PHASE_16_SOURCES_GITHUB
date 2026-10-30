"""Project-to-diagram projection without Tk widgets or application state.

The wiring graph is derived from electrical assignments, not from the drawing
camera. This adapter protects the input snapshot and retains custom devices,
positions and manually drawn links according to project_validation.sync_diagram.
"""
import copy
from project_validation import sync_diagram


def wiring_signature(strings, assignments, blocks):
    """Compatibility signature of the authoritative electrical topology.

    Preserve the legacy repr comparison while the string command model is
    being migrated: altering this signature mid-refactor would change when
    custom diagram placements get reconciled.
    """
    return repr((strings, assignments, blocks))


def diagram_projection(snapshot):
    """Return (nodes, links) without modifying the caller's project data."""
    isolated = dict(snapshot)
    isolated['diagram_nodes'] = copy.deepcopy(snapshot.get('diagram_nodes', {}))
    isolated['diagram_links'] = copy.deepcopy(snapshot.get('diagram_links', []))
    sync_diagram(isolated)
    return isolated['diagram_nodes'], isolated['diagram_links']
