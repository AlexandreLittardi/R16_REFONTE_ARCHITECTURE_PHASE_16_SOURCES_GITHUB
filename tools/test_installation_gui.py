"""Tk integration smoke test for Installation Area image editing and pan navigation."""
import copy
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from project_store import write_project,validate_project

with tempfile.TemporaryDirectory() as folder:
    os.environ['PV_APP_RECENTS_FILE']=str(Path(folder)/'recent.json')
    os.chdir(folder)
    root=tk.Tk()
    errors=[]
    root.report_callback_exception=lambda *args:errors.append(args)
    try:
        app=PVLayoutRibbonApp(root)
        root.update()
        app.ribbon_notebook.select(app.tab_roof)
        app.roof_pil_img=Image.new('RGB',(1800,1250),'white')
        # Camera initialization is explicit: UI auto-fit may run on tab switch.
        app._auto_fit=False
        app.zoom_level=1.
        app.px_per_mm=2.
        app.roof_zones=[{'id':1,'x1':100.,'y1':100.,'x2':500.,'y2':400.,
                         'w_mm':200.,'h_mm':150.,'align_x':'Centre','align_y':'Centre'}]
        app.measures=[{'p1':(150.,125.),'p2':(350.,125.),'label':(250.,100.),'axis':'aligned'}]
        app.draw_grid()
        root.update()
        image=app.canvas.find_withtag('roof_background')
        assert len(image)==1
        zone_before=copy.deepcopy(app.roof_zones)
        measure_before=copy.deepcopy(app.measures)
        # Menu should expose the tool to the user.
        assert any(str(w.cget('text'))=='Image / Navigation' for w in app.tab_roof.winfo_children() if 'text' in w.keys())
        app._select_background_move_tool()
        ev=SimpleNamespace(x=300,y=250)
        app.on_left_press(ev)
        app.on_left_drag(SimpleNamespace(x=355,y=295))
        assert app.roof_image_offset==(55.,45.),app.roof_image_offset
        assert app.roof_zones==zone_before
        assert app.measures==measure_before
        app.on_left_release(ev)
        root.update()
        coords=app.canvas.coords(app.canvas.find_withtag('roof_background')[0])
        assert all(abs(x-y*app.zoom_level)<.1 for x,y in zip(coords,(55,45))),(coords,app.zoom_level)
        data=app._collect_project_data()
        filepath=Path(folder)/'roundtrip.json'
        write_project(filepath,data,app.roof_pil_img)
        loaded=validate_project(__import__('json').loads(filepath.read_text()))
        assert loaded['roof_image_offset']==[55.,45.]
        app._apply_document(loaded,str(filepath));root.update()
        assert app.roof_image_offset==(55.,45.),app.roof_image_offset
        assert all(app.roof_zones[0][k]==zone_before[0][k] for k in ('x1','x2','y1','y2'))
        app._stop_background_move_tool()
        # A wheel/zoom changes drawing size but never physically changes measured length.
        scale=app.px_per_mm
        app._zoom_button_change(1.2)
        assert app.px_per_mm==scale
        assert app.measures==measure_before
        assert all(abs(x-y*app.zoom_level)<.1 for x,y in zip(app.canvas.coords(app.canvas.find_withtag('roof_background')[0]),(55,45)))
        # Middle-click pan moves the viewport only.
        app.canvas.configure(scrollregion=(0,0,2800,2200))
        app.canvas.xview_moveto(.5);app.canvas.yview_moveto(.5);root.update()
        before=app.canvas.xview()
        app._installation_middle_pan_start(SimpleNamespace(x=240,y=250))
        app._installation_middle_pan_drag(SimpleNamespace(x=140,y=250))
        app._installation_middle_pan_stop(SimpleNamespace(x=140,y=250))
        assert app.canvas.xview()!=before,(before,app.canvas.xview())
        assert app.roof_image_offset==(55.,45.)
        assert app.roof_zones==zone_before
        # Real canvas events also honor mouse bindings and do not mutate survey geometry.
        root.update()
        app._reset_background_position()
        assert app.roof_image_offset==(0.,0.)
        assert not errors,errors
        print('PASS: tool menu, photo drag, geometry isolation, project JSON, zoom and middle-button pan')
    finally:
        root.destroy()
