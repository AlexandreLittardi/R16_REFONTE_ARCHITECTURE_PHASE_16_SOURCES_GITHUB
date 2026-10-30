# Phase 9 - History transactions across Installation, Layout and Cabling

## Design

Phase 9 introduces a small framework-independent `application/edit_transactions.py`
`EditTransactionGate`, integrated in `SafeProjectMixin` via
`_begin_canvas_edit(owner)` and `_finish_canvas_edit(owner=None)`.

```text
User gesture (press)
   -> _record_history(prepare_zone_grids=False)  [before, once]
   -> EditTransactionGate.begin(owner)
   -> multiple drag/paint frames: no additional history records
   -> underlying domain edit commands (phase 8)
User gesture (release)
   -> EditTransactionGate.finish(owner)
   -> _record_history(prepare_zone_grids=False)  [after, once]
   -> built-in equality check omits unchanged/no-op gestures
```

The gate does not hold project objects and has no Tk dependency. The editor
still uses the established 100-snapshot Undo/Redo format, view metadata, image
identity, schema-v2 persistence and `make_history_payload`. A new undo format
or JSON field is NOT introduced.

## Migrated interactions

- **Installation**: selected-zone translation (one or multiple zones), corner
  resize and dimension-label drag. The press captures the original state, the
  release closes the transaction, even when the legacy release handler exits
  early. Clicking without moving makes no additional snapshot.
- **Cable routing areas**: whole-polygon and vertex drags remain owned by
  `EditorInteractionsMixin -> MoveRoutingArea`, with history now coalesced
  across all mouse-motion frames. Invalid motions are still rejected.
- **Layout and Stringing Ctrl-left brush**: painting multiple cells makes
  one Undo/Redo step. **Ctrl-right brush** deletion commits on right release,
  through the existing `DiagramEditorMixin` event owner.
- **Cabling**: creation/deletion of complete cable routes and routing polygons
  is immediately undoable as one discrete edit, without waiting for the
  global 300/600 ms fallback history timer.

## Why the press snapshot does not validate zone grids

Pressing/selecting a zone is a *read-only* gesture until it actually moves.
The phase-6 grid calculation boundary must not allocate zone rows during a
mere click. The two explicit snapshots use
`_record_history(prepare_zone_grids=False)`. Existing zone drag and layout
commands still calculate and reconcile their data at their edit boundary;
commit logic in save/load/tab-switch remains intact.

## Legacy compatibility and exclusions

The diagram editor retains its own `_begin_diagram_gesture` and
`_finish_diagram_gesture`. Mounting retains its clamp-specific drag history
logic. Other edit actions continue to use the project-wide periodic fallback.
The gate is **not** a universal command bus and cannot be used to delete the
remaining mixin owners without additional tests. No mouse gesture bindings
are changed, no application tab reordered, no new dependencies installed.

## Tests executed

```sh
python -m unittest discover -s tests -q
xvfb-run -a python tools/test_phase9_transactions_gui.py
xvfb-run -a python tools/test_phase8_canvas_gui.py
xvfb-run -a python tools/test_phase7_gesture_gui.py
xvfb-run -a python tools/test_project_roundtrip_gui.py '/path/to/frimo-project.json'
xvfb-run -a python tools/test_mounting_gui.py
```

The phase-9 GUI harness verifies no-op gestures, intermediate poll suppression,
zone and polygon Undo/Redo, physical cable path creation/deletion Undo/Redo,
Ctrl-left addition and Ctrl-right removal of multiple modules in one history
step. A Frimo JSON containing 533 panels, 9 zones, 2 routing areas and
32 strings was loaded/saved/reloaded without changes in these counts.

## Remaining work

- Continue to migrate commands invoked by ribbon buttons and dialogs to
  explicit transactions; periodic fallback cannot yet be removed.
- Shared transaction commands should ultimately move into a project-document
  controller (one mutation authority), leaving GUI widgets as adapters.
- Do not conflate MRO collisions with dead code. This phase removes none:
  **53 colliding method names** remain, with the same event owners.
