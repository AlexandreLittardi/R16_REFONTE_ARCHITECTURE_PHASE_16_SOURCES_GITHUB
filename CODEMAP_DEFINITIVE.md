# R16 - Code map (post-audit, migration baseline)

**Date:** 26 October 2026. **Target:** desktop Python/Tkinter, English-language interface, local schema-v2 JSON. No server, `.spec`, executable or local packaging script. **Status:** phase 16 incremental refactor (232 tests), not a completed rewrite.


## Phase 16 - Shadow/Cabling site-edit boundaries and Undo restoration

- `domain/site_edit_commands.py`: pure image-coordinate/relative-offset, zone-height and gathering-point commands (unknown metadata preserved, finite-number validation).
- `mixins/shadow_tools.py` + `mixins/canvas_grid.py`: image-click obstacle/reference, offset, elevation and clear actions are one synchronous history transaction each; Shadow calculations unchanged.
- `mixins/cable_network.py`: manual gathering-point and reset actions are one history transaction each; nearest-zone selection and route invalidation unchanged.
- `mixins/safe_project.py`: restored-document signature prevents derived shadow-preview normalisation from creating a phantom edit and deleting Redo history.
- Tests: `tests/test_phase16_site_edits.py`, `tools/test_phase16_site_edits_gui.py`; full description in `docs/PHASE16_SITE_EDIT_TRANSACTIONS.md`.
- **232 unit tests passed; 41 duplicated MRO names remain.** The legacy fallback poller remains enabled until the remaining edit paths are migrated and verified.

## Phase 15 - Proven-dead override cleanup

- MRO-based inventory and explicit-call search identified 14 unreachable
  definitions. Their removal does not change any live method dispatch.
- Removed old DiagramTools, ZoneTools, CableNetwork, SelfConsumption, toolbar,
  help and energy-workspace implementations (see
  `docs/PHASE15_REMOVED_OVERRIDES.csv`).
- Current dispatch owners are protected by `tests/test_phase15_shadowed_cleanup.py`.
  **225 tests pass**, including the full Frimo JSON and Mounting GUI regressions.
- Colliding method **names: 53 -> 41**; the two toolbar chains got shorter
  while their method names still have multiple definitions.
- Legacy automatic history polling remains for unported mutation paths;
  `draw_grid` and cooperative event-handler overrides are deliberately retained.
- See `docs/PHASE15_MRO_CLEANUP.md` for the evidence and remaining work.

## Phase 14 - Roof image registration and calibration

- `domain/roof_registration.py` (no Tkinter): zoom-invariant photograph
  translation, scale measurements, and replacement-photo resizing factor.
- `mixins/canvas_grid.py`: image move and measurement label gestures have one
  history step per drag; calibration and measure creation/deletion commit
  explicitly. New measures always carry the alignment axis during serialization.
- `mixins/zone_tools.py`: imported/replaced image, reset offset, and clear
  measurements use explicit project edit transactions. Existing geometry,
  JSON keys, survey scale and vector export engines are not changed.
- Contract: `docs/PHASE14_ROOF_HISTORY.md`; tests:
  `tests/test_phase14_roof_registration.py`,
  `tools/test_phase14_roof_history_gui.py`. **223 unit tests** pass.
- **53 MRO method-name collisions** remain. Automated history polling is
  retained as a fallback for other un-migrated interactions.

## Phase 13 - Spreadsheet and Material edit transactions

- `domain/spreadsheet_edits.py` (no Tkinter): validated raw-cell writes,
  atomic paste input, axis extension/trimming, formula-reference
  translation and numeric/formula fill. Existing schema-v2
  `material_spreadsheet` fields stay unchanged.
- `mixins/spreadsheet_tools.py`: cell editor and formula bar, variable insert,
  sheet dimensions, CSV import and clear use one explicit
  `_run_project_edit` per user action. Row/column resizing uses one
  press/release edit gate regardless of drag frame count.
- `mixins/spreadsheet_interactions.py`: clipboard paste and fill-handle
  call the pure commands and commit once. Navigation, selection and zoom
  do not change project history.
- `mixins/material_tools.py`: equipment sheet rows and raw field edits use
  explicit transactions. Linked inverter/module reference cleanup is still
  performed by `equipment_state.delete_material_row`.
- Tests: `tests/test_phase13_spreadsheet_edits.py` and
  `tools/test_phase13_spreadsheet_gui.py`. **217 unit tests** pass and the
  real Frimo JSON roundtrip is unchanged.
