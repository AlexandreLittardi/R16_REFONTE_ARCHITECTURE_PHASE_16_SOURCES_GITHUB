"""Stable panel identity reconciliation without Tkinter dependencies."""
from uuid import uuid4


def reconcile_panel_uids(existing, panels, *, id_factory=None):
    """Preserve IDs by coordinate; generate only for newly appearing panels."""
    if id_factory is None:
        id_factory = lambda: uuid4().hex
    return {coord: existing[coord] if coord in existing else id_factory() for coord in panels}
