# R16 - Architecture refactor: phase 16 (26 October 2026)

**Scope:** add explicit, atomic edit commands for Shadow obstacle placement, obstacle offset and clearing; zone height; and cable gathering points. Keep the legacy project JSON schema, 11 English tabs, drawings, formulas, native vector PDF, and manual GitHub build setup.

## Delivered

1. Added `domain/site_edit_commands.py` with Tk-independent validated coordinate, zone-height and gathering-point updates, preserving unknown user metadata.
2. Migrated Shadow image-click, reference, relative position, clear, and elevation controls to `_run_project_edit` transaction boundaries.
3. Migrated Cabling manual gathering-point placement and reset commands to explicit transactions; retained the original nearest-zone selection logic and routing invalidation.
4. Fixed a real Undo/Redo regression found by the new Tk tests: restored shadow caches can be normalized during load, and were previously misinterpreted as a new user edit, truncating the redo branch. The guard now compares against the **actual restored state**, while allowing genuine new edits to replace redo history.
5. Added seven pure-domain tests and one full Tk GUI end-to-end regression. See `docs/PHASE16_SITE_EDIT_TRANSACTIONS.md`.

## Verification

- **232/232 unit tests passed** (225 in phase 15).
- GUI: phase 16 Shadow and Cabling edit transactions, 11-tab architecture, phase 9 gestures, phase 12 MPPT and native vector Mounting PDF.
- Full 500-panel Mounting GUI test including zoom and engineering report: passed.
- Actual external Frimo project read/edit-boundary/write/read-back: **533 panels, 9 zones, 2 routing polygons, 32 strings** retained.
- **41 MRO collision names** (unchanged); no unsafe override deletion.

## Remaining

- The global 600 ms snapshot watcher is intentionally retained for unmigrated UI modifications. Shadow slider/entry parameters and other multi-input dialogs are next candidates.
- Application code is still Tkinter/mixin based; migration to a complete UI-independent command bus is not complete.
- No Windows runtime test, EXE, build workflow, `.spec`, or binaries are included.

---

# R16 - Architecture refactor: phase 15 (26 October 2026)

**Scope:** prune strictly unreachable MRO method definitions; no alteration of
project data, geometry, rendering, or undo/redo semantics.

## Delivered

- 14 shadowed method definitions deleted across 6 modules (359 definition lines).
- Unused historical alternatives to diagram sizing/list selection, zone
  editing, cable-route computations, weather import, energy workspace, toolbar
  building and help are gone; all live owners stay in place.
- MRO collision-name inventory reduced from **53 to 41**. The active callback
  order is unchanged. A unit test freezes the 14 corresponding ownership paths.
- `docs/PHASE15_MRO_CLEANUP.md` records the reasons, proof and validation;
  `docs/PHASE15_REMOVED_OVERRIDES.csv` lists the exact removed names.

## Verified

- 225/225 unit tests (223 in phase 14).
- 11-tab UI, diagram, Installation, Cabling, spreadsheet, MPPT,
  undo transactions, Mounting A/B/C, vector A3 PDF, 500-panel mounting GUI.
- Frimo JSON load/save/reload: **533 panels, 9 zones, 2 routing areas,
  32 strings**.

## Remaining boundaries

41 duplicate method names remain, most with real layered dispatch. The legacy
600ms history watcher remains necessary for not-yet-migrated editing actions;
this phase does not claim to have finished the CommandBus transition or
Windows executable verification. No build artifacts shipped.

---

# R16 - Architecture refactor: phase 14 (26 October 2026)

**Scope:** explicitly transactional roof-photo import, translation, reset and
calibration, plus dimension labels/creation/removal. Start from the phase-13
GitHub sources. Preserve existing local JSON schema and all installation
geometry, the 11 tabs, and the vector mounting PDF.

## Delivered

1. Extracted zoom-independent image offset and calibration calculations into
   `domain/roof_registration.py`. This domain module has no Tkinter dependency.
2. Moved import/replacement of the roof photo, reset, and calibration under
   single synchronous project edit transactions. Modal cancellation is a no-op.
3. Made left-button photograph and dimension-label moves single history
   gestures instead of relying on periodic polling. Switching out of photo
   move mode also closes its pending transaction.
4. Added explicit history for adding, removing and clearing dimensions. Newly
   drawn dimensions preserve their `axis` after Undo/Redo.
5. Added six pure-domain tests and a Tk regression script for all workflows,
   including replacement-photo alignment and JSON persistence.

## Verified

- **223/223 unit tests pass** (217 before phase 14).
- GUI tests: phase 14 photo and calibration, Installation zoom/photo, phase
  9-13 transaction regressions, Mounting A3 native vector PDF and 500-panel
  Mounting test.