- There are **53 MRO name collisions**; the history fallback is kept until
  all project mutation paths have been inventoried and migrated.

## Phase 12 - Equipment / MPPT transactions

- `domain/mppt_edits.py`: pure MPPT assignment proposal + robust drop-target
  interpretation; no widget calls, input dictionary modifications or file I/O.
- `mixins/equipment_tools.py`: equipment Treeview assign/unassign release
  events use `_run_project_edit('equipment:mppt-drop', ...)`; rejected or
  repeated drops create no history entry; successful changes continue to
  publish wiring changes and refresh the tree.
- `mixins/ui_builders.py`: Auto-assign and Clear MPPT menu commands now use
  `equipment:auto-mppt` and `equipment:clear-mppt` transaction boundaries.
- Invariant: a successful assignment, unassignment, automatic distribution
  or confirmed clear is one Undo/Redo step. Invalid/unchanged/cancelled edits
  do not create a history step. The schema-v2 JSON assignments and electrical
  projection are unchanged.
- Source and verification: `docs/PHASE12_MPPT_TRANSACTIONS.md`,
  `tests/test_phase12_mppt_edits.py`, `tools/test_phase12_equipment_gui.py`.
- **53 MRO name collisions remain**, unchanged. `_poll_history` remains a
  compatibility fallback for UI paths outside the migrated boundaries.

## Phase 11 - Text fields and engineering questionnaire

- `mixins.configuration_questionnaire.show_questionnaire`: validation / imports
  precede one explicit `project:engineering-questionnaire` transaction. A
  failed Apply restores the original document without adding an undo step.
- `mixins.notes_tools.NotesToolsMixin`: notes `FocusIn`/`FocusOut` batches one
  typing session; valid DC sizing fields are also committed on focus loss.
- `mixins.safe_project.SafeProjectMixin`: Undo/Redo first settles any active
  text edit and then re-arms the still-focused widget after restoration.
- The old 600-ms polling is still a **compatibility fallback**, not an edit
  transaction API. No mixin was deleted: there are 53 MRO name collisions.
- Source of detailed contracts and test commands:
  `docs/PHASE11_TEXT_EDIT_TRANSACTIONS.md`.

## Entry point and ownership

```text
main.py -> platform_setup.py -> app.PVLayoutRibbonApp (11 tabs)
                        | legacy mixins = UI controllers + domain integration
                        |
                        +-- domain/ (no Tkinter)
                        |   +-- schema.py                JSON schema version 2
                        |   +-- serialization.py         serial, fingerprint
                        |   +-- geometry_validation.py   valid_polygon
                        |   +-- project_document.py      defensive immutable snapshot
                        |   +-- project_consistency.py   stable panel UID mapping
                        |   +-- reconciliation_plan.py  pure consistency requirements (no Tk)
                        |   +-- zone_grid_state.py      pure signature for zone grid inputs and allocations
                        |   +-- routing_geometry.py      pure area transform in image px
                        |   +-- installation_edits.py    zone translate/resize/create (image px)
                        |   +-- cabling_edits.py         path/area creation (JSON schema v2)
                        |   +-- mppt_edits.py            pure MPPT proposals and drag/drop intents
                        |   +-- spreadsheet_edits.py     cell, paste, fill and sheet structure commands
                        |   +-- roof_registration.py     photo offset, calibration and scale alignment
                        |   +-- layout_remap.py          pure global-row translation for layout/strings/UIDs
                        |
                        +-- application/ (no Tkinter)
                        |   +-- routing_commands.py      MoveRoutingArea absolute drag command
                        |   +-- events.py                RoutingAreaChanged, EventBus
                        |   +-- undo_redo.py             shared payload, editing-only signatures
                        |   +-- edit_transactions.py     explicit gesture/ribbon/dialog history gate (phases 9-12)
                        |   +-- diagram_projection.py    pure defensive electrical wiring projection
                        |
                        +-- infrastructure/
                        |   +-- json_repository.py       ProjectRepository read/write/recovery
                        |   |                            wraps established schema-v2 validation,
                        |   |                            atomic save, backups and routing verification
                        |   +-- project_store.py         legacy facade/writer (root module)
                        |   +-- project_validation.py    migration, normalization, MPPT diagram
                        |
                        +-- ui/
                        |   +-- tab_ids.py               TabId 0..10, drawing groups
                        |   +-- gesture_policy.py       pure Installation click/drag intent
                        |   +-- gesture_hit_testing.py  pure Installation zone/dimension hit tests
                        |
                        +-- mixins/ (legacy adapters retained until parity)
                            +-- safe_project.py          persistence/history + state reconciliation at edit/IO/tab boundaries
                            +-- editor_interactions.py   routing command -> domain event
                            +-- paths_tools.py           single owner of path gestures
                            +-- unified_navigation.py   sole live wheel/middle-pan event bindings
                            +-- project_io.py            preserve all routing metadata on load
                            +-- ui_builders.py           dead outer-scroll UI removed
                            +-- project_integrity.py    explicit wiring projection synchronization
                            +-- installation_geometry.py adapter for pure row remapping
                            +-- remaining UI and simulation/render mixins preserved
```

