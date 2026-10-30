"""Phase 5 integration: repaint/zoom cannot commit wiring/UIDs/shadow history."""
import copy
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from application.diagram_projection import wiring_signature


def run():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(directory)/'recent.json')
        root=tk.Tk()
        root.geometry('1200x800')
        failures=[]
        root.report_callback_exception=lambda *args:failures.append(args)
        try:
            app=PVLayoutRibbonApp(root)
            root.update()
            # A representative edit from a not-yet-migrated controller:
            # the data changes directly; the next history/IO/tab boundary
            # repairs the derived state, NOT an arbitrary repaint or zoom.
            app.panels={(0,0):1,(0,1):2}
            app.panel_uids={(0,0):'stable-id'}
            app.strings={'String 1':[(0,0),(0,1)]}
            app.blocks={'INV':{'color':'#445566','mppt_count':2,'max_strings_per_mppt':2}}
            app.string_mppt_assignment={'String 1':{'block':'INV','mppt':1}}
            app.shadow_result={'source_signature':'outdated','shadowed':set()}
            old_signature=app._diagram_signature
            old_shadow=copy.deepcopy(app.shadow_result)
            app.ribbon_notebook.select(app.tab_layout)
            root.update()
            # First tab change is an edit boundary and intentionally commits.
            assert set(app.panel_uids)==set(app.panels)
            assert app.panel_uids[(0,0)]=='stable-id'
            assert app.shadow_result=={}
            assert app._diagram_signature==wiring_signature(app.strings,app.string_mppt_assignment,app.blocks)
            assert old_signature!=app._diagram_signature
            # Set up new pending edits AFTER the tab-change boundary.
            app.panels[(0,2)]=3
            app.strings['String 1'].append((0,2))
            app.shadow_result={'source_signature':'stale','shadowed':set()}
            stale_signature=app._diagram_signature
            shadow=copy.deepcopy(app.shadow_result)
            existing_uids=dict(app.panel_uids)
            for _ in range(3):
                app.draw_grid()
            assert app.panel_uids==existing_uids,'Painting allocated persistent panel UIDs'
            assert app.shadow_result==shadow,'Painting invalidated cached shadow data'
            assert app._diagram_signature==stale_signature,'Painting reconciled wiring'
            # History is a domain commit boundary, including legacy direct edits.
            app._record_history()
            assert set(app.panel_uids)==set(app.panels)
            assert app.panel_uids[(0,0)]=='stable-id'
            assert app.shadow_result=={}
            assert app._diagram_signature==wiring_signature(app.strings,app.string_mppt_assignment,app.blocks)
            # Switching directly to Mounting also commits pending UID changes.
            app.panels[(0,3)]=4
            app.ribbon_notebook.select(app.tab_mounting)
            root.update()
            assert (0,3) in app.panel_uids,'Mounting opened with unreconciled panel UIDs'
            # Manual polygon handles moved out of the legacy draw_grid override
            # and into the single common scene painter.
            app.ribbon_notebook.select(app.tab_roof)
            root.update()
            app.roof_polygons=[{'id':1,'points':[(25,20),(80,20),(80,50),(25,50)]}]
            app.path_mode='select_polygon'
            app.active_polygon_idx=0
            app.draw_grid()
            white_rectangles=[item for item in app.canvas.find_all()
                              if app.canvas.type(item)=='rectangle' and app.canvas.itemcget(item,'fill')=='white']
            assert len(white_rectangles)==4, ('Expected four editable polygon vertices',white_rectangles)
            # Local save contains newly assigned UIDs with untouched project schema.
            filename=str(Path(directory)/'phase5.json')
            with patch('mixins.safe_project.messagebox.showinfo'):
                assert app.save_project(destination=filename)
            assert Path(filename).is_file()
            assert not failures,failures
            print('PASS phase 5: read-only repaint, consistency on history/tab/save, polygon handles')
        finally:
            root.destroy()


if __name__=='__main__':
    run()
