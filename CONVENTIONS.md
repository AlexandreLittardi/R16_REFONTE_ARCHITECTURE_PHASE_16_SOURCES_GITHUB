# R16 development conventions

- The product is a **local desktop Python/Tkinter** application. Keep the 11 English UI tabs and preserve schema-v2 JSON backward compatibility.
- Read `CODEMAP_DEFINITIVE.md` and `AUDIT_ARCHITECTURE.md` before modifying legacy mixins. Record all changes in `REFONTE_ETAT.md`.
- Keep numeric and geometry engines under `domain/` and avoid importing Tkinter from that directory. Keep project writes in `infrastructure/`.
- Use `TabId` instead of hard-coded indexes for any newly migrated UI callback. Do not reorder the notebook.
- Add a domain command + regression tests before moving an editing operation out of a mixin. Preserve all unknown/legacy fields in save and load cycles.
- The 41 remaining MRO method-name collisions are **not** disposable until their super() and explicit call paths are understood.
- Wheel zoom at cursor, middle-drag pan, and left-button manipulation must remain identical in all drawing tabs. Camera-only changes must not create new undo history entries.
- Keep clamp A/B/C geometry, intermediate clamp sharing, editing labels without geometry changes and monochrome A3 vector exports unchanged.
- Validate with `python -m unittest discover -s tests -q`, the GUI scripts under `tools/` and a project JSON read/write/reload roundtrip.
- Do not commit user projects, cached bytecode, `.exe`, PyInstaller specs, binaries or build artifacts. The GitHub EXE build belongs to the project owner.

## Zone-grid calculation boundary (phase 6)

- Do not call `_recalculate_zone_grids()` from `draw_grid()`, `_panel_rect()`
  or other painting/geometry-query functions.
- Prepare the grid in zone-edit commands, hit-testing, tab entry, explicit
  history commits, and JSON save/load. Passive background history checks
  must not reassign zone row ranges.
- Keep `domain.zone_grid_state.zone_grid_signature` free of Tkinter and
  resilient to legacy spacing aliases; preserve `zone_registry` row ranges
  and `domain.layout_remap` when editing a zone.
- Run unit tests, `tools/test_phase6_zone_paint_gui.py`, the long camera
  navigation test, Mounting regression, and a real JSON roundtrip before
  changing the grid signature or its commit points.

## Canvas editing boundary (phase 7)

- Every left gesture must have **one owner**: Mounting, DiagramEditor,
  EditorInteractions (routing polygons), or the remaining CanvasGrid editor.
- No direct mutation of diagram block coordinates in CanvasGrid: use the
  copy-on-write commands and history transaction in DiagramEditor.
- The Installation hit-test functions in `ui/gesture_hit_testing.py` must not
  allocate zones, mutate the project or import Tkinter. All thresholds are
  in screen pixels, not roof millimetres.
- Preserve list-first hit priority for overlapping zones and last-first
  priority for dimension labels.
- Run the phase 7 GUI test and both camera navigation tests after changing
  the mouse dispatch order; validate Frimo JSON roundtrip before release.

## Installation and Cabling commands (phase 8)

- Keep zone translation, resize and construction in
  `domain.installation_edits`. Call with image-pixel coordinates and absolute
  gesture-start snapshots; apply only returned geometry fields.
- Polygon and cable path constructors belong to `domain.cabling_edits`.
  Preserve `id`/`points` JSON keys and unknown user metadata.
- Path canvas press/right-click is dispatched through `PathsToolsMixin`,
  not reimplemented in `CanvasGridMixin` or other mixins.
- Routing-area drags use `MoveRoutingArea`; do not restore the removed
  CanvasGrid direct-mutation fallback. Keep navigation and history unchanged.
- Run `tools/test_phase8_canvas_gui.py` after changing event ownership.

## Edit transaction boundary (phase 9)

- One pointer edit should produce **one Undo/Redo step**, regardless of how
  many intermediate `Motion` or polling events occur.
- Use `SafeProjectMixin._begin_canvas_edit(owner)` and
  `_finish_canvas_edit(owner)` for migrated Installation/Layout/Cabling edits.
  Always pair opening and closing, including early-return and exception paths.
- Press/release history records use `prepare_zone_grids=False`: selecting a
  zone or clicking a control handle must not commit zone-grid metadata.
- Keep the diagram and mounting specialized gestures independently owned.
  The edit gate is not a replacement for project consistency or persistence.