The domain module layer has no `tkinter` imports; the only location touching `Path.open`, JSON on disk, backup files or roof image persistence remains the infrastructure/legacy persistence layer. `ProjectDocument` does not implicitly validate, normalize or assign IDs: normalization occurs on repository read/write, not during read-only snapshots.

## Phase 10 - Explicit ribbon and configuration history boundaries

```text
Layout ribbon: Generate / New Block / Delete Block / Remove inverter
Stringing side panel: Move up/down / Add/remove / tree drag reorder
Installation: Zone Settings Apply / Delete Zone menu / Routing Heights Apply
Equipment: MPPT capacity Apply
Project: Grid Connection Apply
Panel configuration: Width + Height + Tilt + Azimuth as one Apply
         -> SafeProjectMixin._run_project_edit(owner, callback, ...)
         -> _begin_canvas_edit(owner) / EditTransactionGate
         -> existing mutation/validation function (unchanged algorithms)
         -> _finish_canvas_edit(owner) -> one Undo/Redo record
```

`_run_project_edit` is a synchronous adapter: it records model state before
mutation, suppresses automatic polling and callbacks during the command, and
records the result once. Invalid input/cancel/no-op does not add a new history
entry. Nested operations reuse the parent's owner, and the gate closes even
when an operation raises. The Stringing tree reorder now emits an electrical
change notification, consistent with the existing up/down edit behavior.

`application/undo_redo.py`, the JSON data schema and the diagram/Mounting
specialized history remain unchanged. Non-migrated entrypoints are still
protected by the existing periodic snapshot fallback. The engineering
questionnaire has its own validated rollback-and-restore path, which remains
separate pending targeted migration. See `docs/PHASE10_COMMAND_TRANSACTIONS.md`
for the exact migrated callbacks and GUI tests.

## Phase 9 - Transactional history of edits

```text
Installation zone/measure drag -> CanvasGridMixin
Routing-area drag            -> EditorInteractionsMixin
Ctrl-left paint              -> CanvasGridMixin (Layout, Stringing)
Ctrl-right erase             -> CanvasGridMixin / DiagramEditorMixin release
Complete routing/path add/del-> PathsToolsMixin
                -> SafeProjectMixin._begin_canvas_edit(owner)
                -> application.edit_transactions.EditTransactionGate (Tk-free)
                -> edits through existing domain/legacy commands
                -> SafeProjectMixin._finish_canvas_edit(owner)
                -> one before/after snapshot, no intermediate polling records
```

The underlying `application.undo_redo` payload and schema-v2 JSON are not
modified. `DiagramEditorMixin` and `MountingMixin` retain their specialized
history transactions. See `docs/PHASE9_EDIT_TRANSACTIONS.md` and the phase-9
Tk GUI regression harness. The effective MRO has **53 name collisions**, the
same as phase 8; no methods were discarded merely because of their names.

## Phase 8 - Installation and Cabling domain commands

```text
Installation zone move / resize / creation
  -> CanvasGridMixin (canvas events, widget updates)
  -> domain.installation_edits (absolute geometry changes; Tk-free)
  -> commit only geometry fields to selected project zone(s)
  -> _recalculate_zone_grids() at edit boundary, not during paint

Installation polygon/marker and Cabling path clicks
  -> CanvasGridMixin (generic mouse dispatch)
  -> PathsToolsMixin._handle_path_canvas_press / _handle_path_canvas_right_press
  -> domain.cabling_edits (finite points, valid polygons, path creation)
  -> existing local JSON persistence / cable route invalidation

Installation polygon drag
  -> EditorInteractionsMixin -> MoveRoutingArea (unchanged)
```