- Real Frimo schema-v2 JSON: **533 panels, 9 zones, 32 strings and 2 routing
  areas** retained after read/write/read-back.
- **53 MRO name collisions**, unchanged. This phase reduces the remaining
  dependency on implicit history rather than removing unsafe method chains.

## Still pending

Other project-modifying legacy UI paths must be audited and migrated before
`_poll_history` can be removed. The phase 14 change does not claim complete
refactoring, codebase shrinkage or Windows-specific GUI verification.

---

# R16 - Architecture refactor: phase 13 (26 October 2026)

**Scope:** consolidate Spreadsheet and project Material sheet edits behind
explicit Undo/Redo boundaries, and move spreadsheet cell, paste, grid shape
and fill-handle operations to Tk-independent domain commands. This phase
starts from the phase-12 GitHub archive and changes no scientific formula,
project JSON schema or drawing/export engine.

## Delivered

1. Added `domain/spreadsheet_edits.py`: raw-cell validation, multi-cell
   paste with clipping and atomic input validation, row/column insertion
   and deletion with dimension metadata preservation, reference shifting,
   and numeric/formula fill-handles independent of Tkinter.
2. Migrated Spreadsheet edits to `_run_project_edit`: single-cell edit,
   Delete, formula-bar Apply, fill, paste, row/column insertion/deletion,
   clear, CSV import and variable insertion. Column and row resize gestures
   use `_begin_canvas_edit` on press and `_finish_canvas_edit` on release;
   intermediate motion does not create history records.
3. Migrated Material equipment-sheet row addition, confirmed deletion and
   cell commits to explicit edit transactions; existing reference cleanup
   (`equipment_state.delete_material_row`) and formulas are preserved.
4. Added 14 new pure-domain unit tests and an end-to-end Tk regression
   covering cell/paste/fill, resizing, Material rows/cells, CSV import,
   clear, Undo/Redo and JSON roundtrip.

## Verification executed

- `python -m unittest discover -s tests -q`: **217/217 tests passed**
  (203 in phase 12).
- GUI: `tools/test_phase13_spreadsheet_gui.py`, phase 9/10/11/12 edit
  transactions, phase 7/8 interactions, unified navigation, 11-tab
  architecture, native A3 Mounting PDF, and full 500-panel Mounting suite.
- Actual Frimo project JSON roundtrip: **533 panels, 9 zones,
  2 cable routing areas and 32 strings** preserved.
- MRO inventory: **53 multiply defined method names**, unchanged.
  `_poll_history` still runs as a compatibility fallback for paths not
  migrated; disabling it globally is not justified by this phase.

## Not yet migrated

The freeform image/scale editing workflows and some remaining utility
settings must still be assessed for explicit commit boundaries. The
snapshot watcher can only be retired after every mutation path is covered
by tests, including Windows Tkinter behavior. No EXE, installer, `.spec`,
build directory or GitHub build workflow is supplied in this ZIP.

---

# R16 - Architecture refactor: phase 12 (26 October 2026)

**Scope:** explicit MPPT Equipment assignment history, safe domain assignment
validation and equipment tree drop actions, preserving the legacy calculation
and project JSON.

## Delivered

1. Added `domain/mppt_edits.py` with pure assignment proposals, input
   immutability, MPPT limits and panel-count checks, plus Treeview drop intent
   normalization independent of Tkinter.
2. Wrapped Equipment tree assign/unassign, auto-distribute, and confirmed clear
   in explicit `_run_project_edit` boundaries. Invalid/cancelled/repeated
   operations do not create history steps; electrical synchronization remains
   event-driven for actual edits.
3. Added 12 domain unit tests and one full Tk equipment regression harness,
   updated the codemap and interaction conventions. No schema change.

## Verified

- `python -m unittest discover -s tests -q`: **203/203 tests pass**
  (191 in phase 11).
- GUI: real Equipment tree drag/drop and menu callbacks with history
  Undo/Redo, cancelled clear and rejected full MPPT.
- GUI: phase 11 text/questionnaire, phase 10 dialogs, phase 9 gestures,
  phase 7 hit tests, phase 4 diagram editor and Mounting native A3 vector PDF.
- Full Mounting GUI 500-panel suite passes, including save/restore and zoom.
- Frimo schema-v2 read/write/readback: **533 panels, 9 zones,
  2 routing areas and 32 strings** maintained.
- Method override inventory stays at **53 multiply defined method names**;
  this phase improves command ownership rather than deleting override owners.

## Pending

A global UI-independent project commit layer and removal of `_poll_history`
are still out of scope. The history watcher must remain until all edit paths
are migrated and Windows GUI validation has been completed. No EXE, `.spec`,
GitHub build workflow or generated files are included in the archive.

---

