"""UI regression for view-only undo history and routing command dispatch."""
from pathlib import Path
import os
import sys
import tempfile
import tkinter as tk
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import PVLayoutRibbonApp
from application.events import RoutingAreaChanged

with tempfile.TemporaryDirectory() as tmp:
    os.environ['PV_APP_RECENTS_FILE'] = str(Path(tmp) / 'recent.json')
    root = tk.Tk()
    root.geometry('1280x820')
    callback_errors = []
    root.report_callback_exception = lambda *args: callback_errors.append(args)
    try:
        app=PVLayoutRibbonApp(root)
        root.update()
        assert len(app.ribbon_notebook.tabs()) == 11
        # Only the unified controller is installed for wheel/middle-pan.
        # Old per-tab callbacks remain callable but are not registered twice.
        for sequence, callback in (
            ('<ButtonPress-2>', '_navigation_pan_press'),
            ('<B2-Motion>', '_navigation_pan_drag'),
            ('<ButtonRelease-2>', '_navigation_pan_release'),
            ('<MouseWheel>', '_navigation_wheel'),
            ('<Button-4>', '_navigation_wheel'),
            ('<Button-5>', '_navigation_wheel'),
        ):
            binding = app.canvas.bind(sequence)
            assert callback in binding, (sequence, binding)
            assert len(binding.strip().splitlines()) == 1, (sequence, binding)
        app.ribbon_notebook.select(app.tab_roof)
        app._auto_fit=False
        app.px_per_mm=1
        app.roof_zones=[dict(id=1,x1=0,y1=0,x2=200,y2=200)]
        app.roof_polygons=[{'id':1,'points':[(20,20),(90,20),(90,90),(20,90)],'height_m':11}]
        app.draw_grid()
        app._record_history()
        before=app._history_index
        ids_before=dict(app.panel_uids)
        for _ in range(8):
            app._zoom_button_change(1.07)
        app._record_history()
        assert app._history_index == before, f'Zoom produced history: {before}->{app._history_index}'
        assert app.panel_uids == ids_before

        event_log=[]
        app._project_events.subscribe(event_log.append)
        app.path_mode='select_polygon'
        app.active_polygon_idx=0
        app.polygon_drag_mode='move'
        app.polygon_drag_start_pt=(app.canvas.canvasx(0),app.canvas.canvasy(0))
        app.polygon_drag_initial_points=list(app.roof_polygons[0]['points'])
        app._polygon_vertex=None
        app.on_left_drag(SimpleNamespace(x=0,y=0,state=0))
        # Explicit command, with real nonzero translation; no model/metadata lost.
        app.on_left_drag(SimpleNamespace(x=30,y=20,state=0))
        assert event_log and isinstance(event_log[-1],RoutingAreaChanged),event_log
        assert app.roof_polygons[0]['height_m']==11
        assert app.roof_polygons[0]['points'][0][0]>20,app.roof_polygons
        assert not callback_errors,callback_errors
        print('PASS 11 tabs, view-only undo unchanged, routing command/events in live UI')
    finally:
        root.destroy()