The base canvas' shadowed polygon-drag mutation branch is removed. Physical
mounting positions, clamp geometry and all exports are unaffected. The count
of colliding names remains **53**, with four live left-gesture owners. Phase 8
adds 16 unit tests and a live edit/persistence GUI harness. Full gesture
ownership and legacy constraints are documented in
`docs/PHASE8_CANVAS_COMMAND_BOUNDARIES.md`.

## Phase 7 - Canvas gesture consolidation

```text
Wheel / middle-button pan
  -> UnifiedNavigationMixin (sole canvas bindings)

Left press / drag / release
  -> MountingMixin                     [mounting editing]
  -> DiagramEditorMixin                [diagram selection and commands]
  -> EditorInteractionsMixin           [Installation routing commands]
  -> CanvasGridMixin                   [Installation/Layout/Cabling editing]

Installation hit test (read-only)
  -> ui.gesture_hit_testing.zone_at_point / zone_resize_handle /
     dimension_label_at
  -> CanvasGridMixin applies selection/drag state after hit test

Diagram edit
  -> DiagramEditorMixin / domain.diagram_commands (copy-on-write + Undo/Redo)
  -> CanvasGridMixin handles link mode ONLY
```

The three passthrough `WorkspaceImprovementsMixin.on_left_*` wrappers have
been removed. Event chains are now **4** implementations rather than 5.
The masked base diagram movement branch which directly modified `diagram_nodes`
has been removed. The UI code now uses `TabId` constants in the migrated
`CanvasGridMixin` click/drag handlers. **53** method-name collisions remain
in the complete MRO; reducing a chain from 5 to 4 does not remove the name
from the collision inventory. See `docs/PHASE7_GESTURE_OWNERSHIP.md` and the
regenerated `docs/MRO_OWNERSHIP.csv`.

## Phase 6 - Zone grid input/paint separation

```text
Edit zone / change panel size or gap / click in Layout
  -> InstallationGeometryMixin._recalculate_zone_grids()
  -> domain.zone_grid_state.zone_grid_signature()   [read-only]
  -> geometry_layout.grid_spec()                    [only when changed]
  -> zone_registry.allocate_ranges()               [only when changed]
  -> domain.layout_remap.remap_zone_state()         [only if a zone range moves]
  -> committed roof_zones, panel/string identities and row allocations

Explicit save / load / tab change / explicit history record
  -> SafeProjectMixin._reconcile_project_state(prepare_zone_grids=True)
  -> zone grid reconciliation, then UID/shadow/electrical consistency

Passive 600ms history polling
  -> _record_history(prepare_zone_grids=False)
  -> snapshot changes, but NEVER recalculates zone allocations

CanvasGridMixin.draw_grid(), ShadowGeometryMixin._panel_rect()
  -> consume the most recently committed zone rows and offsets
  -> NO zone-grid calculations or row remaps during drawing
```

The former `ZoneToolsMixin._recalculate_zone_grids` implementation was
unreachable and has been deleted (66 lines). The active method is owned by
`InstallationGeometryMixin` only. **53** colliding names remain after phase 6.
Three `draw_grid()` overrides remain, in `SafeProjectMixin`, `MountingMixin`
and `CanvasGridMixin`. The UI/viewport renderer is still not wholly pure; its
**zone-grid allocation and panel geometry-query paths** are now read-only.

## Phase 5 - authoritative state and paint boundaries

```text
Legacy Layout edit (generate / Ctrl-click add / delete)
    -> _reconcile_project_state()     [UIDs / shadow cache / wiring projection]
    -> draw_grid()                    [canvas scene; no above domain changes]

Legacy indirect edit (still not migrated)
    -> _record_history()             [300ms event queue / 600ms safeguard]
    -> _reconcile_project_state()     [once per model signature change]

Save / autosave / project load
    -> _reconcile_project_state()     [before serialized snapshot or paint]
    -> unchanged schema-v2 repository and diagram

Switch tab (e.g. Mounting or single-line)
    -> _reconcile_project_state()     [before renderer consumes the data]
    -> _prepare_diagram_layout()      [only single-line]
    -> normal tab render
```

