# Phase 8 - Installation and Cabling edit command boundaries

## Effective ownership

```text
Tk button 1 / button 3
  -> MountingMixin                  specialized mounting interactions
  -> DiagramEditorMixin            electrical diagram commands + Undo/Redo
  -> EditorInteractionsMixin       routing-area drag via MoveRoutingArea
  -> CanvasGridMixin               Layout + zone selection/drag + generic dispatch
         -> PathsToolsMixin._handle_path_canvas_press / _handle_path_canvas_right_press
              -> domain.cabling_edits (point append, finish polygon/path)
         -> domain.installation_edits (zone translation, corner resize, new zone)
```

- `CanvasGridMixin` delegates Installation polygon, distance-marker and Cabling path-click/right-click handling to the single path owner, `PathsToolsMixin`. Only that owner decides whether a path gesture is consumed.
- Zone-selection and scale calibration remain in `CanvasGridMixin`. Pure drag calculations use the *original snapshot* and return field patches, applied only to the selected zone dicts. Unknown metadata keys are never replaced by geometric patches.
- Polygon vertex/move gestures remain in `EditorInteractionsMixin` using `application.routing_commands.MoveRoutingArea`, not the now-removed direct-mutation fallback in `CanvasGridMixin`.
- Polygons and cable paths are built by `domain.cabling_edits`, maintaining prior id allocation, point coordinates and existing JSON keys. The project's stored dimensions, panel positions and clamps are unchanged.

## Coordinate and model contracts

- UI mouse positions are in Tk canvas pixels; command calculations use original image pixels. The widget layer divides by `zoom_level` before invoking geometry.
- Minimum zone resize size is **15 screen pixels** / zoom, unchanged from phase 7.
- `w_mm` and `h_mm` are recomputed from `px_per_mm` only when positive; without a scale, existing physical dimension fields remain unchanged during resize.
- A multi-zone move applies absolute displacement relative to the saved start-of-drag rectangles, never incremental motion from the previous frame.
- Incoming `roof_zones` entries can have arbitrary metadata; the domain returns only fields being changed. `roof_polygons` and `cable_paths` remain lists of `{id, points, ...}` entries for schema-v2 JSON.
- Invalid/degenerate polygons are not committed. Cable paths require two finite vertices; temporary points must have finite numeric image coordinates.

## Explicitly not migrated

- Scale calibration, roof image repositioning, physical cable route computation and automatic gathering-point placement are still in existing UI/service methods.
- The 53 colliding method-name groups are still present. Splitting pure commands from callbacks does not imply deleting active mixin overrides.
- The project-level Undo/Redo transaction bus is not yet unified; edits still use the existing snapshot mechanism outside the Diagram editor. There is no Windows build support in this archive.

## Tests and reproduction

```sh
python -m unittest discover -s tests -q
xvfb-run -a python tools/test_phase8_canvas_gui.py
xvfb-run -a python tools/test_unified_navigation_gui.py
xvfb-run -a python tools/test_mounting_pdf_gui.py
xvfb-run -a python tools/test_project_roundtrip_gui.py '/path/to/project.json'
python tools/report_mro.py > docs/MRO_OWNERSHIP.csv
```

The phase 8 GUI test covers multi-zone Ctrl/Shift move, zone resize in physical mm, polygon creation, Cabling path creation and JSON roundtrip with custom metadata. No user project data is included.
