# Phase 14 - Photograph registration and calibration transactions

## Scope

This phase continues from phase 13 without changing schema-v2 JSON or engineering
formulae. It covers **Installation Area** image registration, scale calibration,
and user-created dimensions. Surveyed roof geometry stays in original-image pixel
coordinates; shifting a photograph never moves panel or zone geometry.

| User action | Owner | Undo/Redo boundary | Cancel / no-op |
| --- | --- | --- | --- |
| Import or replace photograph | `ZoneToolsMixin.load_roof_image` | one `installation:import-photo` command after the chooser returns | file chooser cancelled: no history |
| Move photograph | `CanvasGridMixin.on_left_press/drag/release` | one `installation:photo-offset` gate from press to release | click without movement: no history |
| Exit move mode mid-gesture | `ZoneToolsMixin._stop_background_move_tool` | closes a pending photo move gate | no edit: no history |
| Reset photograph position | `ZoneToolsMixin._reset_background_position` | one `installation:reset-photo` command | offset already zero: no history |
| Scale reference segment | `CanvasGridMixin.on_left_release` | one `installation:calibration` command after valid input | cancelled/short segment: no history |
| Align replacement photograph | `_apply_scale_reference` | one calibration step; preserves existing project scale | validation errors raised before modification |
| Add / remove dimension | canvas mouse handlers | one edit transaction per operation | gestures below minimum length: no history |
| Move dimension label | canvas mouse press/release | one `installation:dimension-label` gate | click without movement: no history |
| Clear dimensions | `ZoneToolsMixin.clear_measures` | one `installation:clear-measures` command | already empty: no history |

## Implementation

- `domain/roof_registration.py` has pure `shifted_photo_offset`,
  `calibrated_scale`, and `replacement_scale_factor` helpers; no Tk import.
- Only photo offset changes on a photo drag. The raster is still moved by the
  existing canvas renderer, and the final release redraw updates scroll extents.
- New dimensions store `axis` at creation. This avoids a normalization-induced
  history mismatch during Redo (loaded measure dictionaries always carry axis).
- History retains the original in-memory PIL image per record; the JSON writer
  and image-asset path resolution are unchanged.
- Automatic `_poll_history` remains a safety net for **other** un-migrated UI
  mutations. It is suppressed while a photo or label pointer transaction is open.

## Validation

```sh
python -m unittest discover -s tests -q
xvfb-run -a python tools/test_phase14_roof_history_gui.py
xvfb-run -a python tools/test_installation_gui.py
xvfb-run -a python tools/test_mounting_pdf_gui.py
xvfb-run -a python tools/test_project_roundtrip_gui.py /path/to/existing_project.json
```

Unit coverage: cancellation/invalid reference inputs, screen-to-image
coordinates, preservation of survey scale, image replacement factors.
Tk coverage: image import and replacement, zoom-independent move, reset,
calibration, alignment of a replacement photo, dimension creation and label
movement, exact Undo/Redo boundaries, cancelled dialog, JSON read-back.

No `.spec`, EXE, installer, build workflow or generated binaries are shipped.