The reconciliation algorithm is in `domain/reconciliation_plan.py` and the Tk project integration in `mixins/safe_project.py`. The diagram projection implementation remains in `application/diagram_projection.py`; explicit electrical events introduced earlier still run without a canvas drawing. `CanvasGridMixin` now owns the previously duplicated polygon-edit handles. MRO draw chain: `SafeProjectMixin -> MountingMixin -> CanvasGridMixin`; **54** colliding method *names* remain, not 54 bugs.

**The renderer is not globally pure yet**: viewport state and certain zone recalculations remain coupled. Do not delete a mixin/override solely because its method name occurs several times. See `docs/MRO_OWNERSHIP.csv` for effective resolution order and `REFONTE_ETAT.md` for outstanding migrations.

## User-facing tabs and stable IDs

| Stable ID | Value | Legacy Tk attribute | Core subsystem |
|---|---:|---|---|
| `HOME` | 0 | `tab_file` | project lifecycle, files |
| `INSTALLATION` | 1 | `tab_roof` | scale, roof imagery and routing polygons |
| `LAYOUT` | 2 | `tab_layout` | zones, physical module placement |
| `STRINGING` | 3 | `tab_stringing` | strings and module mapping |
| `MPPT` | 4 | `tab_equipment` | inverter & MPPT assignment |
| `SHADOW` | 5 | `tab_shadow` | shadows, sunlight |
| `SPREADSHEET` | 6 | `tab_material` | materials spreadsheet |
| `SINGLE_LINE` | 7 | `tab_diagram` | electrical diagram |
| `CABLING` | 8 | `tab_notes` | cable routes, 3D plans and notes |
| `ENERGY` | 9 | `tab_energy` | annual energy, BESS |
| `MOUNTING` | 10 | `tab_mounting` | clamps, dimensions, BOM and A3 PDFs |

IDs are intentionally identical to the prior numeric indices. Some legacy mixins still use numeric indexes; migrate them only with a full end-to-end event test.

## Actual commands and data flow implemented

### Open

```text
SafeProjectMixin._load_project_file(filepath)
 -> ProjectRepository.read(filepath)
 -> validate_project(json) [schema-v2 + legacy normalization]
 -> ProjectDocument (defensive copy, unknown keys retained)
 -> SafeProjectMixin._apply_document(snapshot)
 -> ProjectIOMixin._load_project_file(...)  [legacy Tk state]
```

### Save / autosave

```text
ProjectIOMixin._collect_project_data()     [legacy: still UI-coupled]
 -> ProjectDocument(raw)
 -> ProjectRepository.write(path, document, image, recovery)
 -> project_store.write_project()          [atomic JSON + image + .backups]
 -> verify_routing_geometry()             [roof_polygons, offsets, cable_paths]

silent autosave: independent .recovery/ copy, then active project only if dirty.
```

### Move a cable routing polygon

```text
EditorInteractionsMixin.on_left_drag(event)
 -> MoveRoutingArea(index, original_points, dx_px, dy_px, vertex)
 -> update_routing_area() -> valid_polygon()
 -> new polygon list, or reject invalid geometry without mutation
 -> RoutingAreaChanged(index) on EventBus
 -> SafeProjectMixin._on_domain_event(): invalidate cable routing cache, queue undo
 -> existing draw_grid()                  [unchanged legacy presentation]
```

### Zoom / pan and undo

- `UnifiedNavigationMixin` is still the sole installed wheel / middle-pan binding on the shared drawing canvas; names are now semantic `TabId`s.
- `_record_history` creates a normalized payload via `application.undo_redo` but only domain changes / a different background image produce new entries; zoom-only changes do not fork redo.
- An updated view continues to be stored alongside **edits**, to restore a useful camera on undo/redo.
- `SafeProjectMixin.draw_grid` no longer queues an unconditional undo operation. Panel IDs are reconciled only when the coordinate sets differ.

## PDF and independent calculations (unchanged)

