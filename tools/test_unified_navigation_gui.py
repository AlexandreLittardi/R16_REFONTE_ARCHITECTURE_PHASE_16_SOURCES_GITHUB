"""End-to-end stress for shared wheel/middle-pan navigation and large Layout photos."""
import copy
import os
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp

with tempfile.TemporaryDirectory() as tmp:
    os.environ['PV_APP_RECENTS_FILE'] = str(Path(tmp)/'recent.json')
    os.chdir(tmp)
    root = tk.Tk()
    exceptions = []
    root.report_callback_exception = lambda *e: exceptions.append(e)
    try:
        app = PVLayoutRibbonApp(root)
        root.update()
        app._auto_fit = False
        app.roof_pil_img = Image.new('RGB', (5500, 3600), '#bcbcbc')
        app.px_per_mm = 2.0
        app.roof_zones = [dict(id=1, x1=180., y1=120., x2=2680., y2=1940.,
                               w_mm=1250., h_mm=910., rows=0, cols=0)]
        app.measures = [dict(p1=(200, 200), p2=(1250, 200),
                             label=(500, 170), axis='aligned')]
        snapshot = copy.deepcopy(([(z["x1"], z["y1"], z["x2"], z["y2"]) for z in app.roof_zones], app.measures))
        # Test all drawings which use the common canvas, not just the two that
        # happened to be crashing last time. The image stays in model memory.
        tabs = [app.tab_roof, app.tab_layout, app.tab_stringing,
                app.tab_equipment, app.tab_shadow, app.tab_diagram,
                app.tab_notes, app.tab_mounting]
        for tab in tabs:
            app.ribbon_notebook.select(tab)
            root.update()
            idx = app._get_active_tab_index()
            app._auto_fit = False
            if idx not in (7, 10):
                app.zoom_level = 3.8
                app.draw_grid()
                assert app.roof_tk_img.width() < app.canvas.winfo_width() + 700, (
                    idx, app.roof_tk_img.width(), app.canvas.winfo_width())
                assert app.roof_tk_img.height() < app.canvas.winfo_height() + 700
            anchor = (max(100, app.canvas.winfo_width()*.4),
                      max(100, app.canvas.winfo_height()*.6))
            for direction in [1, 1, 1, -1, -1, 1, -1]:
                before = (app.canvas.canvasx(anchor[0])/app.zoom_level,
                          app.canvas.canvasy(anchor[1])/app.zoom_level)
                app._navigation_wheel(SimpleNamespace(x=anchor[0], y=anchor[1],
                                                       num=0, delta=120*direction))
                root.after(30, root.quit)
                root.mainloop()
                after = (app.canvas.canvasx(anchor[0])/app.zoom_level,
                         app.canvas.canvasy(anchor[1])/app.zoom_level)
                if idx != 10:
                    assert abs(before[0] - after[0]) < 12/app.zoom_level, (idx, before, after)
                    assert abs(before[1] - after[1]) < 12/app.zoom_level, (idx, before, after)
            # A plain left drag is deliberately NOT a pan gesture.
            if idx in (2, 3):
                plain = SimpleNamespace(x=230, y=220, state=0)
                left_before = (app.canvas.canvasx(0), app.canvas.canvasy(0))
                app.on_left_press(plain)
                app.on_left_drag(SimpleNamespace(x=130, y=115, state=0))
                app.on_left_release(SimpleNamespace(x=130, y=115, state=0))
                left_after = (app.canvas.canvasx(0), app.canvas.canvasy(0))
                assert abs(left_after[0]-left_before[0])<2, (idx,left_before,left_after)
                assert abs(left_after[1]-left_before[1])<2, (idx,left_before,left_after)
            old = (app.canvas.canvasx(0), app.canvas.canvasy(0))
            app._navigation_pan_press(SimpleNamespace(x=250, y=280))
            app._navigation_pan_drag(SimpleNamespace(x=180, y=190))
            app._navigation_pan_release(SimpleNamespace(x=180, y=190))
            moved = (app.canvas.canvasx(0), app.canvas.canvasy(0))
            assert abs(moved[0] - old[0] - 70) < 5, (idx, old, moved)
            assert abs(moved[1] - old[1] - 90) < 5, (idx, old, moved)
            root.update()
            print('PASS tab', idx, 'zoom', round(app.zoom_level, 3))
        assert ([(z['x1'],z['y1'],z['x2'],z['y2']) for z in app.roof_zones], app.measures) == snapshot, 'Physical geometry changed during navigation'
        assert not exceptions, [str(e) for e in exceptions]
        print('PASS unified zoom + middle pan, model invariance, large photo tiled in every drawing tab')
    finally:
        root.destroy()
