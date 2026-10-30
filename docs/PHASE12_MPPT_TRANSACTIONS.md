# Phase 12: Equipment tree and MPPT edit boundaries

## Purpose

Migrate the remaining interactive Equipment MPPT operations away from the
600-ms fallback history watcher. Do not change saved `string_mppt_assignment`
shape, string geometry, the electrical diagram projection, tab order, or the
inverter auto-distribution algorithm.

## Implemented changes

- `domain/mppt_edits.py`: `propose_mppt_assignment` validates that the string
  exists and contains panels, the block and MPPT exist, all strings on the
  target MPPT have compatible panel counts, and the target is not full. It
  returns a new dictionary without mutating caller state. It also exposes
  `interpret_equipment_drop` to distinguish click-only, target-block warning,
  sibling-string, unassigned, and MPPT drop actions without importing Tkinter.
- `mixins/equipment_tools.py`: `_assign_string_to_mppt` applies the proposal only
  after successful validation; existing user-facing warnings and the
  `_notify_wiring_change` event still run for actual changes. The Treeview
  release handler runs assign/unassign within one `_run_project_edit` boundary;
  invalid, repeated or informational drops create no history entry.
- `mixins/ui_builders.py`: the two *MPPT actions* menu callbacks now use a
  transaction around the existing auto-distribution and confirmation-driven
  clear operations. A cancelled clear remains a no-op.

## Validation

`python -m unittest discover -s tests -q` (203 passing tests) covers the
pure MPPT assignment proposal and drop intent rules. In a headless Linux
session use `xvfb-run -a python tools/test_phase12_equipment_gui.py`, which
checks Treeview drops and actual menu callbacks, Undo/Redo, repeated and
rejected drops, and cancelled clear. The GUI test supplies a fixed geometry
fixture and its matching `layout_geometry` signature, to avoid unrelated
zone-allocation changes while testing Equipment history.

Additional regression checks run: phases 7/9/10/11 GUI tests, live electrical
diagram edit/Undo, native A3 PDF export, the full 500-panel Mounting scenario,
and the Frimo v2 JSON read/write/readback (533 panels, 9 zones, 2 routing
areas, 32 strings). Project data is not packaged in the sources archive.

## Boundaries not yet migrated

`_poll_history` remains the compatibility fallback for other legacy UI edits.
It must not be removed yet. The original inverter auto-distribution algorithm
and its user dialogs remain unchanged, although now captured as a single
transaction. Other mixins still have 53 multiply defined method names; this
phase does not delete them. A complete Windows runtime and EXE build remains
outside these Linux GUI tests and is maintained by the project owner.
