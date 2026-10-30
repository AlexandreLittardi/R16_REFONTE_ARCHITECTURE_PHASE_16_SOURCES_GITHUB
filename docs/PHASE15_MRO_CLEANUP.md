# Phase 15 - Remove proven-dead MRO overrides

Date: 26 October 2026. Source baseline: phase 14. All eleven English-language tabs,
local schema-v2 JSON, mounting A/B/C and native vector PDF generation are unchanged.
This is a **targeted dead-code deletion**, not a wholesale mixin rewrite.

## Proof of unreachability

For each deleted definition:

1. In the actual `app.PVLayoutRibbonApp.__mro__`, a higher-priority method with
   the **same name** handles every `self.method(...)` dispatch.
2. The controlling implementation does **not** invoke `super()` to reach the
   deleted definition. For `_build_tab_file_tools` and
   `_build_tab_layout_tools`, the chain *does* call `super()` but terminates
   in `WorkspaceImprovementsMixin`, **before** reaching `UIBuildersMixin`.
3. The source tree contained no explicit calls of the form
   `RemovedMixin.method(self, ...)` to these deleted implementations.
4. The live owner and absence of each deleted definition are enforced by
   `tests/test_phase15_shadowed_cleanup.py`.
5. Existing application and Tkinter regression tests were rerun.

These guarantees apply to the present application MRO. A future standalone use
of one of the older mixins would need its own contract and implementation.

## What was removed

See `docs/PHASE15_REMOVED_OVERRIDES.csv` for all fourteen source locations,
original definition lengths, and the live owners.

- Three obsolete diagram sizing/selection handlers in `DiagramToolsMixin`.
  The active handlers in `DiagramEditorMixin` / `EditorInteractionsMixin` remain.
- Three older zone geometry/generation/deletion handlers in `ZoneToolsMixin`.
  The active `InstallationGeometryMixin` implementation remains; crucially,
  this does **not** replace zone-centred rotation with the old per-cell rotation.
- Two legacy cable-routing computations in `CableNetworkMixin`.
  The active `TwoPoleCablesMixin` implementation remains.
- The unused older energy-workspace builder in `WorkspaceImprovementsMixin`.
- Three unused `UIBuildersMixin` methods: the old help pop-up, and early file
  and layout toolbar builders (the live toolbar chain ends earlier).
- Two superseded weather download/import methods in `SelfConsumptionMixin`.
  The active `SafeProjectMixin` versions remain.

**Result:** 14 method definitions and 359 lines of their bodies removed.
Method-name collisions go **53 -> 41**. The two old toolbar methods were one
member each of a chain with multiple remaining owners, hence deleting them
shortens the chains but does not eliminate those collision *names*.

## Executed validation

- `python -m unittest discover -s tests -q`: **225 tests pass** (223 phase-14 baseline).
- Tkinter GUI tests: 11 tabs and unified navigation, diagram create/link/move,
  Installation zone edits, Cabling areas, phases 9-14 transactions, MPPT drop,
  spreadsheet edits, Mounting PDF A3 and mounting A/B/C.
- Full GUI Mounting stress test: **500 panels**, native zoom and 21-page
  vector engineering report.
- Real Frimo project load -> save -> reload: **533 panels, 9 roof zones,
  2 cable routing areas, 32 strings** (project is not included in this ZIP).
- `python tools/report_mro.py > docs/MRO_OWNERSHIP.csv` regenerates the
  **41 remaining** duplicate method-name inventory.

## Explicit remaining work

- The 41 colliding names are **not** necessarily dead: `draw_grid`, notebook
  switches, and canvas events have cooperative `super()` chains.
- `SafeProjectMixin._poll_history` remains as a compatibility safety net for
  legacy mutation paths. Removing it requires tracing every remaining edit
  action with dedicated before/after Undo/Redo tests; it was **not** removed
  here.
- No project JSON migration, formula changes, image processing changes,
  mounting calculation changes, EXE build, `.spec` or GitHub Actions workflow.