- `mounting.py`, `mounting_edges.py`, `mounting_spacing.py`, `mounting_quantities.py`, `mounting_joint_gap.py`: mounting dimensions, shared physical clamps and BOM.
- `mounting_drawing.py`: vector scene objects / geometry; `mounting_plan_pdf.py`: one-page A3 vector installation plan; `mounting_installer.py`: multi-page installation package.
- `engineering_report.py`, `report_mounting.py`, `report_plans.py`, `report_studies.py`: engineering report, separate from the installation plans; no LaTeX export.
- `geometry_layout.py`, `zone_registry.py`: panel layout calculation and stable row/zone IDs.
- `energy_engine.py`, `self_consumption.py`, `battery_dispatch.py`, `shadow_engine.py`, `detailed_electrical.py`, `single_line_516.py`: independent numerical engines.
- `view_navigation.py`: viewport transforms and zoom anchored under pointer, consumed by the current Tk adapter.
- `application/diagram_projection.py`: pure defensive electrical wiring graph projection, used before rendering when topology changes.
- `domain/layout_remap.py`: pure coordinate remapping of layout row ranges, string membership and stable module identities.

## Current refactor boundary / remaining work

1. **DONE:** retained baseline, 114 unit tests, live GUI navigation + mounting + installation + project roundtrip on Frimo 533; README documents no EXE build scripts.
2. **DONE / first vertical slice:** defensive `ProjectDocument`, `ProjectRepository`, domain routing transform, command/event adapter, initial undo decoupling, stable named `TabId`, routing metadata preservation.
3. **PARTIAL, PHASE 2:** `SafeProjectMixin._prepare_canvas_model` now explicitly prepares shadow provenance, stable panel UIDs and the diagram. `ProjectIntegrityMixin.draw_grid` was removed; its synchronization code is now `_synchronize_diagram_projection` backed by an isolated pure `application/diagram_projection.py` function. Rendering still invokes this preflight for behavioural compatibility: **not yet a pure renderer**.
4. **PARTIAL, PHASE 2:** `ui/tab_ids.py` is used in the unified navigation and polygon editor. Wheel/middle-pan bindings are now installed only once by UnifiedNavigationMixin; old legacy handler methods are retained for backward compatibility. Other MRO input dispatch remains unchanged.
5. **DONE, proof of unreachable code:** deleted `UIBuildersMixin._build_root_scroller` and its two callbacks, the unused `DiagramToolsMixin._draw_diagram`, and the unreachable `ProjectWorkspaceMixin._export_engineering_report`. The active implementations remain in `ResponsiveUIMixin`, `DiagramEditorMixin` and `SafeProjectMixin`. Verified 11-tab startup and navigation.
6. **STARTED, PHASE 2:** `domain/layout_remap.py` now owns pure row-address transformations for panel maps, UIDs, diagram layout geometry, selection and strings; `InstallationGeometryMixin` adapts them to UI state. The full `LayoutEngine`, gesture router, command-based history for all tabs and mounting editor extraction are still pending.
7. **NOT DONE:** extract electrical/shadow/BESS/spreadsheet controllers fully, unify only common PDF primitives, and remove the remaining method collisions after domain parity tests.
8. **NOT DONE:** full Windows/GitHub EXE integration testing (build remains deliberately user-owned).

**Verified MRO metrics after phase 2:** 38 classes including app+object; **55 duplicate method-name groups** (unchanged vs phase 1; 58 at baseline). `draw_grid` chain shortened from 5 to 4 implementations. The tracked report is `docs/MRO_OWNERSHIP.csv`, generated by `tools/report_mro.py`. The remaining groups must not be removed en masse because of their explicit `super()` chains and hidden persistence dependencies. See `AUDIT_ARCHITECTURE.md` for the original baseline / twelve-stage plan.

## Tests

```bash
python -m unittest discover -s tests -q
python tools/test_architecture_gui.py                     # desktop display required
python tools/test_project_roundtrip_gui.py /path/to/site.json
```

Under Linux CI, run GUI scripts through `xvfb-run -a ...`. Full regression scripts in `tools/` include mounting A/B/C, intermediate clamp gaps, live dimensions, SVG/CSV legacy utilities and the A3 vector PDF. Do not package these tests or project fixtures into an EXE.

## Phase 3 - compléments à la codemap (23/10/2026)

```text
Stringing UI / MPPT UI / layout modification
 -> domain/string_commands.py (copy-on-write, pour les edits manuels)
 -> ProjectIntegrityMixin._notify_wiring_change(source)
 -> application.events.ElectricalTopologyChanged
 -> SafeProjectMixin._on_domain_event(event)
 -> ProjectIntegrityMixin._synchronize_diagram_projection()
 -> application/diagram_projection.py (calcul defensif, signatures)
 -> diagram_nodes + diagram_links, puis mise a jour des widgets
```

