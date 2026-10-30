"""Pure, copy-on-write edits for string membership and ordering.

Coordinates and user-assigned string IDs remain opaque.  These operations do
not validate PV electrical limits: existing MPPT checks retain that responsibility.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StringEdit:
    strings: dict
    changed: bool
    owner: str | None = None


def add_panel(strings, string_id, coord):
    """Add once; expose its current owner when already present elsewhere."""
    for owner, members in strings.items():
        if coord in members:
            return StringEdit(strings, False, owner)
    result = {name: list(members) for name, members in strings.items()}
    result.setdefault(string_id, []).append(coord)
    return StringEdit(result, True)


def remove_panel(strings, coord):
    for owner, members in strings.items():
        if coord in members:
            result = {name: list(cells) for name, cells in strings.items()}
            result[owner].remove(coord)
            return StringEdit(result, True, owner)
    return StringEdit(strings, False)


def reorder_panel(strings, string_id, index, offset):
    members = strings.get(string_id, ())
    target = index + offset
    if not (0 <= index < len(members) and 0 <= target < len(members)):
        return StringEdit(strings, False)
    if target == index:
        return StringEdit(strings, False)
    result = {name: list(cells) for name, cells in strings.items()}
    result[string_id][index], result[string_id][target] = (
        result[string_id][target], result[string_id][index])
    return StringEdit(result, True)


def remove_at(strings, string_id, index):
    members = strings.get(string_id, ())
    if not 0 <= index < len(members):
        return StringEdit(strings, False)
    result = {name: list(cells) for name, cells in strings.items()}
    result[string_id].pop(index)
    return StringEdit(result, True)
