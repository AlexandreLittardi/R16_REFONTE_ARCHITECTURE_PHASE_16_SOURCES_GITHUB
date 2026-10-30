"""Live Tk test: Phase 10 ribbon/dialog edits are immediately undoable."""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(directory) / 'recent.json')
        root = tk.Tk()
        root.geometry('1300x850')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            assert len(app.ribbon_notebook.tabs()) == 11

            # A grid connection dialog's Apply button must immediately commit.
            original = dict(app.grid_connection_settings)
            app._record_history()
            before = app._history_index
            app._show_grid_configuration()
            dialog = [w for w in root.winfo_children()
                      if isinstance(w, tk.Toplevel) and w.title() == 'Grid connection'][-1]
            for child in dialog.winfo_children():
                if isinstance(child, tk.Entry) or isinstance(child, __import__('tkinter').ttk.Entry):
                    child.delete(0, tk.END)
                    child.insert(0, '175')
            apply = [w for w in dialog.winfo_children()
                     if isinstance(w, __import__('tkinter').ttk.Button) and w.cget('text') == 'Apply'][0]
            apply.invoke()
            assert app.grid_connection_settings['existing_contract_kw'] == 175
            assert app._history_index == before + 1, ('grid commit', before, app._history_index)
            app.undo_project()
            assert app.grid_connection_settings == original
            app.redo_project()
            assert app.grid_connection_settings['existing_contract_kw'] == 175

            # Block create/delete uses actual ribbon methods with modal dialogs.
            app._record_history()
            before = app._history_index
            with patch('mixins.canvas_grid.simpledialog.askstring', return_value='Phase10Block'):
                app._run_project_edit('layout:new-block', app.create_new_block)
            assert 'Phase10Block' in app.blocks
            assert app._history_index == before + 1
            app.undo_project()
            assert 'Phase10Block' not in app.blocks
            app.redo_project()
            assert 'Phase10Block' in app.blocks

            # A cancelled command creates no extra history record.
            before = app._history_index
            with patch('mixins.canvas_grid.simpledialog.askstring', return_value=None):
                app._run_project_edit('layout:new-block', app.create_new_block)
            assert app._history_index == before

            # Zone settings button edit (inputs change, not the data until Apply).
            app.px_per_mm = 2.0
            app.roof_zones = [dict(id=1, x1=100.,y1=80.,x2=500.,y2=380.,
                                   w_mm=200., h_mm=150., angle_deg=0.,
                                   align_x='Centre',align_y='Centre')]
            app.active_zone_idx = 0
            app._recalculate_zone_grids()
            app._update_zone_entries_from_active()
            app._record_history()
            before = app._history_index
            app.entry_zone_x.delete(0, tk.END)
            app.entry_zone_x.insert(0, '75')
            buttons = [w for w in app.zone_params_frame.winfo_children()
                       if isinstance(w, __import__('tkinter').ttk.Button) and w.cget('text') == 'Apply changes']
            assert buttons, 'Zone settings ribbon callback missing'
            buttons[0].invoke()
            assert round(app.roof_zones[0]['x1']) == 150
            assert app._history_index == before + 1, ('zone commit', before, app._history_index)
            app.undo_project()
            assert round(app.roof_zones[0]['x1']) == 100
            app.redo_project()
            assert round(app.roof_zones[0]['x1']) == 150

            assert not errors, errors
            print('PASS phase10: grid dialog, block ribbon and zone settings Undo/Redo; cancelled command no-op')
        finally:
            root.destroy()


if __name__ == '__main__':
    main()