La projection se produit désormais sur les edits instrumentés, meme lorsque la methode d'affichage est temporairement neutralisee. Un fallback legacy demeure dans `SafeProjectMixin._prepare_canvas_model` **pour les chemins non encore migres**. Ce fallback reste un effet de bord du dessin et ne doit pas etre retire avant phase 4. Un rechargement de projet passe egalement par une reconciliation explicite.

```text
Left click/drag, shared canvas
 -> MountingMixin (Mounting)
 -> DiagramEditorMixin (Single-line diagram)
 -> EditorInteractionsMixin + ui/gesture_policy.py (Installation polygons)
 -> CanvasGridMixin (remaining non-installation tools)
Wheel / middle-button pan
 -> UnifiedNavigationMixin (one shared binding)
```

Les anciennes branches diagramme dans `EditorInteractionsMixin` ont ete retirees car `DiagramEditorMixin` les interceptait systematiquement avant elles dans le MRO. Les fonctions `_on_diagram_list_select` et `_delete_selected_diagram_node` de ce mixin restent **actives** et sont conservees.

**Mesures actualisees :** 123 tests unitaires, 55 groupes de methodes redéfinis (idem phase 2), 4 definitions de `draw_grid`. Voir `docs/MRO_OWNERSHIP.csv` et `REFONTE_ETAT.md` pour le statut exact et la liste des controles.

## Phase 4 - Single-line editing and paint-boundary isolation (23 October 2026)

```text
Single-line diagram user action
  -> domain/diagram_commands.py       (no Tkinter)
     add_custom_node / add_manual_link / delete_nodes
     move_nodes / position_nodes
  -> DiagramEditorMixin._apply_diagram_edit(edit)
  -> SafeProjectMixin._record_history()   (before + after one user edit)
  -> diagram_nodes / diagram_links
  -> existing draw_grid()                (presentation only for diagram primitives)

Mouse drag on selected diagram blocks
  -> DiagramEditorMixin._begin_diagram_gesture(): baseline history
  -> _preview_diagram_move(originals, dx, dy): absolute-delta copy-on-write
  -> _finish_diagram_gesture(): one history commit
  -> SafeProjectMixin._record_history() skips intermediate gesture frames

Canvas drawing
  -> SafeProjectMixin._prepare_canvas_model()
  -> ProjectIntegrityMixin._synchronize_diagram_projection() [legacy fallback]
  -> DiagramEditorMixin._prepare_diagram_layout() [on SINGLE_LINE tab]
  -> CanvasGridMixin.draw_grid()
  -> DiagramEditorMixin._draw_diagram()   [does not mutate nodes]
```

- Removed the masked `DiagramToolsMixin._delete_selected_diagram_node`; the actual implementation lives in `EditorInteractionsMixin` and delegates to `domain.diagram_commands.delete_nodes`.
- The effective `DiagramEditorMixin` owns grouped drag history, logical diagram reflow and auto-generate history boundaries. The UI keeps its existing gesture semantics and custom link data, including distance and style.
- The automatic collision layout is computed in the pre-render preparation step, **not** while emitting diagram canvas primitives. The project-wide `draw_grid` boundary remains **partially mutating** for non-migrated legacy paths (panel UID reconciliation, wiring projection and shadow invalidation).
- `docs/MRO_OWNERSHIP.csv` regenerated: **54** duplicate method-name groups (previously 55); `draw_grid` still has four implementations (do not delete this chain without tracing `super()`).
- Tests: **130 unit tests**, `tools/test_phase4_diagram_gui.py` tests create/link/drag/delete/undo/redo/save/load/zoom/read-only paint. Previous GUI, installation, Frimo-533 and mounting PDF tests retained.
- JSON schema remains **v2**, with the same saved keys and no server or build files. User-authored node/link metadata is not silently discarded by domain commands.

### Still pending

1. Eliminate `SafeProjectMixin._prepare_canvas_model()`'s wiring-sync fallback **only after every indirect model edit is routed through commands/events**.
2. Migrate diagram automatic generation and all direct drag handlers to a single central CommandBus, then decouple the generic history polling.
3. Extract other tab paint-time mutations and complete an explicit gesture ownership model for Layout, Shadow and Cabling; retain shared middle-button pan and cursor-centered wheel zoom.
4. Consolidate the remaining 54 MRO name collisions only as their specific superclass chains are tested.
5. Full Windows EXE verification remains with the user's GitHub build workflow.
