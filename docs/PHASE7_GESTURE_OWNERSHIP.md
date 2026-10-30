# Phase 7: Shared canvas gesture ownership

## Actual mouse-button dispatch (method resolution order)

All primary clicks traverse these **four** mixin owners, in order:

1. `MountingMixin`: owns A/B/C mounting fixings, manual dimensions, panel selections. Other tabs call `super()`.
2. `DiagramEditorMixin`: owns diagram node selection and **copy-on-write** block moves, with one Undo/Redo transaction per gesture. Link creation delegates to base CanvasGrid.
3. `EditorInteractionsMixin`: owns Installation routing-area selection/vertex drag and moves (via `MoveRoutingArea`, application events), and Installation release handling. Other tabs call `super()`; left-button actions never activate a legacy pan.
4. `CanvasGridMixin`: owns remaining Installation scale/zone/dimension gestures, Layout selection, panel and zone edits, MPPT/inverter placement and Cabling path actions. Diagram link-mode clicks are the only remaining diagram input here.

Navigation is independent: `UnifiedNavigationMixin` owns wheel zoom (at pointer) and middle-drag pan. Left gestures do not pan the canvas.

The three `WorkspaceImprovementsMixin.on_left_*` methods were removed. The former press wrapper only set `_canvas_pan_start=None`; this remains in the editor delegation path, without an intermediate method owner. Drag/release wrappers did nothing but `super()`.

## Read-only hit tests

`ui/gesture_hit_testing.py` has three small, Tk-free functions:

- `zone_at_point`: match the first overlapping Installation zone, including reversed saved rectangles and zoom; same strict priority as the previous two duplicate loops.
- `zone_resize_handle`: identify the four zone corners using an **8 screen-pixel** threshold, not scaled geometric units.
- `dimension_label_at`: select the last/topmost dimension label, with the previous **58 x 15 screen-pixel** tolerances.

The drawing geometry and coordinate scale are unchanged. State changes remain in the mixin; hit testing does **not** change project records.

## Legacy diagram mutation removed

`CanvasGridMixin.on_left_press` no longer has a second implementation of normal diagram node selection and drag state. This branch is bypassed by `DiagramEditorMixin`, and could operate only if its dispatcher changed. `CanvasGridMixin.on_left_drag` no longer mutates diagram node coordinate dictionaries directly, which would have bypassed the phase-4 copy-on-write diagram commands and history.

Diagram links continue to be created through `domain.diagram_commands.add_manual_link`. Normal group moves remain exclusively in `DiagramEditorMixin`.

## What remains to migrate

- Installation and Cabling still combine mouse modes and model mutations in `CanvasGridMixin`; only the repeated, pure hit tests have been extracted here. Their full conversion to command objects requires scenario coverage for every mode, including scale calibration, image repositioning, path editing and Ctrl painting.
- `EditorInteractionsMixin` calls `CanvasGridMixin.on_left_*` directly for Installation to avoid legacy wrappers. A future extraction should provide an explicit Installation gesture handler instead, with a single routed entry point.
- Middle pan and wheel handlers are shared, but Mounting maintains its specialized vector-view transform for responsiveness.
- The application still has **53 colliding method names** in its overall inheritance tree, including intentional overrides; this phase makes three mouse-event *chains* shorter without changing this count.
