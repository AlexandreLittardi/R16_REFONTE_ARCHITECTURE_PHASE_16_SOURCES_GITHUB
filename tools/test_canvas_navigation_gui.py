"""GUI stress/regression test: zoom cursor anchor, pan, redraw and isolated cameras."""
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


def near(a,b,eps=3.):
    assert abs(a-b) < eps, (a,b)

with tempfile.TemporaryDirectory() as folder:
    os.environ['PV_APP_RECENTS_FILE'] = str(Path(folder)/'recent.json')
    os.chdir(folder)
    root=tk.Tk()
    errors=[]
    root.report_callback_exception=lambda *args:errors.append(args)
    try:
        app=PVLayoutRibbonApp(root)
        root.update()
        app.ribbon_notebook.select(app.tab_roof)
        root.update()
        # Large photo at zoom 4.5 must not allocate a full >100 Mpix raster.
        app.roof_pil_img=Image.new('RGB',(5500,3600),'#aaaaaa')
        app.px_per_mm=2
        app.roof_zones=[dict(id=1,x1=120,y1=100,x2=950,y2=740,
                             w_mm=415,h_mm=320)]
        app.measures=[dict(p1=(120,120),p2=(520,120),label=(320,95),axis='aligned')]
        original=copy.deepcopy((app.roof_zones,app.measures))
        app.zoom_level=.18
        app.draw_grid()
        root.update()
        app.canvas.xview_moveto(.55)
        app.canvas.yview_moveto(.55)
        x,y=app.canvas.winfo_width()*.4,app.canvas.winfo_height()*.7
        for factor in [1.15]*14+[1/1.15]*11:
            before=(app.canvas.canvasx(x)/app.zoom_level,app.canvas.canvasy(y)/app.zoom_level)
            app._zoom_at_pointer(SimpleNamespace(x=x,y=y),1 if factor>1 else -1)
            after=(app.canvas.canvasx(x)/app.zoom_level,app.canvas.canvasy(y)/app.zoom_level)
            near(before[0],after[0],6/app.zoom_level)
            near(before[1],after[1],6/app.zoom_level)
        assert (app.roof_zones,app.measures)==original
        app.zoom_level=4.5
        app.draw_grid()
        root.update()
        assert app._installation_photo_tiled, 'Large photograph not clipped at high zoom'
        assert app.roof_tk_img.width()<app.canvas.winfo_width()+600
        app._installation_middle_pan_start(SimpleNamespace(x=300,y=220))
        app._installation_middle_pan_drag(SimpleNamespace(x=100,y=120))
        app._installation_middle_pan_stop(SimpleNamespace(x=100,y=120))
        root.update()
        assert (app.roof_zones,app.measures)==original
        app.ribbon_notebook.select(app.tab_diagram)
        root.update()
        app.diagram_nodes={'custom-%d'%i:dict(type='custom',label='Switchboard %d'%i,x=(i%10)*400,y=(i//10)*180)
                           for i in range(80)}
        app.diagram_links=[dict(a='custom-%d'%i,b='custom-%d'%(i+1),auto=False)
                           for i in range(79)]
        app._diagram_layout_applied=app._diagram_layout_signature()
        app._fit_diagram()
        root.update()
        before_nodes=copy.deepcopy(app.diagram_nodes)
        x,y=app.canvas.winfo_width()*.64,app.canvas.winfo_height()*.48
        for direction in [1]*18+[-1]*22+[1]*7:
            before=(app.canvas.canvasx(x)/app.zoom_level,app.canvas.canvasy(y)/app.zoom_level)
            app._zoom_at_pointer(SimpleNamespace(x=x,y=y),direction)
            after=(app.canvas.canvasx(x)/app.zoom_level,app.canvas.canvasy(y)/app.zoom_level)
            near(before[0],after[0],6/app.zoom_level)
            near(before[1],after[1],6/app.zoom_level)
        assert app.diagram_nodes == before_nodes, 'Nodes were moved by zoom'
        app.on_left_press(SimpleNamespace(x=240,y=270))
        app.on_left_drag(SimpleNamespace(x=180,y=180))
        app.on_left_release(SimpleNamespace(x=180,y=180))
        assert app.diagram_nodes==before_nodes, 'Nodes were moved by panning'
        # A selected diagram block can still be moved accurately using right drag.
        from view_navigation import place_viewport
        app.zoom_level = 1.
        app.draw_grid()
        moved_id = 'custom-25'
        node = app.diagram_nodes[moved_id]
        place_viewport(app.canvas, node['x']-app.canvas.winfo_width()/2,
                       node['y']-app.canvas.winfo_height()/2)
        root.update()
        sx = node['x'] - app.canvas.canvasx(0)
        sy = node['y'] - app.canvas.canvasy(0)
        orig_node = (node['x'],node['y'])
        app.diagram_selected_nodes={moved_id}
        app.on_right_press(SimpleNamespace(x=sx,y=sy,state=0))
        app.on_right_drag(SimpleNamespace(x=sx+40,y=sy+25))
        app.on_right_release(SimpleNamespace(x=sx+40,y=sy+25))
        # The phase-4 copy-on-write command replaces the node dictionary.
        # Assert against the authoritative current model, not a stale alias.
        near(app.diagram_nodes[moved_id]['x'],orig_node[0]+40,.1)
        near(app.diagram_nodes[moved_id]['y'],orig_node[1]+25,.1)
        diagram_zoom=app.zoom_level
        diagram_center=(app.canvas.canvasx(0)+app.canvas.winfo_width()/2)/diagram_zoom
        app.ribbon_notebook.select(app.tab_roof)
        root.update()
        app.ribbon_notebook.select(app.tab_diagram)
        root.update()
        near(app.zoom_level,diagram_zoom,.0001)
        near((app.canvas.canvasx(0)+app.canvas.winfo_width()/2)/app.zoom_level,diagram_center,10/app.zoom_level)
        root.update()
        assert not errors, [str(e) for e in errors]
        print('PASS navigation: anchored wheel + & -, 80 nodes, panning, camera restore, tiled 5500x3600 aerial at x4.5')
    finally:
        root.destroy()
