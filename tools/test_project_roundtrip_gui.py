"""Optional GUI integration check against a real v2 project JSON.

Usage: xvfb-run -a python tools/test_frimo_project_roundtrip.py path/to/project.json
No Frimo-specific data is embedded in the R16 source distribution.
"""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from infrastructure.json_repository import ProjectRepository


def test(path):
    repo=ProjectRepository()
    expected=repo.read(path)
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(tmp)/'recent.json')
        root=tk.Tk()
        root.geometry('1280x800')
        errors=[]
        root.report_callback_exception=lambda *err:errors.append(err)
        try:
            app=PVLayoutRibbonApp(root)
            root.update()
            with patch('mixins.safe_project.messagebox.askyesnocancel',return_value=False), \
                 patch('mixins.safe_project.messagebox.showerror') as showerror:
                loaded=app._load_project_file(str(path))
            assert loaded,showerror.call_args_list
            root.update()
            assert len(app.ribbon_notebook.tabs())==11
            current=app._collect_project_data()
            for k in ('panels','strings','roof_zones','roof_polygons',
                      'cable_paths','panel_uids','mounting_plan','roof_image_offset'):
                actual=current.get(k)
                expected_value=expected.get(k)
                if k=='roof_polygons':
                    actual=[{**area,'points':[list(pt) for pt in area['points']]} for area in actual]
                assert actual==expected_value,(k,str(actual)[:90],str(expected_value)[:90])
            destination=Path(tmp)/'full_cycle.json'
            repo.write(destination,current)
            roundtrip=repo.read(destination)
            for k in ('panels','strings','roof_zones','roof_polygons',
                      'cable_paths','panel_uids','mounting_plan','roof_image_offset'):
                assert roundtrip.get(k)==expected.get(k),k
            assert not errors,errors
            print('PASS loaded, edited-boundary saved and reloaded:',
                  len(app.panels),'panels,',len(app.roof_zones),'zones,',
                  len(app.roof_polygons),'routing areas,',len(app.strings),'strings')
        finally:root.destroy()

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python tools/test_frimo_project_roundtrip.py project.json')
    test(Path(sys.argv[1]))