# R16 - Architecture refactor: phase 11 (23 October 2026)

**Scope:** extend explicit Undo/Redo transactions to the complete engineering
questionnaire, project notes, and cable-sizing text fields. All 11 tabs,
local schema-v2 JSON, formulas and vector PDFs remain unchanged.

## Delivered

1. Questionnaire validation/import before atomic `Apply`, with existing
   rollback preserved and previous unfinished note edits settled first.
2. Focus-based one-operation history for notes and DC sizing inputs.
3. Keyboard Undo/Redo first commits active typing and resumes a still-focused
   input after the document is restored.
4. Regression coverage for no-op/invalid input, active edit Undo, subsequent
   focus edits and actual questionnaire Apply/Undo/Redo.
5. Updated codemap and override inventory, packaged only sources, tests and
   docs with no EXE/build artefacts.

## Verified

- **191/191 unit tests** (185 in phase 10).
- GUI: text fields + questionnaire, tab architecture, unified camera,
  phase 8/9/10 interactions, installation, electrical diagram, Mounting A/B/C,
  500-panel Mounting and A3 vector PDF export.
- Frimo JSON: 533 panels, 9 roof zones, 2 routing polygons, 32 strings
  preserved on read/write/readback.
- **53 names** remain multiply defined in the MRO. This phase intentionally
  reduces dependency on the automatic history fallback, not the MRO count.

## Outstanding

Equipment drag/drop and other remaining non-migrated UI changes still rely on
`_poll_history`; do not disable it yet. Before removing further mixins, extend
tests to all editing pathways and validate Windows behavior. No build workflows
are included in this source archive.

---

# R16 - Architecture refactor: phase 10 (23 October 2026)

**Scope:** migrate the next set of synchronous ribbon and configuration
operations to explicit Undo/Redo boundaries. Based on the phase-9 source
archive; no changes to local JSON schema v2, calculations, panel numbering,
mounting clamps, PDF export or tab order.

## Changes actually implemented

1. `SafeProjectMixin._run_project_edit(owner, callback, ...)`: UI adapter
   leveraging the same `EditTransactionGate` introduced in phase 9. It
   preserves callback return values and exceptions, closes the transaction
   through `finally`, and treats nested commands as part of their parent.
2. Toolbar/ribbon operations migrated: Layout generation, new/delete block,
   removing an inverter placement, manual Stringing reorder/add/remove.
3. Form Apply actions migrated: Layout panel dimensions+orientation (one
   combined transaction), Installation zone dimensions/angle, routing heights,
   MPPT/inverter capacity and grid-connection limits. Zone deletion uses the
   same boundary.
4. Stringing tree drag/drop reordering is now one explicit command and sends
   the same electrical topology notification as the Move Up/Down buttons.
5. Added 5 unit tests for cancel/no-op, nesting, exceptions and lifecycle;
   added `tools/test_phase10_ribbon_dialog_gui.py` for real Undo/Redo on three
   dialogs/ribbon controls.

## Verification executed

- `python -m unittest discover -s tests -q`: **185/185 tests pass**
  (180 in phase 9).
- GUI: phase-10 grid settings, block create/cancel and zone Apply Undo/Redo;
  phase-9 pointer transactions; 11-tab architecture; unified navigation;
  phase-8 Installation/Cabling edits; electrical diagram Undo/Redo; Mounting
  6-point A/B/C preview and native vector A3 PDF.
- Full 500-panel Mounting live regression: native zoom, shared clamps,
  labels, PDF engineering report and JSON recovery all pass; benchmark in
  executed harness median 9.8 ms/frame, not a universal performance claim.
- Real Frimo schema-v2 JSON read/save/readback: **533 panels, 9 zones,
  2 cable routing areas and 32 strings** maintained.
- `tools/report_mro.py`: **53 redefined method names**, unchanged. Phase 10
  adds transaction boundaries rather than removing unrelated mixins.

## Remaining priorities

- Migrate the engineering questionnaire's special rollback/replace behavior
  and equipment tree MPPT drop; expand the same command contract to other
  settings, while keeping programmatic editing compatible.
- Introduce explicit project commits/validation independent of Tkinter and
  progressively retire periodic 600-ms history polling once every edit path
  is covered. It is intentionally retained as a fallback for now.
- Preserve Windows EXE build ownership in GitHub. This archive has no
  installer, generated executable, `.spec` or local build workflow.

---

# R16 - Architecture refactor: phase 9 (23 October 2026)

**Scope:** explicit edit history transactions for Installation, Layout and
Cabling. Based on the phase-8 source archive. The schema-v2 JSON, English UI,
11 tabs, Mounting clamp geometry, and vector PDF generation are unchanged.

## Changes actually implemented