- Run `tools/test_phase9_transactions_gui.py`, the 180 unit tests and a real
  Frimo roundtrip before changing undo/event lifecycle.

## Text and modal transaction boundary (phase 11)

- Validate questionnaire values and optional imports before calling
  `_run_project_edit('project:engineering-questionnaire', ...)` once. Preserve
  rollback on `_apply_document` failure and close a pre-existing text gesture
  before opening the modal window.
- For user-editable `Text` controls, open the history gate **before typing**:
  `_record_history` reads the live widget text. Close the gate on loss of focus.
- For numeric fields, validate the whole form before ending its focus gesture;
  malformed values should not be serialized or recorded.
- A keyboard Undo/Redo must commit an active edit first, then restore the
  document and re-arm any text field that remains focused.
- Keep the periodic legacy history fallback until all other UI edit paths
  have explicit transactions. See `docs/PHASE11_TEXT_EDIT_TRANSACTIONS.md`.

## Equipment transaction boundary (phase 12)

- MPPT drop-target interpretation and assignment validation belong to
  `domain.mppt_edits`; keep it independent of Tk and do not mutate its inputs.
- Run successful assign/unassign drops and the auto/clear menu actions through
  one `_run_project_edit` call. UI warnings for rejected drops do not change
  state and must not open a history entry.
- Keep `_notify_wiring_change` for actual electrical edits and the old
  `string_mppt_assignment` schema keys (`block`, `mppt`) untouched.
- Before changing Equipment menus or trees, run
  `tools/test_phase12_equipment_gui.py` and the Frimo JSON roundtrip.

## Spreadsheet and Material edit boundary (phase 13)

- Workbook mutations must use Tk-independent `domain.spreadsheet_edits`
  where possible, preserving schema-v2 raw formula text and unknown keys.
- One cell edit, formula-bar Apply, fill-handle drop, paste, confirmed clear,
  row/column operation or CSV import = one explicit Undo/Redo step; a no-op
  leaves the undo cursor unchanged.
- Begin a row/column resize transaction on mouse press, end only at release.
  Do not take snapshots on every drag frame.
- Material sheet row deletion must continue using `equipment_state` to
  repair module and inverter references. Guard Material UI actions with
  `_run_project_edit`, but do not change the stored French schema keys.
- Run the phase-13 Tk regression, unit tests, Frimo project roundtrip,
  and the previous-phase equipment and mounting regression tests.
- Keep `_poll_history` until there are explicit commits for every other
  mutation path and a Windows GUI test has verified equivalent behaviour.

## Phase 14 - Photograph and dimension editing

- Store roof-photograph offset in original-image pixels, never in zoomed
  canvas-screen pixels; use `domain.roof_registration.shifted_photo_offset`.
- Treat each background move and dimension-label move as one press/release
  transaction; modal calibration and imported images are explicit commands.
- Keep original zone and panel coordinates unchanged when translating or
  rescaling a replacement background photograph.
- Preserve the existing JSON schema; new measures must include the axis key
  to ensure deterministic Undo/Redo read-back.
- Keep periodic history as a fallback until all remaining legacy edit routes
  are migrated and tested.

## Shadowed legacy methods (phase 15)

- Keep `docs/MRO_OWNERSHIP.csv` aligned with the actual MRO (`python tools/report_mro.py`).
- Before deleting an override, establish that every higher-priority dispatch
  chain terminates without reaching it through `super()` or explicit class calls.
- Avoid removing cooperative `draw_grid`, on-canvas and notebook methods based
  only on duplicate names. Add GUI and MRO owner tests for every deletion.
- The legacy automatic history poll is intentionally kept until all mutation
  entry points have direct undo/redo verification.

## Site editing and history restoration (phase 16)

- Shadow obstacle positions are roof-image **pixels**, while their relative offsets and zone heights are **mm**; validate with `domain.site_edit_commands` before modifying project fields.
- Shadow and Cable gathering-point edits must be atomic using `_run_project_edit`, with no changes to roof-zone metadata not owned by the command.
- Undo/Redo may normalise derived caches such as `shadow_result` during JSON restoration. Do not erase the redo branch merely because derived state differs from its historic projection. Genuine user changes after Undo must still append a fresh history record.
- Keep the periodic history poller until **all** unported mutations have explicit, tested transaction boundaries. See `docs/PHASE16_SITE_EDIT_TRANSACTIONS.md`.
