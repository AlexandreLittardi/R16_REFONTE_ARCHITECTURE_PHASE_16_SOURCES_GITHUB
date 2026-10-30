"""Real Tk pointer/F2/Delete test for non-geometric dimension labels (xvfb-run)."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from mounting import default_config,validate_config


def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(tmp)/'recent.json')
        old=os.getcwd();os.chdir(tmp)
        root=tk.Tk();root.geometry('1550x970');errors=[]
        root.report_callback_exception=lambda *err:errors.append(err)
        try:
            app=PVLayoutRibbonApp(root);root.update()
            app.panel_width_mm=1303;app.panel_height_mm=2384;app.px_per_mm=.1
            from PIL import Image
            app.roof_pil_img=Image.new('RGB',(600,550),'white')
            app.roof_zones=[dict(id=1,x1=100,y1=100,x2=450,y2=450,angle_deg=0)]
            app.generate_panels_from_zones()
            app.ribbon_notebook.select(app.tab_mounting);root.update()
            coord=next(iter(app.panels));uid=app.panel_uids[coord]
            config=default_config(1303,2384);config['count']=6;config['top_offsets_mm']=[440,1090,1930]
            app.mounting_plan['panels'][uid]=validate_config(config)
            app.selected_panel_coords={coord}
            app._render_mounting_plan();app._fit_mounting();root.update()
            original=copy.deepcopy(app.mounting_plan['panels'])
            def focus_tag(tag):
                ids=[i for i in app.canvas.find_withtag(tag) if app.canvas.type(i)=='text']
                assert ids,tag
                x,y=app.canvas.coords(ids[0]);x-=app.canvas.canvasx(0);y-=app.canvas.canvasy(0)
                assert 0<x<app.canvas.winfo_width() and 0<y<app.canvas.winfo_height(),(tag,x,y)
                app.canvas.event_generate('<ButtonPress-1>',x=round(x),y=round(y));root.update()
                app.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y));root.update()
                app.canvas.focus_set()
            focus_tag('live-dimension:field:x')
            assert app._mounting_selected_live_dimension=='field:x',app._mounting_selected_live_dimension
            with patch('mixins.mounting_ui.simpledialog.askstring',return_value='LIGNE REFERENCE CHANTIER'):
                app.canvas.event_generate('<KeyPress-F2>');root.update()
            assert app.mounting_plan['dimension_labels']['field:x']=='LIGNE REFERENCE CHANTIER'
            assert app.mounting_plan['panels']==original
            app.undo_project();root.update()
            assert 'field:x' not in app.mounting_plan['dimension_labels']
            app.redo_project();root.update()
            assert app.mounting_plan['dimension_labels']['field:x']=='LIGNE REFERENCE CHANTIER'
            assert any(app.canvas.itemcget(i,'text')=='LIGNE REFERENCE CHANTIER'
                       for i in app.canvas.find_withtag('live-dimension:field:x') if app.canvas.type(i)=='text')
            app.canvas.event_generate('<KeyPress-Delete>');root.update()
            assert 'field:x' in app.mounting_plan['hidden_dimensions']
            assert not app.canvas.find_withtag('live-dimension:field:x')
            app._mounting_restore_dimensions();root.update()
            assert app.canvas.find_withtag('live-dimension:field:x')
            # Zoom into the selected panel: detailed A/B/C are deliberately
            # hidden on the general overview when labels would be illegible.
            app.selected_panel_coords={coord}
            app.draw_grid();root.update()
            item=app._mounting_items[uid]
            cx=sum(point[0] for point in item['poly'])/4
            cy=sum(point[1] for point in item['poly'])/4
            app._mounting_zoom(max(1.,1.3/app.zoom_level));root.update()
            app._set_mounting_viewport(cx*app.zoom_level-app.canvas.winfo_width()/2,
                                      cy*app.zoom_level-app.canvas.winfo_height()/2)
            app._draw_mounting_annotations();root.update()
            focus_tag(f'live-dimension:panel:{uid}:abc:A')
            assert app._mounting_selected_live_dimension==f'panel:{uid}:abc:A'
            with patch('mixins.mounting_ui.simpledialog.askstring',return_value='A = position A adapter'):
                app._mounting_double_click(type('E',(),{'x':round(app.canvas.coords([i for i in app.canvas.find_withtag(f'live-dimension:panel:{uid}:abc:A') if app.canvas.type(i)=='text'][0])[0]-app.canvas.canvasx(0)),
                                                  'y':round(app.canvas.coords([i for i in app.canvas.find_withtag(f'live-dimension:panel:{uid}:abc:A') if app.canvas.type(i)=='text'][0])[1]-app.canvas.canvasy(0)), 'state':0})())
                root.update()
            assert app.mounting_plan['dimension_labels'][f'panel:{uid}:abc:A']=='A = position A adapter'
            assert app.mounting_plan['panels']==original
            assert not errors,str(errors)
            print('PASS Tk dimension selection/F2/Edit/Delete/Restore/ABC double-click; fixing geometry unchanged')
        finally:
            root.destroy();os.chdir(old)

if __name__=='__main__':run()
