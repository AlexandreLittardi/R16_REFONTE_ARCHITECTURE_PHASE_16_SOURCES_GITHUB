"""Headless Tk regression for six paired A/B/C top-origin fixing stations."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from mounting import fixings
from mounting_drawing import geometry, resolve_point


def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(tmp)/'recent.json')
        old=os.getcwd();os.chdir(tmp)
        root=tk.Tk();root.geometry('1400x900');errors=[]
        root.report_callback_exception=lambda *args:errors.append(args)
        try:
            app=PVLayoutRibbonApp(root);root.update()
            app.panel_width_mm=1303;app.panel_height_mm=2384;app.px_per_mm=.1
            from PIL import Image
            app.roof_pil_img=Image.new('RGB',(900,750),'white')
            app.roof_zones=[dict(id=1,x1=100,y1=100,x2=700,y2=650,angle_deg=0)]
            app.generate_panels_from_zones()
            app.ribbon_notebook.select(app.tab_mounting);root.update()
            coord=next(iter(app.panels));uid=app.panel_uids[coord]
            app.selected_panel_coords={coord}
            app._open_mounting_config();root.update()
            dialog=app._mounting_dialog
            count=next(w for w in walk(dialog) if isinstance(w,ttk.Combobox) and '6' in w.cget('values'))
            count.set('6');root.update()
            labels=[w.cget('text') for w in walk(dialog) if isinstance(w,ttk.Label)]
            assert 'A — from top (mm)' in labels,labels
            assert 'B — from top (mm)' in labels
            assert 'C — from top (mm)' in labels
            abc_entries=[w for w in walk(dialog) if isinstance(w,ttk.Entry) and w.winfo_ismapped() and
                         any(isinstance(sib,ttk.Label) and 'from top' in sib.cget('text')
                             for sib in w.master.winfo_children())]
            assert len(abc_entries)==3,len(abc_entries)
            for entry,value in zip(abc_entries,('440','1090','1930')):
                entry.delete(0,'end');entry.insert(0,value)
            root.update()
            apply=next(w for w in walk(dialog) if isinstance(w,ttk.Button) and
                       w.cget('text').startswith('Apply to selection'))
            assert not apply.instate(['disabled']),'Six-station preview must be valid'
            before=copy.deepcopy(app.mounting_plan)
            assert before['panels']=={},'Preview must not change plan before applying'
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                from PIL import ImageGrab
                root.update();ImageGrab.grab().save(os.path.join(os.environ['PV_MOUNTING_CAPTURE'],'config_6_abc.png'))
            apply.invoke();root.update()
            c=app.mounting_plan['panels'][uid]
            assert c['top_offsets_mm']==[440,1090,1930],c
            assert [f['position_mm'] for f in fixings(c)]==[440,440,1090,1090,1930,1930]
            app._fit_mounting();root.update()
            item=app._mounting_items[uid]
            assert len(item['fixings'])==6
            app._mounting_selected_fixing=(uid,0);app._mounting_update_status();root.update()
            app._mounting_inspector_value.set('520')
            app._mounting_apply_inspector();root.update()
            c=app.mounting_plan['panels'][uid]
            assert c['top_offsets_mm']==[520,1090,1930]
            assert [f['position_mm'] for f in fixings(c)][:2]==[520,520]
            app._mounting_auto_dimensions();root.update()
            dims=[d for d in app.mounting_plan['dimensions'] if d.get('auto')=='abc-top']
            assert len(dims)==3,len(dims)
            for distance,d in zip(c['top_offsets_mm'],dims):
                p1,p2=resolve_point(d,1,geometry(app)),resolve_point(d,2,geometry(app))
                assert abs((p2[1]-p1[1])/app.px_per_mm-distance)<.0001
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                from PIL import ImageGrab
                app._mounting_selected_fixing=None;app.draw_grid();root.update()
                ImageGrab.grab().save(os.path.join(os.environ['PV_MOUNTING_CAPTURE'],'montage_6_abc.png'))
            from mounting_installer import write_installer_pdf
            pdf=os.path.join(os.environ.get('PV_MOUNTING_CAPTURE',tmp),'exemple_pose_abc.pdf')
            write_installer_pdf(app,pdf)
            assert not errors,str(errors)
            print('PASS 6-point A/B/C Tk: live preview, validation, paired edit, 3 associative top-edge dimensions, PDF')
        finally:
            root.destroy();os.chdir(old)


if __name__=='__main__':main()
