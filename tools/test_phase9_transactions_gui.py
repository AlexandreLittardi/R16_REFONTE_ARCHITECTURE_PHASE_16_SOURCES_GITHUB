"""History transaction parity: zone, routing polygon and cable path edits."""
import copy
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(directory) / 'recent.json')
        root = tk.Tk()
        root.geometry('1300x850')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            app.ribbon_notebook.select(app.tab_roof)
            root.update()
            app._auto_fit = False
            app.zoom_level = 1.0
            app.px_per_mm = 2.0
            app.path_mode = 'select'
            app.roof_mode = 'select'
            app.roof_zones = [dict(id=1, x1=80., y1=90., x2=380., y2=340.,
                                   w_mm=150., h_mm=125., align_x='Centre',
                                   align_y='Centre', metadata={'retain': 1})]
            app._record_history()
            app.draw_grid()
            root.update()

            def ev(cx, cy, state=0):
                return SimpleNamespace(x=cx-app.canvas.canvasx(0),
                                       y=cy-app.canvas.canvasy(0), state=state)

            # Selection click, zero-distance drag: no snapshot, no geometry mutation.
            start = app._history_index
            before = copy.deepcopy(app.roof_zones)
            app.on_left_press(ev(200, 200))
            app._poll_history()  # asynchronous polling must not split an edit
            app.on_left_release(ev(200, 200))
            assert app._history_index == start, (start, app._history_index)
            assert app.roof_zones == before

            # One physical zone drag with several intermediate frames: one edit.
            app.on_left_press(ev(200, 200))
            app.on_left_drag(ev(210, 207))
            app.on_left_drag(ev(220, 212))
            app._poll_history()
            assert app._history_index == start, 'Drag produced intermediate history'
            app.on_left_release(ev(220, 212))
            assert app._history_index == start + 1, (start, app._history_index)
            assert app.roof_zones[0]['x1'] == 100., app.roof_zones
            assert app.roof_zones[0]['metadata'] == {'retain': 1}
            app.undo_project()
            assert app.roof_zones[0]['x1'] == 80., app.roof_zones
            app.redo_project()
            assert app.roof_zones[0]['x1'] == 100., app.roof_zones

            # A no-op click over a routing polygon is a selection, not an edit.
            app.roof_polygons = [dict(id=1,points=[(450.,100.),(590.,100.),
                                                           (590.,240.),(450.,240.)],
                                      metadata={'cable': 'retain'})]
            app.active_polygon_idx = 0
            app.path_mode = 'select_polygon'
            app._record_history()
            start = app._history_index
            app.on_left_press(ev(500, 170))
            app.on_left_release(ev(500, 170))
            assert app._history_index == start
            app.on_left_press(ev(500, 170))
            app.on_left_drag(ev(540, 180))
            app.on_left_drag(ev(560, 195))
            assert app._history_index == start
            app.on_left_release(ev(560, 195))
            assert app._history_index == start + 1
            assert app.roof_polygons[0]['points'][0] == (510.,125.)
            app.undo_project()
            assert app.roof_polygons[0]['points'][0] == (450.,100.)
            app.redo_project()
            assert app.roof_polygons[0]['points'][0] == (510.,125.)
            assert app.roof_polygons[0]['metadata'] == {'cable': 'retain'}

            # Creating and deleting one cable path must each be immediately undoable.
            app.ribbon_notebook.select(app.tab_notes)
            root.update()
            app.path_mode = 'draw_cable_path'
            app.temp_cable_path_points = [(80.,500.), (150.,530.), (230.,570.)]
            app._record_history()
            start = app._history_index
            app._finish_cable_path_draw()
            assert app._history_index == start+1, 'Cable-path creation should be one edit'
            created_id = app.cable_paths[-1]['id']
            app.undo_project()
            assert not any(p['id'] == created_id for p in app.cable_paths)
            app.redo_project()
            assert any(p['id'] == created_id for p in app.cable_paths)
            app.active_cable_path_idx = len(app.cable_paths) - 1
            start = app._history_index
            app.delete_active_cable_path()
            assert app._history_index == start+1
            app.undo_project()
            assert any(p['id'] == created_id for p in app.cable_paths)

            # Ctrl+left/right strokes across multiple cells are atomic.
            app.roof_zones = [dict(id=1,x1=0.,y1=0.,x2=3500.,y2=3900.,
                                   w_mm=3500.,h_mm=3900.,align_x='Centre',align_y='Centre')]
            app.px_per_mm = 1.
            app.ribbon_notebook.select(app.tab_layout)
            root.update()
            app._record_history()
            start = app._history_index
            with patch.object(app, '_get_cell_coords', side_effect=[(0, 0), (0, 1)]):
                app.on_left_press(ev(200, 200, 0x0004))
                app.on_left_drag(ev(210, 205, 0x0004))
                app._poll_history()
                assert app._history_index == start
                app.on_left_release(ev(210, 205, 0x0004))
            assert app._history_index == start + 1
            assert (0,0) in app.panels and (0,1) in app.panels, app.panels
            app.undo_project()
            assert (0,0) not in app.panels and (0,1) not in app.panels
            app.redo_project()
            assert (0,0) in app.panels and (0,1) in app.panels
            app._record_history()  # flush any legacy post-restore derived state
            start = app._history_index
            with patch.object(app, '_get_cell_coords', side_effect=[(0, 0), (0, 1)]):
                app.on_right_press(ev(200, 200, 0x0004))
                app.on_right_drag(ev(210, 205, 0x0004))
                assert app._history_index == start
                app.on_right_release(ev(210, 205, 0x0004))
            assert app._history_index == start+1
            assert (0,0) not in app.panels and (0,1) not in app.panels
            app.undo_project()
            assert (0,0) in app.panels and (0,1) in app.panels

            assert len(app.ribbon_notebook.tabs()) == 11
            assert not errors, [str(e) for e in errors]
            print('PASS phase9: zone/routing drags, path creation/deletion and Layout Ctrl brush Undo/Redo')
        finally:
            root.destroy()


if __name__ == '__main__':
    main()
