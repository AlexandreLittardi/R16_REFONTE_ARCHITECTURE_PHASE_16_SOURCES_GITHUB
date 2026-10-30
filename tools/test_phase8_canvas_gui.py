"""Live Installation/Cabling edit regression after domain extraction."""
import copy
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from infrastructure.json_repository import ProjectRepository


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(directory) / 'recent.json')
        root = tk.Tk()
        root.geometry('1320x860')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            app.ribbon_notebook.select(app.tab_roof)
            root.update()
            app._auto_fit = False
            app.zoom_level = 1.
            app.px_per_mm = 2.
            app.path_mode = 'select'
            app.roof_mode = 'select'
            app.roof_zones = [dict(id=1, x1=80., y1=90., x2=350., y2=330.,
                                   w_mm=135., h_mm=120., align_x='Centre', align_y='Centre',
                                   custom_metadata={'installer': 'retain'}),
                              dict(id=2, x1=420., y1=110., x2=640., y2=290.,
                                   w_mm=110., h_mm=90., align_x='Centre', align_y='Centre')]
            app.draw_grid()
            root.update()

            def ev(cx, cy, state=0):
                return SimpleNamespace(
                    x=cx-app.canvas.canvasx(0),
                    y=cy-app.canvas.canvasy(0), state=state)

            # Move two zones in a single Ctrl/Shift selection, verify IDs and
            # custom project metadata survive, not just rectangle coordinates.
            app.on_left_press(ev(200, 210, 0x0004))
            app.on_left_release(ev(200, 210, 0x0004))
            app.on_left_press(ev(500, 200, 0x0005))
            app.on_left_release(ev(500, 200, 0x0005))
            assert app.selected_zone_indices == {0, 1}, app.selected_zone_indices
            app.on_left_press(ev(200, 210, 0x0004))
            app.on_left_drag(ev(216, 224, 0x0004))
            app.on_left_release(ev(216, 224, 0x0004))
            assert app.roof_zones[0]['x1'] == 96., app.roof_zones
            assert app.roof_zones[1]['x1'] == 436., app.roof_zones
            assert app.roof_zones[0]['custom_metadata'] == {'installer': 'retain'}

            app.selected_zone_indices = {0}
            app.active_zone_idx = 0
            app.roof_mode = 'select'
            app.on_left_press(ev(96, 104))
            assert app.zone_drag_mode == 'resize_tl', app.zone_drag_mode
            app.on_left_drag(ev(110, 120))
            app.on_left_release(ev(110, 120))
            assert app.roof_zones[0]['x1'] == 110, app.roof_zones[0]
            assert app.roof_zones[0]['y1'] == 120, app.roof_zones[0]
            assert app.roof_zones[0]['w_mm'] == 128, app.roof_zones[0]

            # Installation polygon vertices are handled by PathsTools and
            # use the existing routing-area validation and persisted schema.
            app.roof_mode = 'select'
            app.path_mode = 'draw_polygon'
            app.temp_polygon_points = []
            for x, y in ((700, 130), (830, 130), (830, 230), (700, 230)):
                app.on_left_press(ev(x, y))
            app.on_right_press(ev(700, 230))
            assert app.roof_polygons[-1]['points'] == [
                (700., 130.), (830., 130.), (830., 230.), (700., 230.)]
            assert app.path_mode == 'select'

            # Cabling path belongs to Cabling tab and is independent of zone
            # hit testing, panel selection and camera gestures.
            app.ribbon_notebook.select(app.tab_notes)
            root.update()
            app._auto_fit = False
            app.zoom_level = 1.
            app.path_mode = 'draw_cable_path'
            app.temp_cable_path_points = []
            for x, y in ((100, 350), (260, 360), (400, 390)):
                app.on_left_press(ev(x, y))
            app.on_right_press(ev(400, 390))
            assert app.cable_paths[-1]['points'] == [
                (100., 350.), (260., 360.), (400., 390.)], app.cable_paths
            assert app.path_mode == 'select'

            document = app._collect_project_data()
            target = Path(directory) / 'phase8.json'
            repo = ProjectRepository()
            repo.write(target, document)
            loaded = repo.read(target).snapshot()
            assert loaded['roof_zones'][0]['custom_metadata'] == {'installer': 'retain'}
            assert len(loaded['roof_polygons']) == len(app.roof_polygons)
            assert len(loaded['cable_paths']) == len(app.cable_paths)
            assert len(app.ribbon_notebook.tabs()) == 11
            assert not errors, [str(e) for e in errors]
            print('PASS phase8 GUI: multi-zone move, resize, routing polygon, cabling path, JSON')
        finally:
            root.destroy()


if __name__ == '__main__':
    main()