1. `application/edit_transactions.py`: new pure `EditTransactionGate` (explicit
   owner, begin/finish/abort), no Tkinter and no serialized changes.
2. `SafeProjectMixin`: before/after snapshot at edit boundaries; the
   release/poll timer cannot create intermediate records during a gesture.
   Both snapshots avoid a zone-grid recalculation at mere pointer press.
3. `CanvasGridMixin`/`EditorInteractionsMixin`: one history step for selected
   zone moves/resizes, dimension label moves, polygon/vertex drags and Ctrl
   paint/erase across multiple cells. Early-return release branches close the
   transaction, including Ctrl-right release through `DiagramEditorMixin`.
4. `PathsToolsMixin`: complete cable path and polygon creation/deletion is
   immediately undoable with one before/after boundary.
5. Added gate-level unit tests and GUI transaction parity script. Existing
   Diagram and Mounting history remains independently owned, unchanged.

## Validation executed

- `python -m unittest discover -s tests -q`: **180/180** (176 in phase 8).
- Live GUI transaction harness: zero-distance clicks do not add history,
  multi-frame zone/area move or Ctrl add/remove creates one Undo/Redo record,
  cable-path creation/deletion is immediately reversible.
- GUI phase 8, phase 7, architecture, unified navigation, diagram editing,
  string/MPPT notifications and Mounting vector A3 export passed.
- Complete 500-panel Mounting GUI/regression passed (including the 21-page
  vector engineering report); zoom stress median **12.3 ms/frame** in the
  executed harness, not a claim about all computers.
- Real Frimo project JSON roundtrip: **533 panels, 9 zones, 2 cable routing
  areas and 32 strings** retained.
- `tools/report_mro.py`: **53 names** still have more than one definition.
  Phase 9 eliminates intermediate snapshot churn, not method-name collisions.

## Remaining migration priorities

- Convert ribbon/dialog operations and image/scale changes to explicit edit
  transactions before retiring periodic history capture.
- Centralize model commits/validation outside Tkinter mixins, and avoid
  `_recalculate_zone_grids()` at each zone-drag motion frame.
- Expand GUI golden-state tests and Windows runtime verification before any
  broad removal of the remaining 53 method-name collisions.

No EXE, installer, build script, `.spec` or user data are packaged.

---

# R16 - Architecture refactor: phase 8 (23 October 2026)

**Scope:** separate Installation zone geometry and Cabling path creation from
shared canvas pointer callbacks. This release starts from phase 7 and retains
the 11 English-language tabs, all mounting calculations, local JSON schema v2
and vector PDF generation. No build configurations or executable files.

## Actual changes

1. Added `domain/installation_edits.py`: pure multi-zone movement, four-corner
   resizing with the existing 15-screen-pixel limit, and new-zone geometry.
   Absolute drags do not accumulate floating-point drift; non-geometry zone
   metadata is retained on commit.
2. Added `domain/cabling_edits.py`: immutable temporary-point append and
   schema-compatible cable-routing polygon and path constructors, with
   geometric validity checks and existing ID allocation policies.
3. `PathsToolsMixin` now owns Installation/Cabling path press and right-click
   dispatch. `CanvasGridMixin` delegates those gestures rather than duplicating
   routing-mode logic in its generic canvas handlers.
4. Removed unreachable direct polygon dragging from the legacy base
   `CanvasGridMixin`: `EditorInteractionsMixin` and its `MoveRoutingArea`
   command remain the authoritative polygon move/vertex edit path.
5. Updated remaining numeric references to `TabId.INSTALLATION` and
   `TabId.STRINGING` in migrated mouse handlers. No notebook reordering.
6. Added 16 pure-domain/MRO unit tests and a live GUI parity test covering
   multi-zone movement, resizing, polygon/path creation and JSON persistence.

## Executed validation

- `python -m unittest discover -s tests -q`: **176/176 pass**, formerly 160.
- `tools/test_phase8_canvas_gui.py`: new multi-zone/resize/polygon/Cabling/JSON
  scenario passes in Tkinter.
- Existing architecture (11 tabs), Installation image pan/scale, unified mouse
  navigation, phase-7 gestures, electrical diagram Undo/Redo, mounting A/B/C
  and A3 vector PDF GUI tests pass.
- Real schema-v2 Frimo project read, save and reread: **533 panels, 9 roof
  zones, 2 cable routing areas and 32 strings** preserved.
- Effective MRO: **53 method-name collisions**, unchanged; `draw_grid` has
  three active chain owners and left-button handlers four.

## Unfinished work

- The zone drag adapter still commits field patches into live Tkinter state,
  recalculates zone allocations and redraws; a universal GUI-independent
  edit transaction/history service remains future work.
