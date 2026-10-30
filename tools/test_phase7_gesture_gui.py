"""Live Tk regression for Installation hit tests and Diagram gesture isolation."""
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
from domain.diagram_commands import add_custom_node


def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(tmp) / 'recent.json')
        root = tk.Tk()
        root.geometry('1280x840')
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
            app.roof_mode = 'select'
            app.path_mode = 'select'
            app.roof_zones = [dict(id=1,x1=80.,y1=100.,x2=380.,y2=360.,
                                   w_mm=150.,h_mm=130.,align_x='Centre',align_y='Centre')]
            app.measures = [dict(p1=(450, 100),p2=(550, 100),
                                 label=(500, 120),axis='aligned')]
            app.draw_grid()
            root.update()

            def ev(cx, cy, state=0):
                return SimpleNamespace(x=cx-app.canvas.canvasx(0),
                                       y=cy-app.canvas.canvasy(0), state=state)

            # Click interior: select the zone, preserve geometry and viewport.
            before = copy.deepcopy(app.roof_zones)
            app.active_zone_idx = None
            app.selected_zone_indices = set()
            app._canvas_pan_start = ('legacy',)
            app.on_left_press(ev(220, 220))
            assert app.active_zone_idx == 0
            assert app._canvas_pan_start is None
            app.on_left_release(ev(220, 220))
            assert app.roof_zones == before
            # Corner starts resizing, with no accidental camera pan.
            app.on_left_press(ev(80, 100))
            assert app.zone_drag_mode == 'resize_tl', app.zone_drag_mode
            app.on_left_release(ev(80, 100))
            # Dimension labels are selectable separately from zones.
            app.roof_mode = 'select'
            app.on_left_press(ev(500, 120))
            assert app.measure_drag_idx == 0, app.measure_drag_idx
            app.on_left_release(ev(500, 120))
            assert app.measure_drag_idx is None
            # Ctrl+click a zone begins a multi-zone move and retains IDs.
            app.on_left_press(ev(220, 220, 0x0004))
            assert app.selected_zone_indices == {0}
            app.on_left_release(ev(220, 220, 0x0004))
            assert app.roof_zones == before

            # Diagram canvas in link mode must not mutate nodes via a stale
            # pre-command drag state (the old CanvasGrid code path did this).
            app.ribbon_notebook.select(app.tab_diagram)
            root.update()
            edit = add_custom_node(app.diagram_nodes, app.diagram_links,
                                   'custom::phase7', 'Phase7 test block')
            app._apply_diagram_edit(edit)
            app.diagram_nodes['custom::phase7']['x'] = 450.
            app.diagram_nodes['custom::phase7']['y'] = 250.
            app._diagram_layout_applied = app._diagram_layout_signature()
            app.draw_grid()
            root.update()
            original = copy.deepcopy(app.diagram_nodes)
            app.diagram_drag_node = 'custom::phase7'  # obsolete legacy state
            app.diagram_drag_start = (450, 250)
            app.diagram_drag_orig = (450, 250)
            app.diagram_link_mode = True
            app.on_left_drag(ev(500, 280))
            assert app.diagram_nodes == original, 'Link-mode gesture changed diagram geometry'
            app.diagram_drag_node = None
            app.diagram_link_mode = False
            # Direct drag handled by DiagramEditorMixin copy-on-write commands.
            app._record_history()
            start = app._history_index
            screen = (450 * app.zoom_level, 250 * app.zoom_level)
            app.on_left_press(ev(*screen))
            app.on_left_drag(ev(screen[0] + 18, screen[1] + 13))
            app.on_left_release(ev(screen[0] + 18, screen[1] + 13))
            assert app.diagram_nodes['custom::phase7']['x'] == 468., app.diagram_nodes['custom::phase7']
            assert app._history_index == start + 1, (app._history_index, start)
            app.undo_project()
            assert app.diagram_nodes['custom::phase7']['x'] == 450.
            app.redo_project()
            assert app.diagram_nodes['custom::phase7']['x'] == 468.
            assert not errors, errors
            print('PASS phase7 GUI: zone selection/resize/measure/ctrl, diagram link isolation and Undo/Redo')
        finally:
            root.destroy()


if __name__ == '__main__':
    run()
