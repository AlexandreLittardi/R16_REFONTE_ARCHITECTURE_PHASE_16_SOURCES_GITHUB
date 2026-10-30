"""Stable, read-only signature of the inputs and outputs of zone grid allocation.

A canvas redraw must never allocate row ranges or silently rewrite zone data.
The signature lives in the domain layer and has no Tkinter dependencies.
"""


def zone_grid_signature(zones, settings, scale, panel_width, panel_height):
    """Describe the data relevant to the zone registry without mutating it.

    Include derived fields so imported or manually edited records without a
    valid projection cannot be mistaken for an already committed grid.  Do not
    include non-geometric metadata such as installer notes or roof elevation.
    """
    settings = settings or {}
    gap_w = settings.get('module_gap_width_mm', settings.get('module_gap_x_mm', 0))
    gap_l = settings.get('module_gap_length_mm', settings.get('module_gap_y_mm', 0))
    clearance = settings.get('edge_clearance_mm', 0)
    inputs = (scale, panel_width, panel_height, gap_w, gap_l, clearance)
    zone_keys = (
        'x1', 'y1', 'x2', 'y2', 'angle_deg', 'align_x', 'align_y',
        'row_base', 'row_capacity', 'rows', 'cols', 'offset_x_mm',
        'offset_y_mm', 'gap_width_mm', 'gap_length_mm', 'gap_x_mm',
        'gap_y_mm', 'edge_clearance_mm', 'uid',
    )
    return (inputs, tuple(tuple(zone.get(key) for key in zone_keys) for zone in zones))