- Cable-path automatic routing and gathering-point placement remain in their
  existing services. This phase does **not** change wiring algorithms or
  Mounting dimensions.
- Full Windows executable parity has not been exercised; the user owns the
  EXE workflow in GitHub. No EXE/installer/spec/build output is packaged.

See `docs/PHASE8_CANVAS_COMMAND_BOUNDARIES.md` for ownership and contracts.

---

# R16 - Architecture refactor: phase 7 (23 October 2026)

**Scope:** eliminate redundant left-button dispatch wrappers, remove obsolete
diagram direct-mutation paths, extract read-only Installation hit testing and
standardize canvas tab identifiers. Based on phase 6. No JSON schema, panel
layout algorithm, cable routing geometry, mounting calculations, vector PDF
export logic or user-facing English labels have changed.

## Changes made

1. Removed three pass-through left-mouse handlers from
   `WorkspaceImprovementsMixin`. The only legacy `_canvas_pan_start` reset is
   retained inside `EditorInteractionsMixin` when delegating an edit.
2. Left press/drag/release resolve through **four owners rather than five**:
   Mounting -> DiagramEditor -> EditorInteractions -> CanvasGrid.
3. Added read-only, Tk-free `ui/gesture_hit_testing.py` to consolidate two
   duplicated zone hit-test loops, resize-handle hit testing, and last-on-top
   dimension label hit testing. Original click tolerance and overlap precedence
   are preserved.
4. Removed obsolete diagram drag and selection branches from `CanvasGridMixin`.
   DiagramEditor owns the normal gestures; only diagram link mode enters
   CanvasGrid. This prevents bypassing the copy-on-write Undo/Redo commands.
5. Replaced positional tab indices with `TabId` names in the modified shared
   canvas handlers. No notebook order or saved tab IDs changed.
6. Re-generated `docs/MRO_OWNERSHIP.csv`, added
   `docs/PHASE7_GESTURE_OWNERSHIP.md` and 14 new tests.

## Validation executed

- `python -m unittest discover -s tests -q`: **160/160 passing** (146 before).
- Live Tk `tools/test_phase7_gesture_gui.py`: zone selection, resize, dimension
  label, Ctrl multi-select and diagram link-mode no-op with stale legacy state,
  diagram movement as a single undoable edit.
- GUI: architecture (11 tabs), unified and large-photo navigation, Installation
  (photo move/scale/measure), diagram editing/JSON Undo/Redo, Mounting A/B/C,
  Mounting native vector A3 PDF and phase 6 paint/zone invariant tests.
- Full `tools/test_mounting_gui.py`: 500-panel scene, vector drawing + 21-page
  engineer report, dimension labels and project persistence verified.
- Project JSON `tools/test_project_roundtrip_gui.py` on the existing Frimo
  project: **533 panels, 9 zones, 2 routing polygons and 32 strings** preserved
  by load/save/reload. User project is NOT bundled.
- Effective MRO: **53 method-name collisions** (unchanged), `draw_grid`
  retains three owners, left gesture chains shortened from 5 to 4.

## Explicit limitations

- This is not yet a single application-wide gesture router or universal
  Undo/Redo command bus. Installation/Cabling editing still uses legacy
  `CanvasGridMixin` branches; removing the remaining handlers requires a
  gesture-by-gesture parity harness.
- Custom diagram pointer gestures are now protected from the obsolete base
  mutation path but existing diagram and mounting specific handlers remain.
- Project/schema data and UI structure are unchanged. No Windows EXE build
  or PyInstaller workflow is included; that remains owned by the user.

---

# R16 - Architecture refactor: phase 6 (23 October 2026)

**Scope:** zone-grid computation and paint/edit boundary. This release is based
on phase 5. Local project schema v2, 11 tabs, mounting rules and PDF/CSV exports
remain unchanged. It contains Python sources and tests only, not Windows build
artifacts or executable packaging configurations.

## Changes actually made

1. **Read-only zone-grid signature** (`domain/zone_grid_state.py`): describes
   geometric inputs and derived allocations, ignoring unrelated installer notes
   and elevations. The helper imports no Tkinter.
2. **Idempotent grid allocation** (`InstallationGeometryMixin._recalculate_zone_grids`):
   only runs `grid_spec` and `zone_registry.allocate_ranges` when the signature
   differs. A repeated geometry query or explicit check on an unchanged model
   no longer remaps coordinates, changes UIDs or allocates ranges.
3. **No zone-grid mutation during painting:** the Layout/Stringing and Shadow
   branches of `CanvasGridMixin.draw_grid` now use committed zone projections;
   `ShadowGeometryMixin._panel_rect` no longer triggers an allocation merely to
   measure a panel. Painting and mouse-wheel zoom do not commit pending zone
   geometry changes.
