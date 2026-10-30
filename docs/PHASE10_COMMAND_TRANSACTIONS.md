# Phase 10 - Toolbar and dialog transactions

## Goal

A user's **one Apply / one ribbon command = one undoable operation**, with
no intermediate snapshots caused by GUI callbacks, electrical notifications
or the background 600-ms history check. Editing logic and JSON schema are
left unchanged.

## Implemented command boundaries

| Source | Owner | Command |
|---|---|---|
| Layout ribbon | `layout:generate` | Generate layout from zones |
| Layout ribbon | `layout:new-block` | New block (dialog) |
| Layout ribbon | `layout:delete-block` | Delete active block |
| Layout ribbon | `layout:remove-inverter` | Remove inverter placement |
| Layout panel configuration | `layout:panel-settings` | Width, height, tilt, azimuth in a single Apply |
| Stringing side panel | `stringing:move-up`, `stringing:move-down` | Reorder selected panel |
| Stringing side panel | `stringing:add-manual`, `stringing:remove-manual` | Add/remove panel |
| Stringing tree drag | `stringing:tree-reorder` | Drop a panel into a new position |
| Installation zone settings | `installation:zone-settings` | Apply zone dimensions and rotation |
| Installation zone menu | `installation:delete-zones` | Delete one or more zones |
| Installation routing heights | `installation:routing-heights` | Apply heights and bridge settings |
| Equipment capacity editor | `equipment:capacity` | Apply MPPT capacity |
| Project grid connection | `project:grid-connection` | Apply contract/export limits |

All operations reuse the tested `SafeProjectMixin` edit gate. A nested edit
will not close the outer transaction. The owner is a stable diagnostic label,
not a serialized field. The callback runs synchronously, preserves its return
value, and `finally` ends an owned transaction even if callback fails.

## Deliberate non-changes

- The engineering questionnaire has its own validated rollback and import
  mechanism and is **not** yet migrated. It still uses explicit before/after
  `_record_history()` calls.
- Mounting and Diagram have separate undo/redo command systems and are not
  modified by this phase.
- Non-migrated UI actions retain the legacy automatic-history fallback.
  **Do not remove `_poll_history`** until these remaining paths are covered.
- No user project or roof image is bundled and no build/EXE settings added.

## Regression commands

```sh
python -m unittest discover -s tests -q
xvfb-run -a python tools/test_phase10_ribbon_dialog_gui.py
xvfb-run -a python tools/test_phase9_transactions_gui.py
xvfb-run -a python tools/test_mounting_gui.py
xvfb-run -a python tools/test_project_roundtrip_gui.py /path/to/project.json
```

Windows GUI parity still requires execution on the target host; this Linux
Xvfb validation cannot guarantee every platform-specific behavior.
