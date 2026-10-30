"""Real Tk test: apply physical intermediate clamp clearance to global Layout."""
import os,sys,tempfile,math
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from app import PVLayoutRibbonApp
from mounting import default_config
from mounting_drawing import geometry
from mounting_spacing import nearest_gaps
from mounting_quantities import fixing_inventory
from mounting_installer import write_installer_pdf

def descend(w):
    for child in w.winfo_children():
        yield child
        yield from descend(child)

def run():
    from PIL import Image
    import fitz
    with tempfile.TemporaryDirectory() as td:
        old=os.getcwd();os.chdir(td)
        os.environ['PV_APP_RECENTS_FILE']=str(Path(td)/'recents.json')
        root=tk.Tk();root.geometry('1500x1000');errors=[]
        root.report_callback_exception=lambda *a:errors.append(a)
        try:
            app=PVLayoutRibbonApp(root);root.update()
            app.panel_width_mm=1000;app.panel_height_mm=2000;app.px_per_mm=.1
            app.entry_width.delete(0,'end');app.entry_width.insert(0,'1000')
            app.entry_height.delete(0,'end');app.entry_height.insert(0,'2000')
            app.roof_pil_img=Image.new('RGB',(800,700),'white')
            app.roof_zones=[dict(id=1,x1=100,y1=100,x2=450,y2=340,angle_deg=0)]
            app.generate_panels_from_zones()
            root.update()
            coords=sorted(app.panels)[:2]
            assert coords[0][0]==coords[1][0],coords
            for coord in list(app.panels):
                if coord not in coords:
                    app.panels.pop(coord)
                    app.panel_uids.pop(coord,None)
            for c in coords:
                app.mounting_plan['panels'][app.panel_uids[c]]=default_config(1000,2000)
            app.ribbon_notebook.select(app.tab_mounting);root.update()
            before=nearest_gaps(geometry(app),app.px_per_mm)
            assert any(v['u'] is not None and v['u'][1]<1 for v in before.values()),before
            app._open_mounting_edges();root.update()
            win=app._mounting_edges_dialog
            entries=[w for w in descend(win) if isinstance(w,ttk.Entry)]
            assert len(entries)==8,len(entries)
            joint=entries[-1]
            joint.delete(0,'end');joint.insert(0,'25')
            root.update()
            button=next(w for w in descend(win) if isinstance(w,ttk.Button) and w.cget('text')=='Apply to project')
            assert str(button.cget('state'))!='disabled',[(w.cget('text')) for w in descend(win) if isinstance(w,ttk.Label)][-4:]
            with patch('mixins.mounting_edges_ui.messagebox.askyesno',return_value=True):
                button.invoke()
            root.update()
            assert not win.winfo_exists()
            assert app.model_settings['module_gap_width_mm']==25,app.model_settings
            assert app.mounting_plan['edge_rules']['joint_gap_mm']==25
            after=nearest_gaps(geometry(app),app.px_per_mm)
            gap=next(v['u'][1] for v in after.values() if v['u'] is not None)
            assert abs(gap-25)<.01,(gap,after)
            inv=fixing_inventory(geometry(app),app.px_per_mm,app.mounting_plan['edge_rules']['max_gap_mm'])
            assert inv['pieces_by_kind']=={'edge':4,'intermediate':2},inv
            out=Path(td)/'pose.pdf';result=write_installer_pdf(app,out)
            doc=fitz.open(out);pdftext=' '.join(page.get_text() for page in doc)
            assert 'CLAMP BILL OF MATERIALS' in pdftext and '25.0' in pdftext
            assert result['fixing_pieces']==6
            assert not errors,str(errors)
            print('PASS live Tk -> 25 mm Layout clearance -> accurate coordinates -> physical clamp BOM -> vector A3 PDF')
        finally:
            root.destroy();os.chdir(old)
if __name__=='__main__':run()
