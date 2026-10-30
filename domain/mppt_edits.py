"""Pure MPPT assignment checks and equipment-tree drop interpretation.

The GUI owns warning dialogs and Undo/Redo transaction boundaries. This module
neither mutates its inputs nor imports Tkinter; a rejected edit is a no-op.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MpptProposal:
    assignments: dict
    error: Optional[str] = None
    existing_panel_count: Optional[int] = None


def propose_mppt_assignment(assignments, strings, blocks, string_id, block_name, mppt_idx):
    """Return a proposed copy of assignments or an error, with no side effects."""
    previous = dict(assignments)
    coords = strings.get(string_id) or []
    if not coords:
        return MpptProposal(previous, 'empty_string')
    block = blocks.get(block_name)
    if not block:
        return MpptProposal(previous, 'missing_block')
    count = block.get('mppt_count', 2)
    if type(mppt_idx) is not int or not 1 <= mppt_idx <= count:
        return MpptProposal(previous, 'invalid_mppt')
    existing = [sid for sid, assn in previous.items()
                if sid != string_id and assn.get('block') == block_name
                and assn.get('mppt') == mppt_idx]
    if existing:
        panel_count = len(strings.get(existing[0], []))
        if panel_count != len(coords):
            return MpptProposal(previous, 'different_panel_counts', panel_count)
        if len(existing) >= max(1, block.get('max_strings_per_mppt', 1)):
            return MpptProposal(previous, 'mppt_full')
    previous[string_id] = {'block': block_name, 'mppt': mppt_idx}
    return MpptProposal(previous)


@dataclass(frozen=True)
class EquipmentDrop:
    action: str
    string_id: str
    block_name: Optional[str] = None
    mppt_idx: Optional[int] = None


def interpret_equipment_drop(dragged_item, target, target_parent=None):
    """Convert tree item IDs to an edit intent; ignore clicks and invalid IDs."""
    if not dragged_item or not dragged_item.startswith('string::'):
        return None
    sid = dragged_item[len('string::'):]
    if not sid or not target or target == dragged_item:
        return None
    if target.startswith('string::'):
        target = target_parent
    if target == 'unassigned':
        return EquipmentDrop('unassign', sid)
    if target and target.startswith('mppt::'):
        rest = target[len('mppt::'):]
        if '::' not in rest:
            return None
        block, index = rest.rsplit('::', 1)
        if not block or not index.isdecimal() or int(index) < 1:
            return None
        return EquipmentDrop('assign', sid, block, int(index))
    if target and target.startswith('block::'):
        return EquipmentDrop('choose_mppt', sid)
    return None
