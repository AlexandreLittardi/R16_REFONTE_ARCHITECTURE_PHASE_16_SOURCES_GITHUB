# Phase 13 - Spreadsheet / Material Undo/Redo ownership

## Editing contracts

| User action | Owner | Domain write | Undo/Redo | Cancellation |
| --- | --- | --- | --- | --- |
| Cell edit / Delete | `SpreadsheetToolsMixin` | `write_cell` | 1 step if changed | Escape: none |
| Formula-bar Apply | `SpreadsheetToolsMixin` | `write_cell` | 1 step if changed | None if unchanged |
| Multi-cell paste | `SpreadsheetInteractionsMixin` | `paste_block` | 1 step | No clipboard: none |
| Fill-handle drop | `SpreadsheetInteractionsMixin` | `fill_range` | 1 step | No target: none |
| Column/row resize | `SpreadsheetToolsMixin` | dimension metadata | 1 step per drag | Zero motion: none |
| Row/column add/delete | `SpreadsheetToolsMixin` | `append_axis` / `remove_last_axis` | 1 step | Reject/confirm No: none |
| Clear sheet | `SpreadsheetToolsMixin` | clear raw cells | 1 step | Confirm No: none |
| CSV import | `SpreadsheetToolsMixin` | replace validated workbook | 1 step | Invalid/cancel: none |
| Material row add/delete | `MaterialToolsMixin` | existing equipment state | 1 step | Cancel: none |
| Material cell edit | `MaterialToolsMixin` | raw material field | 1 step if changed | No-op: none |

## Invariants

- JSON field and column names are unchanged, including French field names
  retained for compatibility with existing formulas and installation projects.
- A worksheet stores raw text, including `=` formula prefixes; this phase
  does not rewrite the evaluator or render output.
- Relative reference moves, numeric-series extension and clipping reuse
  original behaviour, now without importing Tkinter into the domain layer.
- Known equipment references must be repaired on row deletion via
  `equipment_state.delete_material_row`.
- Undo/Redo includes the workbook and equipment-sheet fields; viewport-only
  zoom does not create history. `_poll_history` remains a fallback for other UI.

## Validation

```bash
python -m unittest discover -s tests -q
xvfb-run -a python tools/test_phase13_spreadsheet_gui.py
xvfb-run -a python tools/test_phase12_equipment_gui.py
xvfb-run -a python tools/test_mounting_pdf_gui.py
xvfb-run -a python tools/test_project_roundtrip_gui.py /path/to/existing.json
```
