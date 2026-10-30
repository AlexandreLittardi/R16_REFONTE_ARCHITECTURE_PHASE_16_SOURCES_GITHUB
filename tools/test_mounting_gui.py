"""Native Tk smoke test on a disposable synthetic project; requires a display."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk, messagebox
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from mounting import default_config, validate_config, dimension_geometry
from mounting_drawing import geometry, resolve_point, write_svg, write_schedule


def walk(parent):
    for child in parent.winfo_children():
        yield child
        yield from walk(child)


def run():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(directory)/'recent.json')
        previous=os.getcwd();os.chdir(directory)
        root=tk.Tk();errors=[]
        root.report_callback_exception=lambda *args:errors.append(args)
        try:
            app=PVLayoutRibbonApp(root);root.update()
            assert len(app.ribbon_notebook.tabs())==11
            app.panel_width_mm=1303;app.panel_height_mm=2384;app.px_per_mm=.1
            from PIL import Image
            app.roof_pil_img=Image.new('RGB',(900,750),'#fafcfb')
            app.roof_zones=[dict(id=1,x1=100,y1=100,x2=700,y2=650,angle_deg=17)]
            app.generate_panels_from_zones()
            assert len(app.panels)>=2
            app.ribbon_notebook.select(app.tab_mounting);root.update();app._fit_mounting();root.update()
            toolbar=[w for w in app.tab_mounting.winfo_children() if isinstance(w,ttk.Menubutton)]
            assert [str(w.cget('text')) for w in toolbar]==['Selection','Clamps','Dimensions','View','Export','Installation drawing','Edit']
            assert not any(isinstance(w,ttk.Button) for w in app.tab_mounting.winfo_children())
            assert app.mounting_inspector.winfo_ismapped()
            assert app.mounting_auto_cotes.get()
            assert not app.canvas.find_withtag('mounting_background')
            # Menus activate the same tools; history states remain in sync.
            app._mounting_menus['dimensions'].invoke(1);assert app.mounting_mode=='horizontal'
            app._mounting_menus['selection'].invoke(0);assert app.mounting_mode=='select'
            coord=next(iter(app.panels));uid=app.panel_uids[coord]
            app.selected_panel_coords={coord}
            before=copy.deepcopy(app.mounting_plan)
            app._mounting_menus['fixings'].invoke(0);root.update()
            dialog=app._mounting_dialog
            entries=[w for w in walk(dialog) if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox)]
            entries[0].delete(0,'end');entries[0].insert(0,'490')
            entries[1].delete(0,'end');entries[1].insert(0,'490');root.update()
            assert app.mounting_plan==before,'Preview must not commit'
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                from PIL import ImageGrab
                ImageGrab.grab().save(str(Path(os.environ['PV_MOUNTING_CAPTURE'])/'configurator.png'))
            button=next(w for w in walk(dialog) if isinstance(w,ttk.Button) and str(w.cget('text')).startswith('Apply to selection'))
            entries[0].delete(0,'end');entries[0].insert(0,'-1');root.update()
            assert button.instate(['disabled']),'Invalid preview must disable application'
            entries[0].delete(0,'end');entries[0].insert(0,'490');root.update()
            button.invoke();root.update()
            assert set(app.mounting_plan['panels'])=={uid}
            assert len(app._mounting_items[uid]['fixings'])==4
            # Cancel changed preview without altering the stored geometry.
            saved=copy.deepcopy(app.mounting_plan)
            app._open_mounting_config();root.update()
            dialog=app._mounting_dialog
            entry=next(w for w in walk(dialog) if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox))
            entry.delete(0,'end');entry.insert(0,'600');root.update()
            next(w for w in walk(dialog) if isinstance(w,ttk.Button) and str(w.cget('text'))=='Cancel').invoke()
            assert app.mounting_plan==saved
            app._open_mounting_config();root.update()
            next(w for w in walk(app._mounting_dialog) if isinstance(w,ttk.Button) and str(w.cget('text')).startswith('Apply to all')).invoke();root.update()
            assert len(app.mounting_plan['panels'])==len(app.panels)
            assert app._mounting_menus['edit'].entrycget(0,'state')=='normal'
            app._mounting_menus['edit'].invoke(0);root.update()
            assert set(app.mounting_plan['panels'])=={uid},'Undo configuration'
            assert app._mounting_menus['edit'].entrycget(1,'state')=='normal'
            app._mounting_menus['edit'].invoke(1);root.update()
            assert len(app.mounting_plan['panels'])==len(app.panels)
            app.selected_panel_coords={coord};app._mounting_auto_dimensions();root.update()
            dims=app.mounting_plan['dimensions'];assert len(dims)==6
            app._mounting_auto_dimensions();assert len(app.mounting_plan['dimensions'])==6
            # A real pointer gesture on the rotated first fixing, followed by a live associative dimension.
            item=app._mounting_items[uid];point=item['fixings'][0]['point']
            def event(p):return SimpleNamespace(x=p[0]*app.zoom_level-app.canvas.canvasx(0),y=p[1]*app.zoom_level-app.canvas.canvasy(0),state=0)
            # Real Tk events: Shift selects panels even over fixing footprints,
            # during a rapid double click and with incidental pointer movement.
            saved_plan=copy.deepcopy(app.mounting_plan)
            other_coord=next(c for c in app.panels if c!=coord)
            other_uid=app.panel_uids[other_coord]
            other_item=app._mounting_items[other_uid]
            other_center=tuple(sum(p[i] for p in other_item['poly'])/4 for i in (0,1))
            def click(p,state=0,jitter=0):
                e=event(p);kw=dict(x=round(e.x),y=round(e.y),state=state)
                app.canvas.event_generate('<ButtonPress-1>',**kw);root.update()
                if jitter:
                    app.canvas.event_generate('<B1-Motion>',x=round(e.x)+jitter,y=round(e.y),state=state|256);root.update()
                app.canvas.event_generate('<ButtonRelease-1>',**kw);root.update()
            with patch.object(app,'_open_mounting_config',side_effect=AssertionError('Shift opened a dialog')),patch.object(app,'_edit_mounting_fixing',side_effect=AssertionError('Shift edited a fixing')):
                app.selected_panel_coords={coord};click(other_center,1)
                assert app.selected_panel_coords=={coord,other_coord}
                click(other_center,1)
                assert app.selected_panel_coords=={coord},'Rapid Shift double click must toggle twice'
                click(other_item['fixings'][1]['point'],1,6)
                assert app.selected_panel_coords=={coord,other_coord}
                assert app._mounting_drag is None
                click(other_item['fixings'][1]['point'],1)
                assert app.selected_panel_coords=={coord}
                for factor in (.45, 4):
                    app._mounting_zoom(factor,event=SimpleNamespace(x=400,y=300));root.update()
                    app.selected_panel_coords={coord};click(other_center,1,2)
                    assert app.selected_panel_coords=={coord,other_coord},'Shift selection must survive zoom/pan'
                    click(other_center,1)
                    assert app.selected_panel_coords=={coord}
                app._fit_mounting();root.update()
            assert app.mounting_plan==saved_plan,'Shift must never move a fixing or a dimension'
            # A tiny unmodified movement is still a click, not an edit.
            app.on_left_press(event(point))
            tiny=event(point);tiny.x+=2
            app.on_left_drag(tiny);app.on_left_release(tiny)
            assert app.mounting_plan==saved_plan
            app.on_left_press(event(point))
            assert app._mounting_selected_fixing==(uid,0)
            c=item['config'];from mounting import transform
            destination=transform(item['poly'],c['width_mm'],c['height_mm'],(0,600))
            app.on_left_drag(event(destination));app.on_left_release(event(destination));root.update()
            # Pointer precision is one screen pixel; the numerical editor supplies
            # exact millimetres independently of the current fit/zoom.
            assert abs(app.mounting_plan['panels'][uid]['positions']['0']-600)<1/(app.px_per_mm*app.zoom_level)+.2
            with patch('mixins.mounting_ui.simpledialog.askfloat',return_value=600):app._edit_mounting_fixing()
            assert app.mounting_plan['panels'][uid]['positions']['0']==600
            assert abs(__import__('math').dist(resolve_point(dims[0],1,geometry(app)),resolve_point(dims[0],2,geometry(app)))/app.px_per_mm-600)<.1
            # Three clicks: corner, fixing, dimension line position.
            app._set_mounting_mode('aligned')
            corner=item['poly'][0];fix=app._mounting_items[uid]['fixings'][0]['point']
            app.on_left_press(event(corner));app.on_left_press(event(fix))
            app.on_left_press(event((corner[0]-40,corner[1]+20)));root.update()
            assert len(app.mounting_plan['dimensions'])==7
            app._on_escape_key();assert app.mounting_mode=='select'
            app._mounting_selected_dimension=6;app._mounting_delete();assert len(app.mounting_plan['dimensions'])==6
            # Dedicated real-size dialog: live previews, physical footprint,
            # position preservation, selection vs all, associative size dimensions.
            app._mounting_selected_fixing=(uid,0);app.selected_panel_coords={coord}
            app._open_fixing_dimensions();root.update()
            dialog=app._mounting_size_dialog
            entries=[w for w in walk(dialog) if isinstance(w,ttk.Entry)]
            for entry,value in zip(entries,('350','180')):
                entry.delete(0,'end');entry.insert(0,value)
            root.update()
            assert app.mounting_plan['panels'][uid]['clamp_length_mm']==50,'Size preview must not commit'
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                from PIL import ImageGrab
                ImageGrab.grab().save(str(Path(os.environ['PV_MOUNTING_CAPTURE'])/'fixation-dimensions.png'))
            next(w for w in walk(dialog) if isinstance(w,ttk.Button) and str(w.cget('text')).startswith('Apply to selection')).invoke();root.update()
            assert app.mounting_plan['panels'][uid]['clamp_length_mm']==350
            assert app.mounting_plan['panels'][uid]['positions']['0']==600
            other=next(k for k in app.mounting_plan['panels'] if k!=uid)
            assert app.mounting_plan['panels'][other]['clamp_length_mm']==50
            import math
            ident=app.canvas.find_withtag(f'fixing:{uid}:0')[0]
            xy=app.canvas.coords(ident);points=list(zip(xy[::2],xy[1::2]))
            self_scale=app.px_per_mm*app.zoom_level
            assert abs(math.dist(points[0],points[1])/self_scale-180)<1e-6
            assert abs(math.dist(points[1],points[2])/self_scale-350)<1e-6
            # Grabbing a large footprint away from its centre must not make it jump.
            c=app.mounting_plan['panels'][uid];item=app._mounting_items[uid]
            start=transform(item['poly'],c['width_mm'],c['height_mm'],(-60,470))
            end=transform(item['poly'],c['width_mm'],c['height_mm'],(-60,570))
            app.on_left_press(event(start));app.on_left_drag(event(end));app.on_left_release(event(end));root.update()
            assert abs(app.mounting_plan['panels'][uid]['positions']['0']-700)<1/(app.px_per_mm*app.zoom_level)+.2
            with patch('mixins.mounting_ui.simpledialog.askfloat',return_value=600):app._edit_mounting_fixing()
            app._mounting_dimension_fixing();root.update();assert len(app.mounting_plan['dimensions'])==8
            app._mounting_dimension_fixing();assert len(app.mounting_plan['dimensions'])==8
            app._open_fixing_dimensions();root.update();dialog=app._mounting_size_dialog
            entries=[w for w in walk(dialog) if isinstance(w,ttk.Entry)]
            for entry,value in zip(entries,('400','200')):
                entry.delete(0,'end');entry.insert(0,value)
            root.update()
            next(w for w in walk(dialog) if isinstance(w,ttk.Button) and str(w.cget('text')).startswith('Apply to all')).invoke();root.update()
            assert all(c['clamp_length_mm']==400 and c['clamp_width_mm']==200 for c in app.mounting_plan['panels'].values())
            app.undo_project();root.update()
            assert app.mounting_plan['panels'][uid]['clamp_length_mm']==350
            assert app.mounting_plan['panels'][other]['clamp_length_mm']==50
            app.redo_project();root.update()
            assert all(c['clamp_length_mm']==400 for c in app.mounting_plan['panels'].values())
            d=app.mounting_plan['dimensions'][-1];items=geometry(app)
            assert abs(math.dist(resolve_point(d,1,items),resolve_point(d,2,items))/app.px_per_mm-400)<1e-6
            fixed_point=app._mounting_items[uid]['fixings'][0]['point']
            app._mounting_zoom(20);root.update()
            assert app._mounting_items[uid]['fixings'][0]['point']==fixed_point,'Zoom must not alter geometry'
            app._mounting_pan_start(SimpleNamespace(x=500,y=400))
            app._mounting_pan_drag(SimpleNamespace(x=300,y=250));root.update()
            app._fit_mounting();root.update()
            # Layout-style labels and view-only zoom preserve canvas objects,
            # document values and the world point under the pointer.
            label=app.canvas.find_withtag(f'panel-number:{uid}')[0]
            assert app.canvas.itemcget(label,'text')==str(app.panels[coord])
            font=app.canvas.itemcget(label,'font')
            assert str(root.tk.call('font','actual',font,'-weight'))=='bold'
            assert abs(float(app.canvas.itemcget(label,'angle'))-17)<1e-6
            shape=app.canvas.find_withtag(f'fixing:{uid}:0')[0]
            document=copy.deepcopy(app._collect_project_data())
            point=SimpleNamespace(x=360,y=280)
            oldzoom=app.zoom_level
            anchor=(app.canvas.canvasx(point.x)/oldzoom,app.canvas.canvasy(point.y)/oldzoom)
            with patch('mixins.mounting_view.geometry',side_effect=AssertionError('Geometry rebuilt during zoom')):
                app._mounting_zoom(1.2,event=point);root.update()
                assert app.canvas.find_withtag(f'fixing:{uid}:0')[0]==shape
                now=(app.canvas.canvasx(point.x)/app.zoom_level,app.canvas.canvasy(point.y)/app.zoom_level)
                assert max(abs(a-b)*app.zoom_level for a,b in zip(anchor,now))<=1.5
                app._mounting_zoom(1/1.2,event=point);root.update()
            assert app._collect_project_data()==document
            with patch.object(app,'_mounting_zoom',wraps=app._mounting_zoom) as frames:
                start_zoom=app.zoom_level
                for i in range(8):app._zoom_at_pointer(point,5)
                root.after(45,root.quit);root.mainloop()
                assert frames.call_count==1,'Wheel events should share a single frame'
                assert abs(app.zoom_level-min(20,start_zoom*1.2**8))<1e-9
            app._fit_mounting();root.update()
            # Site datum, editable axis position and installer metadata must survive JSON.
            app._mounting_selected_fixing=(uid,0);app.draw_grid();root.update()
            assert app._mounting_inspector_target==(uid,0)
            app._mounting_inspector_value.set('600');app._mounting_apply_inspector();root.update()
            assert app.mounting_plan['panels'][uid]['positions']['0']==600
            app._mounting_define_origin(app._mounting_items[uid]['poly'][0]);root.update()
            assert app.mounting_plan['site']['origin'] is not None
            app._edit_mounting_site();root.update()
            site_window=app._mounting_site_window
            site_entries=[w for w in walk(site_window) if isinstance(w,ttk.Entry)]
            site_entries[3].delete(0,'end');site_entries[3].insert(0,'ZONE CHANTIER')
            next(w for w in walk(site_window) if isinstance(w,ttk.Button) and 'Save site details' in str(w.cget('text'))).invoke();root.update()
            assert app.mounting_plan['site']['roof_reference']=='ZONE CHANTIER'
            assert not app.mounting_auto_cotes.get() is False
            # Local recovery/save/load includes mounting and the existing data model.
            data=app._collect_project_data();assert data['mounting_plan']['panels'][uid]['positions']['0']==600
            from project_store import write_project
            path=Path(directory)/'roundtrip.json';write_project(path,data,app.roof_pil_img)
            app._apply_document(json.loads(path.read_text()),str(path));root.update()
            assert app.mounting_plan['panels'][uid]['positions']['0']==600
            assert app.mounting_plan['panels'][uid]['clamp_length_mm']==400
            assert app.mounting_plan['panels'][uid]['clamp_width_mm']==200
            write_svg(app,Path(directory)/'mounting.svg');write_schedule(app,Path(directory)/'mounting.csv')
            assert (Path(directory)/'mounting.svg').stat().st_size>1000
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                app._fit_mounting();root.update()
                from PIL import ImageGrab
                ImageGrab.grab().save(str(Path(os.environ['PV_MOUNTING_CAPTURE'])/'plan.png'))
            # Old JSON must reset the new plan, even after opening a configured project.
            data.pop('mounting_plan');app._apply_document(data,str(path));root.update()
            assert not app.mounting_plan['panels'] and not app.mounting_plan['dimensions']
            # Two fixing types on a 3 x 3 field: mixed outer panels, manual
            # assignment, boundary selection, undo and persistent exports.
            from mounting import empty_plan
            app.panel_width_mm=1000.;app.panel_height_mm=2000.
            app.model_settings.update(module_gap_width_mm=20.,module_gap_length_mm=20.)
            app.roof_zones=[dict(id=1,x1=100.,y1=100.,x2=404.,y2=704.,angle_deg=0.)]
            app.mounting_plan=empty_plan();app.generate_panels_from_zones();root.update()
            assert len(app.panels)==9
            app.mounting_plan['panels']={uid:default_config(1000,2000) for uid in app.panel_uids.values()}
            app.draw_grid();root.update();app._open_mounting_edges();root.update()
            dialog=app._mounting_edges_dialog
            entries=[w for w in walk(dialog) if isinstance(w,ttk.Entry)]
            for entry,value in zip(entries,('MID-100','100','60','END-160','160','80','50')):
                entry.delete(0,'end');entry.insert(0,value)
            root.update()
            assert not app.mounting_plan['edge_rules']['enabled'],'Edge preview must not commit'
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                from PIL import ImageGrab
                ImageGrab.grab().save(str(Path(os.environ['PV_MOUNTING_CAPTURE'])/'bordures.png'))
            next(w for w in walk(dialog) if isinstance(w,ttk.Button) and str(w.cget('text'))=='Apply to project').invoke();root.update()
            fs=[f for item in app._mounting_items.values() for f in item['fixings']]
            assert sum(f['kind']=='edge' for f in fs)==12 and sum(f['kind']=='intermediate' for f in fs)==24
            middle=app.panel_uids[(1,1)];left=app.panel_uids[(1,0)]
            assert [f['kind'] for f in app._mounting_items[left]['fixings']]==['edge','intermediate','edge','intermediate']
            app._select_boundary_panels();root.update()
            assert len(app.selected_panel_coords)==8 and (1,1) not in app.selected_panel_coords
            app._mounting_selected_fixing=(middle,0);app.selected_panel_coords={(1,1)}
            app._change_mounting_types('edge');root.update()
            assert app._mounting_items[middle]['fixings'][0]['forced']
            assert app._mounting_items[middle]['fixings'][0]['length_mm']==160
            app.undo_project();root.update()
            assert app._mounting_items[middle]['fixings'][0]['kind']=='intermediate'
            app.redo_project();root.update()
            assert app._mounting_items[middle]['fixings'][0]['kind']=='edge'
            app._mounting_selected_fixing=(middle,0);app._change_mounting_types('auto');root.update()
            assert app._mounting_items[middle]['fixings'][0]['kind']=='intermediate'
            app._select_boundary_panels();app._change_mounting_types('edge',panels=True);root.update()
            fs=[f for item in app._mounting_items.values() for f in item['fixings']]
            assert sum(f['kind']=='edge' for f in fs)==32 and sum(f['kind']=='intermediate' for f in fs)==4
            app._open_fixing_dimensions();root.update()
            assert app._mounting_edges_dialog.winfo_exists()
            next(w for w in walk(app._mounting_edges_dialog) if isinstance(w,ttk.Button) and str(w.cget('text'))=='Cancel').invoke()
            # Main station editor also previews effective profiles.
            app._open_mounting_config();root.update()
            next(w for w in walk(app._mounting_dialog) if isinstance(w,ttk.Button) and str(w.cget('text'))=='Cancel').invoke()
            data=app._collect_project_data();write_project(path,data,app.roof_pil_img)
            app._apply_document(json.loads(path.read_text()),str(path));root.update()
            assert app.mounting_plan['edge_rules']['enabled']
            assert len(app.mounting_plan['edge_rules']['overrides'])==8
            write_schedule(app,Path(directory)/'edges.csv');write_svg(app,Path(directory)/'edges.svg')
            import csv
            with (Path(directory)/'edges.csv').open(encoding='utf-8-sig') as stream:rows=list(csv.reader(stream,delimiter=';'))
            assert sum(row[9]=='End' for row in rows[1:])==32
            assert 'END-160' in (Path(directory)/'edges.svg').read_text()
            # Exercise the actual Save, recovery and Open entry points with all
            # mounting fields, not only the low-level JSON writer.
            app.mounting_plan['template']=copy.deepcopy(app.mounting_plan['panels'][middle])
            app.mounting_plan['panels'][middle]['positions']['0']=515.5
            app.mounting_plan['dimensions']=[dict(p1=[0,0],p2=[1,1],label=label,axis=axis,
                ref1=dict(uid=middle,kind='corner',index=0),ref2=dict(uid=middle,kind='fixing',index=index))
                for axis,label,index in (('aligned',[175,330],0),('horizontal',[250,270],1),('vertical',[360,330],0))]
            app.draw_grid();root.update()
            from project_store import serial
            expected=serial(app.mounting_plan)
            with patch('mixins.safe_project.messagebox.showinfo'):
                assert app.save_project(destination=str(path))
            assert app.save_project(silent=True)
            recovery=path.parent/'.recovery'/f'{app.project_uid}.json'
            assert json.loads(path.read_text())['mounting_plan']==expected
            assert json.loads(recovery.read_text())['mounting_plan']==expected
            app.mounting_plan=empty_plan()
            with patch.object(app,'_confirm_unsaved',return_value=True):
                assert app._load_project_file(str(path))
            assert serial(app.mounting_plan)==expected
            assert serial(app._project_snapshot()['mounting_plan'])==expected
            from energy_engine import freeze_app
            frozen=freeze_app(app)
            assert serial(frozen.mounting_plan)==expected
            assert frozen.mounting_plan is not app.mounting_plan
            # The real engineering report path includes the new vector pages,
            # companion SVG/PDF assets and the complete project snapshot.
            from engineering_report import export_report
            report_path=Path(os.environ.get('PV_MOUNTING_CAPTURE',directory))/'rapport_montage_recette.pdf'
            with patch('report_studies.annual_shadow',return_value={'year':2026,'missing':['Recette du montage : étude annuelle non exécutée']}):
                exported=export_report(frozen,report_path)
            import fitz
            pdf=fitz.open(report_path)
            montage=[p for p in pdf if 'Mounting / dimensioned general plan' in p.get_text()]
            assert len(montage)==1
            assert not montage[0].get_images(),'Mounting drawing must stay vector in the final report'
            assert len(montage[0].get_drawings())>40
            report_assets=report_path.with_name(report_path.stem+'_assets')
            assert json.loads((report_assets/'project_inputs.json').read_text())['mounting_plan']==expected
            assert (report_assets/'mounting_general.svg').exists()
            assert 'latex' not in exported and not report_path.with_suffix('.tex').exists()
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                for i,p in enumerate(pdf):
                    if 'MOUNTING /' in p.get_text():p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(report_path.parent/f'rapport-page-{i+1:02d}.png')
            print(f'Engineering report: {exported["pages"]} pages, vector mounting sheets, input snapshot verified (no LaTeX)')
            if os.environ.get('PV_MOUNTING_CAPTURE'):
                app._fit_mounting();root.update()
                ImageGrab.grab().save(str(Path(os.environ['PV_MOUNTING_CAPTURE'])/'plan-bordures.png'))
            # All old fixed-index tabs still activate, with no callback errors.
            for index in range(11):
                app.ribbon_notebook.select(index);root.update()
            # A larger field exercises the actual canvas/image zoom path.
            app.roof_zones=[dict(id=1,x1=0.,y1=0.,x2=2038.,y2=5048.,angle_deg=0.)]
            app._recalculate_zone_grids()
            app.panels={(r,c):r*20+c+1 for r in range(25) for c in range(20)}
            app.mounting_plan=empty_plan();app.panel_blocks={};app._mounting_selected_fixing=None
            app.roof_pil_img=Image.new('RGB',(3000,5500),'#fafcfb')
            # Test setup edits project dictionaries directly. The phase-5
            # contract requires an explicit state boundary before painting.
            app._reconcile_project_state()
            app.draw_grid();root.update();app._fit_mounting();root.update();app._mounting_zoom(6);root.update()
            assert len(app._mounting_items)==500
            import time,statistics
            frames=[];ids=app.canvas.find_withtag('mounting_geometry')
            with patch('mixins.mounting_view.geometry',side_effect=AssertionError('Geometry rebuilt during zoom')):
                for step in range(10):
                    start=time.perf_counter()
                    app._mounting_zoom(1.03 if step%2==0 else 1/1.03)
                    root.update_idletasks();frames.append(time.perf_counter()-start)
            assert app.canvas.find_withtag('mounting_geometry')==ids
            assert not errors,errors
            print('PASS: real Shift-click/double-click at multiple zooms; drag threshold; seven menus; Layout-style labels; retained/pointer-anchored/coalesced zoom; 11 tabs; mounting editing, dimensions and boundary profiles; undo/redo; Save/Open/recovery; vector engineering report; SVG/CSV exports')
            print(f'500-panel native zoom with 3000 x 5500 background: median {statistics.median(frames)*1000:.1f} ms/frame; geometry items retained')
        finally:
            root.destroy();os.chdir(previous)


if __name__=='__main__':run()