4. **Explicit edit/IO boundaries:** zone creation, dimension changes, zone
   drags, generation and cell hit-testing prepare grids at the action boundary.
   Saving, project loading, tab switching and explicitly recorded history also
   prepare a fresh grid. The background 600ms history polling intentionally
   **does not** commit pending zone calculations (regression caught and fixed
   in the navigation test). Legacy `row_base`/`row_capacity` allocation and
   `remap_zone_state` callback still preserve panel and string identities.
5. **Proven masked code removal:** removed the old 66-line
   `ZoneToolsMixin._recalculate_zone_grids`, always hidden behind the active
   `InstallationGeometryMixin` implementation. There are now **53 duplicated
   method-name groups**, down from 54; `draw_grid` still has three implementations.

## Validation executed

- `python -m unittest discover -s tests -q`: **146 passing tests** (137 in phase 5),
  including 9 new domain/geometry tests in `tests/test_phase6_zone_grid_boundary.py`.
- `tools/test_phase6_zone_paint_gui.py`: live 11-tab Tkinter app, zone
  calculation on tab/history, repeated zoom and redraw, read-only panel geometry,
  background-history behavior and Shadow roof-image painter.
- GUI regressions include: cursor-anchored zoom with a large photo and 80 diagram
  nodes; Installation drag, unified navigation; Diagram Undo/Redo; Mounting A/B/C,
  gaps, dimension labels and native vector A3 PDF.
- `tools/test_mounting_gui.py`: complete 500-panel and engineering report regression.
- `tools/test_project_roundtrip_gui.py` with the existing Frimo project: **533
  panels, 9 zones, 2 routing areas and 32 strings** survive JSON load/save/readback.
- Re-generated `docs/MRO_OWNERSHIP.csv`: **53** method-name collisions; no
  redundant `_recalculate_zone_grids` definition, and 3 `draw_grid` owners.

## Limits / next work

- **Not a pure application yet.** Legacy toolbar and gesture code still mutates
  Tk-backed state; CanvasGrid adjusts viewport and UI label values during paint.
- An externally mutated zone does not become a committed panel grid until an
  explicit edit, tab switch, save, or direct history action. This is intentional:
  repaint is not an editing command. A passive history snapshot must not remap
  zone rows.
- Legacy `ZoneToolsMixin._get_cell_coords` paths and other interaction overrides
  still need consolidation with the dedicated geometry adapter; this requires
  click/drag/rotation tests before deletion.
- The full universal Undo/Redo command bus and single gesture dispatcher remain
  pending. Windows EXE creation is intentionally managed by the project owner.

---

# R16 - Architecture refactor: phase 5 (23/10/2026)

Phase 5 continues the source-only GitHub release of phase 4. All **11 tabs**, English UI, schema-v2 local JSON, mounting rules and native vector PDF exports remain available. No EXE workflow, `.spec`, compiled files or installation artifacts are included.

## What changed

1. **Project consistency leaves canvas repaint:** `SafeProjectMixin.draw_grid()` no longer repairs panel UIDs, clears stale shadow data or projects electrical topology. Such model changes now occur at explicit project boundaries: `SafeProjectMixin._reconcile_project_state` (history snapshots, save/autosave, loading and tab changes), plus edit-triggered electrical events from phases 2-4. Diagram layout preparation on entering the diagram tab also occurs before the renderer.
2. **Pure reconciliation plan:** `domain/reconciliation_plan.py` determines which consistency actions are necessary without imports from Tkinter, allocation of UIDs, or modification of project records. A clean signature skips the expensive projection.
3. **Immediate layout edits:** `InstallationGeometryMixin.generate_panels_from_zones` reconciles newly generated/deleted panel identities before drawing. Ctrl-click add/remove in Layout does the same. This is important for immediate use by Mounting, even if there is no tab switch or undo poll.
4. **Fewer draw-grid overrides:** the selected routing polygon's four-pixel white editing handles now belong to `CanvasGridMixin._draw_selected_polygon_handles`; the single-purpose `EditorInteractionsMixin.draw_grid` override was removed. The effective draw chain is now **SafeProject -> Mounting -> CanvasGrid**, down from four to three definitions. The count of **method names with collisions remains 54**, because `draw_grid` still has three owners.
5. **Test maintenance:** the 80-node diagram navigation test now inspects the authoritative `app.diagram_nodes` mapping after a copy-on-write drag, not the old dictionary reference. The 500-panel mounting stress test explicitly commits its synthetic direct mutations instead of relying on a repaint.

## Executed validation

