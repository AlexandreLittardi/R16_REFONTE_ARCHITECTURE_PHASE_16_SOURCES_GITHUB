# R16 - PV Engineering Desktop Application

This repository contains the **Python/Tkinter source code**, project documentation and regression tests. It does not contain an EXE, PyInstaller spec, build script, GitHub Actions packaging workflow, installer or generated build artefacts. Configure Windows EXE packaging separately in your own GitHub workflow.

## Run locally

Use Python 3.11 or newer with Tkinter enabled, then:

```sh
python -m pip install -r requirements.txt
python main.py
```

All project data is saved locally to JSON files; no server is required.

## Tests

```sh
python -m unittest discover -s tests -v
```

Phase 2-16 contracts are in `tests/test_phase2_boundaries.py`, `tests/test_phase3_wiring_and_gestures.py`, and `tests/test_phase4_diagram_commands.py`, and `tests/test_phase5_reconciliation_plan.py` and `tests/test_phase6_zone_grid_boundary.py` and `tests/test_phase7_gesture_hit_testing.py` and `tests/test_phase8_canvas_commands.py` and `tests/test_phase9_history_transactions.py` and `tests/test_phase10_command_transactions.py` and `tests/test_phase11_text_edit_boundaries.py` and `tests/test_phase12_mppt_edits.py`. The current method override inventory can be reproduced with `python tools/report_mro.py > docs/MRO_OWNERSHIP.csv`.

Phase 3-16 GUI checks: `tools/test_phase3_electrical_gui.py` and `tools/test_phase4_diagram_gui.py`, and `tools/test_phase5_paint_boundary_gui.py` and `tools/test_phase6_zone_paint_gui.py` and `tools/test_phase7_gesture_gui.py` and `tools/test_phase8_canvas_gui.py` and `tools/test_phase9_transactions_gui.py` and `tools/test_phase10_ribbon_dialog_gui.py` and `tools/test_phase11_text_questionnaire_gui.py` and `tools/test_phase12_equipment_gui.py`. GUI integration test scripts are provided in `tools/`; they require a desktop display. On Linux use `xvfb-run -a python tools/test_architecture_gui.py`. To verify a real schema-v2 project end-to-end use `xvfb-run -a python tools/test_project_roundtrip_gui.py /path/to/project.json`.

## Development and architecture

See `CODEMAP_DEFINITIVE.md` (phase 16 architecture), `AUDIT_ARCHITECTURE.md` (full audit), `REFONTE_ETAT.md` (completed vs. pending work), and `CONVENTIONS.md`. Keep `requirements.txt` and the `mixins/` package alongside `main.py` when creating your own EXE build.

The app contains 11 tabs, with monochrome mounting drawings, shared physical clamps, local JSON saves and A3 vector PDF exports.

**Engineering limitation:** mounting drawings are geometry plans; clamp and anchor mechanical capacities require manufacturer/structural validation.

No license accompanies this package. The project owner must select a license before redistribution.

Phase 13: spreadsheet and material-sheet edits now use explicit Undo/Redo
transactions; details in `docs/PHASE13_SPREADSHEET_TRANSACTIONS.md`.

Phase 14: photograph import/replacement, movement, calibration, reset and
installation dimensions have explicit Undo/Redo transactions. See
`docs/PHASE14_ROOF_HISTORY.md` and `tools/test_phase14_roof_history_gui.py`.

Phase 15 removes 14 proven-inaccessible MRO definitions (53 -> 41 collision names), protected by `tests/test_phase15_shadowed_cleanup.py`; see `docs/PHASE15_MRO_CLEANUP.md`. The legacy history poller is retained.

Phase 16: Shadow obstacle placement, offset and zone elevation, plus Cabling gathering points, have atomic Undo/Redo transactions. A redo-branch regression caused by normalized derived shadow state is corrected. See `docs/PHASE16_SITE_EDIT_TRANSACTIONS.md` and run `tools/test_phase16_site_edits_gui.py`. 232 unit tests pass; 41 MRO collision names remain. The fallback history watcher is retained.
