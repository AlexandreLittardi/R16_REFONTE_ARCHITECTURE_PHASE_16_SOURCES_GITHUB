"""Exercise phase 3 edit-triggered wiring projection in a real Tk application."""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from application.events import ElectricalTopologyChanged
from application.diagram_projection import wiring_signature


def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(tmp)/'recent.json')
        root=tk.Tk()
        root.geometry('1280x800')
        failures=[]
        root.report_callback_exception=lambda *args:failures.append(args)
        try:
            app=PVLayoutRibbonApp(root)
            root.update()
            events=[]
            app._project_events.subscribe(events.append)
            app.panels={(0,0):1, (0,1):2}
            app.panel_blocks={(0,0):'INV', (0,1):'INV'}
            app.blocks={'INV':{'color':'#000000','mppt_count':2,'max_strings_per_mppt':2}}
            app.diagram_nodes['user::meter']={'type':'custom','label':'Meter','x':17,'y':23}
            # Deliberately prevent the canvas from drawing: sync must not depend
            # on the renderer for a command-owned string/MPPT modification.
            original_draw=app.draw_grid
            app.draw_grid=Mock()
            app.add_panel_to_string((0,0))
            assert isinstance(events[-1], ElectricalTopologyChanged),events
            assert app._diagram_signature==wiring_signature(app.strings,app.string_mppt_assignment,app.blocks)
            assert app.diagram_nodes['user::meter']['x']==17
            assert app.strings['String 1']==[(0,0)]
            assert app._assign_string_to_mppt('String 1','INV',1),app.strings
            assert isinstance(events[-1], ElectricalTopologyChanged),events
            assert 'str::String 1' in app.diagram_nodes, list(app.diagram_nodes)
            assert app.diagram_nodes['user::meter']['x']==17
            before=app._diagram_signature
            app._assign_string_to_mppt('String 1','INV',1)
            assert before==app._diagram_signature
            app.remove_panel_from_strings((0,0))
            assert not app.strings['String 1']
            assert app._diagram_signature==wiring_signature(app.strings,app.string_mppt_assignment,app.blocks)
            assert app.diagram_nodes['user::meter']['y']==23
            app.draw_grid=original_draw
            root.update()
            assert not failures,failures
            print('PASS GUI strings/MPPT update diagram without draw_grid, preserve custom nodes')
        finally:
            root.destroy()


if __name__=='__main__':
    run()