- `python -m unittest discover -s tests -q`: **137 passing tests** (130 in phase 4).
- `tools/test_phase5_paint_boundary_gui.py`: proves that repaint cannot allocate UIDs, invalidate cached shadows or reconcile wiring; history, tab switching and save do reconcile, while editor handles remain visible without a roof image.
- GUI checks pass: Architecture (11 tabs), Canvas Navigation (80 custom nodes + camera), Installation, Unified Navigation, Mounting full regression (500 modules and 21-page engineering report), Mounting A/B/C, shared clamps, dimension labels, native vector A3 PDF, Phase 3 electrical events and Phase 4 diagram edits/Undo/Redo.
- `tools/test_project_roundtrip_gui.py` with a real existing Frimo JSON: **533 panels, 9 zones, 2 cable routing polygons, 32 strings** survive load/save/read-back. This project is *not* bundled into the source archive.
- `tools/report_mro.py`: **54 method-name collisions**, and **3 implementations of `draw_grid`**.

## Deliberate limitations and next priorities

- **Not all drawing operations are pure.** `CanvasGridMixin.draw_grid` still updates viewport/UI state, and legacy helpers (e.g. zone grid recalculation in the Shadow view) require a future edit-boundary migration. This phase removes *project identity, stale-shadow invalidation and wiring projection* from paint; it does not claim complete GUI/model separation.
- Non-migrated edit paths still depend on the history timer (300/600 ms), tab changes, or project saving for eventual consistency. Add explicit notifications to remaining mutators before removing this fallback.
- Snapshot-based Undo/Redo and the remaining 54 mixin name collisions are not yet replaced by a universal command bus. Changes to serialization format were intentionally avoided.
- The source archive has no build configuration; Windows executable parity is not asserted.

---

# R16 - Architecture refactor: phase 4 (23/10/2026)

The phase 4 release follows phase 3 and preserves the entire source application, **all 11 tabs**, the English UI, local schema-v2 JSON and existing engineering calculations. The previous phase-3 status remains below as audit history. No EXE build files are included.

## Changes implemented in phase 4

1. **Pure diagram editing model**: `domain/diagram_commands.py` now supplies copy-on-write actions to add custom blocks, create manual connections, delete selections, move selected groups with absolute drag deltas, and apply a reflow. All link style, distance, and unrelated metadata are preserved. It imports no Tkinter.
2. **Undo/Redo transaction boundaries**: `DiagramEditorMixin._apply_diagram_edit` captures before/after states; gesture start/end captures one history transition for an entire drag. `_record_history` suppresses intermediate snapshots while dragging. Auto-generation, reflow and electrical-spec changes have explicit history capture.
3. **Delete and link ownership**: the effective diagram deletion handler in `EditorInteractionsMixin` delegates to the new domain command, as do custom-node creation (`DiagramToolsMixin`) and manual-link creation (`CanvasGridMixin`). One older shadowed `_delete_selected_diagram_node` definition was removed from `DiagramToolsMixin`.
4. **Painting no longer adjusts diagram coordinates**: `DiagramEditorMixin._prepare_diagram_layout` runs before CanvasGrid's painting step when the single-line tab is visible. `_draw_diagram()` itself emits canvas primitives and does not alter nodes/links.
5. **Responsiveness**: only moved nodes are copied for each drag frame, not the entire project or all node metadata. Existing mouse navigation conventions were retained.
6. **Codemap and MRO**: `docs/MRO_OWNERSHIP.csv` regenerated. Collision-name count is **54**, down from 55. The four `draw_grid` implementations still form a required legacy chain.

## Executed validation

- `python -m unittest discover -s tests -q`: **130/130 tests pass** (123 in phase 3).
- `xvfb-run -a python tools/test_phase4_diagram_gui.py`: create, manual link, grouped drag with one undo step, undo/redo restore, local JSON roundtrip, node/link persistence, zoom without new history, read-only diagram painter.
- `tools/test_architecture_gui.py` and `tools/test_phase3_electrical_gui.py`: pass (11 tabs, unified view-only history, wiring updates without paint).
- Existing Installation, Unified Navigation, Mounting A/B/C, and vector A3 mounting PDF GUI tests: pass.
- Frimo integration test: **533 panels, 9 roof zones, 2 cable-routing areas, 32 strings** load/save roundtrip. These user project files are not bundled into the distribution.

## Explicit limits and next migration priorities

- **This is not a full rewrite or a pure project-wide renderer.** `SafeProjectMixin._prepare_canvas_model` still reconciles wiring topology, panel UIDs and shadow provenance for old edit paths. Only `_draw_diagram()` no longer changes diagram positions.
- The project Undo/Redo system still uses data snapshots and scheduled checking for non-migrated tabs; the diagram gesture boundaries are now explicit. A universal CommandBus is future work.
- 54 remaining method-name collisions must be resolved through testing and ownership transfer, not blindly removed. All 11 UI tabs and calculators remain coupled to the legacy mixin class.
- There is no GitHub Actions workflow, `.spec` file, Windows installer or EXE in this archive. Windows runtime parity has not been tested.

