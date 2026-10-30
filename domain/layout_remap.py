"""Pure remapping of grid row addresses after a layout zone changes capacity.

Panel numbers, stable UIDs, string order and placement metadata are preserved.
Addresses are in (global_row, local_column), *not* physical millimetres.
The legacy collision/update order is retained for compatibility.
"""


def remap_address(coord, old_base, capacity, new_base):
    """Translate an address inside the old row range; leave others unchanged."""
    row, col = coord
    if old_base <= row < old_base + capacity:
        return (new_base + row - old_base, col)
    return coord


def remap_zone_state(old_base, capacity, new_base, *, panels=None,
                     panel_blocks=None, panel_orientations=None, panel_uids=None,
                     layout_geometry=None, strings=None, selected_panel_coords=None):
    """Create fresh affected containers without mutating any original mappings.

    Arguments left as None remain absent from the returned result. This
    matches the old adapter's ``hasattr`` behaviour during app initialization.
    """
    result = {}
    address = lambda coord: remap_address(coord, old_base, capacity, new_base)
    for field, records in (
        ('panels', panels), ('panel_blocks', panel_blocks),
        ('panel_orientations', panel_orientations), ('panel_uids', panel_uids)
    ):
        if records is not None:
            result[field] = {address(coord): value for coord, value in records.items()}
    if layout_geometry is not None:
        transformed = {}
        for key, value in layout_geometry.items():
            row, col = address(tuple(map(int, key.split(','))))
            transformed[f'{row},{col}'] = value
        result['layout_geometry'] = transformed
    if strings is not None:
        result['strings'] = {
            string_id: [address(coord) for coord in coords]
            for string_id, coords in strings.items()
        }
    if selected_panel_coords is not None:
        result['selected_panel_coords'] = {address(coord) for coord in selected_panel_coords}
    return result
