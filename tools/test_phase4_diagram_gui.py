"""Live phase 4 regression: grouped drag undo/redo and native JSON roundtrip."""
import copy
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from domain.diagram_commands import add_custom_node, add_manual_link, delete_nodes


def run():
    with tempfile.TemporaryDirectory() as folder:
        os.environ['PV_APP_RECENTS_FILE']=str(Path(folder)/'recent.json')
        root=tk.Tk()
        failures=[]
        root.report_callback_exception=lambda *args:failures.append(args)
        try:
            app=PVLayoutRibbonApp(root)
            root.update()
            original=set(app.diagram_nodes)
            app._record_history()  # settle the initial deferred Tk state
            baseline=app._history_index
            edit=add_custom_node(app.diagram_nodes,app.diagram_links,'custom::900','Phase4 meter')
            assert app._apply_diagram_edit(edit)
            assert 'custom::900' in app.diagram_nodes
            assert app._history_index==baseline+1,(app._history_index,baseline)
            app.undo_project()
            assert 'custom::900' not in app.diagram_nodes, app.diagram_nodes
            app.redo_project()
            assert 'custom::900' in app.diagram_nodes
            # Manual node movement is one event even across many intermediate frames.
            app._diagram_layout_applied=app._diagram_layout_signature()
            original_pos={key: (app.diagram_nodes[key]['x'],app.diagram_nodes[key]['y']) for key in ('custom::900',)}
            before=app._history_index
            app._begin_diagram_gesture()
            for delta in (2,4,7,10,14):
                app._preview_diagram_move(original_pos,delta,6)
                assert app._history_index==before
            app._finish_diagram_gesture()
            assert app._history_index==before+1,(app._history_index,before)
            x=app.diagram_nodes['custom::900']['x']
            app.undo_project()
            assert app.diagram_nodes['custom::900']['x']==original_pos['custom::900'][0]
            app.redo_project()
            assert app.diagram_nodes['custom::900']['x']==x
            # Link with a different custom device; endpoints and extensions persist.
            new=add_custom_node(app.diagram_nodes,app.diagram_links,'custom::901','Phase4 switch')
            app._apply_diagram_edit(new)
            link=add_manual_link(app.diagram_nodes,app.diagram_links,'custom::900','custom::901',
                                 style='dotted',distance_m=7.5)
            assert app._apply_diagram_edit(link)
            path=Path(folder)/'phase4_project.json'
            with patch('mixins.safe_project.messagebox.showinfo'), \
                 patch('mixins.safe_project.messagebox.askyesnocancel',return_value=False):
                assert app.save_project(destination=str(path))
                assert app._load_project_file(str(path))
            assert 'custom::901' in app.diagram_nodes
            assert any(l.get('a')=='custom::900' and l.get('b')=='custom::901'
                       and l.get('distance_m')==7.5 and l.get('style')=='dotted'
                       for l in app.diagram_links)
            # The renderer is read-only: topology/layout preparation is separate.
            snapshot=copy.deepcopy(app.diagram_nodes)
            app._draw_diagram()
            assert app.diagram_nodes==snapshot, 'Painting mutated diagram data'
            # Deleting two nodes and undoing must restore every custom link.
            before=app._history_index
            deletion=delete_nodes(app.diagram_nodes,app.diagram_links,{'custom::900','custom::901'})
            app._apply_diagram_edit(deletion)
            assert app._history_index==before+1
            app.undo_project()
            assert 'custom::900' in app.diagram_nodes and 'custom::901' in app.diagram_nodes
            assert any(l.get('a')=='custom::900' and l.get('b')=='custom::901'
                       for l in app.diagram_links)
            # Repainting and camera zoom are not user geometry edits.
            app.ribbon_notebook.select(app.tab_diagram)
            root.update_idletasks()
            app._diagram_layout_applied=app._diagram_layout_signature()
            positions={key:(node['x'],node['y']) for key,node in app.diagram_nodes.items()}
            before=app._history_index
            app._zoom_button_change(1.1)
            app.draw_grid()
            assert positions=={key:(node['x'],node['y']) for key,node in app.diagram_nodes.items()}
            app._record_history()
            assert app._history_index==before, 'Zoom forked edit history'
            assert not failures,failures
            print('PASS GUI diagram: create/link/drag/delete, grouped undo/redo, JSON roundtrip')
        finally:
            root.destroy()


if __name__=='__main__':
    run()