---

# R16 - Refonte architecturale, phase 3 (23/10/2026)

Cette livraison reprend integralement la phase 2. **Migration progressive, sans changement du format JSON, des cotes de montage ou des calculs electriques**. Aucune configuration de build Windows incluse.

## Travaux effectues en phase 3

1. **Edition des strings sans Tkinter** : `domain/string_commands.py` propose `add_panel`, `remove_panel`, `remove_at` et `reorder_panel`, avec retour immuable `StringEdit`. Les entrees ne sont pas mutees ; les IDs et l'ordre restent inchanges. `StringingToolsMixin` utilise ces operations pour les editions manuelles.
2. **Synchronisation electrique declenchee par les edits** : `ElectricalTopologyChanged(source)` est un evenement metier dans `application/events.py`. Les modifications des strings, des affectations MPPT, de la capacite et des blocs onduleur publient l'evenement via `ProjectIntegrityMixin._notify_wiring_change` ; `SafeProjectMixin._on_domain_event` met a jour le schema independamment du dessin. Le controle de signature evite de recalculer une topologie identique.
3. **Mises a jour indirectes** : remappage des adresses des zones, retrait de panneaux et nettoyage d'affectations MPPT declenchent egalement une notification en cas de changement effectif.
4. **Chargement** : un point explicite de reconciliation du schema est ajoute apres chargement de l'etat du projet dans `SafeProjectMixin._apply_document`, avant l'appel a `draw_grid`.
5. **Routeur de gestes** : `ui/gesture_policy.py` definit des intentions pures pour les clics et deplacements sur l'onglet Installation. L'editeur du schema unifilaire conserve la propriete exclusive des gestes du schema (`DiagramEditorMixin`). Suppression des branches de selection/deplacement du diagramme devenues inaccessibles dans `EditorInteractionsMixin`, en verifiant l'ordre de resolution MRO.
6. **Tests** : nouveaux contrats pour les editions immuables, les notifications et projections, les intentions de gestes, plus test Tkinter sans dessin pour prouver que la mise a jour electrique ne depend plus necessairement de `draw_grid`.

## Validations executees

- **123/123 tests unitaires reussis** (`python -m unittest discover -s tests -q` ; 114 precedemment).
- Tests Tkinter reussis : `test_architecture_gui`, `test_unified_navigation_gui`, `test_canvas_navigation_gui`, `test_installation_gui`, `test_mounting_abc_gui`, `test_mounting_pdf_gui`, `test_phase3_electrical_gui`.
- Test de chargement/reecriture Frimo avec projet fourni : **533 panneaux, 9 zones, 2 zones de cablage, 32 strings**. Projet non integre au code ni a la distribution.
- Export Mounting PDF A3 vectoriel, sans raster, verifie par test GUI.
- Inventaire MRO regenere : **55 groupes** de noms de methodes en collision ; la chaine `draw_grid` reste de quatre implementations. Aucun nom de methode encore necessaire n'est supprime.

## Limites, explicitement maintenues

- `SafeProjectMixin._prepare_canvas_model` conserve **temporairement la reconciliation de secours** pendant le dessin, car il existe encore des chemins historiques ou des modifications directes du modele non migrees. `draw_grid` n'est **pas encore une fonction sans effet de bord**. La migration complete exige des tests de toutes les operations de Layout, import, Undo/Redo et edition du schema.
- Le systeme d'historique reste hybride : capture par changement d'etat + notifications explicites, non un CommandBus unique. Les vues zoom/pan ne doivent toujours pas produire de nouvel etat.
- La duplication des noms de methodes (**55**) est inchangee : les suppressions de cette phase portent sur des *branches* inaccessibles, pas sur des definitions entieres. La reduction future doit etre fondee sur l'analyse MRO et tests.
- Pas de build EXE, et aucun controle d'execution sous Windows.

## Suite recommandee (phase 4)

1. Centraliser toutes les mutations de schema (ajout, liens, suppression, reflow) dans des commandes independantes de Tkinter avec Undo/Redo.
2. Instrumenter la totalite des chemins de modification des zones et du calepinage (y compris import et suppression rapide) puis retirer la reconciliation de secours de `draw_grid` seulement lorsque des tests prouvent l'exactitude de la projection.
3. Migrer les gestes souris restants vers un routeur explicite par onglet tout en preservant l'API de compatibilite.
4. Consolider les commandes MPPT et les validations electriques derriere le domaine, sans modifier les regles actuelles d'affectation ou de capacite.
5. Continuer la suppression de code masque prouve (et non uniquement suspect) a couverture equivalente.
