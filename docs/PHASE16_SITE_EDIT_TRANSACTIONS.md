# Phase 16 - Shadow/Cabling site edits and restored-history correctness

**Source baseline:** phase 15. **Scope:** replace implicit undo capture for discrete shadow-obstacle and cable gathering point edits; preserve all legacy JSON keys, solar/shadow calculations, geometry and canvas gestures. Do **not** disable legacy history polling or alter the EXE build process.

## Changes

1. `domain/site_edit_commands.py` implements Tk-independent, side-effect-free edit primitives: image coordinates, an obstacle position relative to a reference point in **image pixels**, zone elevation in **mm**, manual cable gathering points and reset-to-automatic. Unknown roof-zone fields are preserved; invalid/non-finite inputs are rejected before mutation.
2. `ShadowToolsMixin`: clearing an obstacle, positioning by ΔX/ΔY, changing a zone height, and placing an obstacle or its reference on the canvas now each open **one explicit `_run_project_edit`**. Position-click routing is retained in `CanvasGridMixin`, which delegates to the Shadow UI owner. The existing recomputation and display refresh run inside the edit transaction.
3. `CableNetworkMixin`: manual gathering-point placement on the nearest zone and resetting all gathering points also become atomic edits, preserving the existing nearest-zone selection and cable route invalidation.
4. `SafeProjectMixin`: after Undo/Redo, restoring a document can legitimately normalise derived/cache fields (notably a shadow preview). `_history_restored_state_signature` records the **actual** restored state. A later history poll or Redo no longer mistakes this harmless normalisation for a fresh edit and truncates the redo branch. A genuine edit changes the signature and correctly opens a new history branch.

## Contract

- Image points in pixels, physical offset in mm multiplied by `px_per_mm`; zone heights stored as mm.
- No Tkinter imports or project-schema changes in `domain/site_edit_commands.py`.
- Canceled, unchanged or invalid operations create no history entry; successful edits create one.
- Undo/Redo restores the saved project state, including obstacle locations and zone metadata. Existing JSON type normalisation (tuples become lists upon reload) is unchanged.
- The 600 ms automatic history poller remains as compatibility coverage for **unmigrated** actions; disabling it is **not** justified in this phase.
- 41 MRO method-name collisions remain; no potentially reachable override was removed.

## Verification

- `python -m unittest discover -s tests -q`: **232 passing tests** (225 baseline).
- `xvfb-run -a python tools/test_phase16_site_edits_gui.py`: shadow image-click placement, obstacle reference and relative offset, zone-height edit, obstacle clear, invalid value, cable gathering point placement/reset, Undo/Redo restoration, branch replacement after Undo, and JSON persistence.
- `tools/test_architecture_gui.py`, `tools/test_phase9_transactions_gui.py`, `tools/test_phase12_equipment_gui.py`, `tools/test_mounting_pdf_gui.py`: pass.
- `tools/test_project_roundtrip_gui.py` against the user's **external** Frimo JSON: **533 panels, 9 roof zones, 2 routing areas, 32 strings** preserved.
- `tools/test_mounting_gui.py`: **500-panel** regression and vector mounting-report export pass.

## Next steps

1. Audit Shadow slider/entry recomputation and equipment/energy parameter dialogs for a single explicit commit boundary, without recording every mouse motion or keystroke.
2. Continue testing old edit paths that still require `_poll_history`, before considering a universal command bus or disabling fallback polling.
3. Consolidate the 41 remaining cooperative mixin chains only after verifying their `super()` ordering and GUI dispatch contracts.
