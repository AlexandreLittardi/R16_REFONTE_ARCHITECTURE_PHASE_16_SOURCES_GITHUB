"""Tk regression for phase-13 spreadsheet/material edit transactions."""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from mixins.material_tools import MATERIAL_CATEGORY_DEFS


def run():
    with tempfile.TemporaryDirectory() as td:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(td) / 'recent.json')
        root = tk.Tk()
        root.geometry('1320x860')
        errors = []
        root.report_callback_exception = lambda *exc: errors.append(exc)
        try:
            app = PVLayoutRibbonApp(root)
            app.ribbon_notebook.select(app.tab_material)
            root.update()
            app._record_history()
            start = app._history_index
            app.spreadsheet_selected = (0, 0)
            app._spreadsheet_start_edit()
            app.spreadsheet_edit_entry.delete(0, tk.END)
            app.spreadsheet_edit_entry.insert(0, '=15*2')
            app._spreadsheet_finish_edit()
            assert app.material_spreadsheet['cells']['A1'] == '=15*2'
            assert app._history_index == start+1, ('cell', start, app._history_index)
            app.undo_project()
            assert 'A1' not in app.material_spreadsheet['cells']
            app.redo_project()
            assert app.material_spreadsheet['cells']['A1'] == '=15*2'

            app.spreadsheet_selected = (0, 1)
            root.clipboard_clear()
            root.clipboard_append('hello\t8\n=1+2\tvalue')
            before=app._history_index
            app._spreadsheet_paste()
            assert app.material_spreadsheet['cells']['B1']=='hello'
            assert app.material_spreadsheet['cells']['C1']=='8'
            assert app.material_spreadsheet['cells']['B2']=='=1+2'
            assert app._history_index==before+1, ('paste',before,app._history_index)
            app.undo_project()
            assert 'B1' not in app.material_spreadsheet['cells']
            assert app.material_spreadsheet['cells']['A1']=='=15*2'
            app.redo_project()
            assert app.material_spreadsheet['cells']['C1']=='8'
            before=app._history_index
            app._spreadsheet_paste()
            assert app._history_index==before, 'Repeated paste is a no-op'

            before=app._history_index
            app._add_spreadsheet_row()
            assert app._history_index==before+1
            app.undo_project()
            assert app.material_spreadsheet['rows']==20
            app.redo_project()
            assert app.material_spreadsheet['rows']==21

            # Resize is one history step even after many B1-Motion callbacks.
            app._rebuild_spreadsheet_grid()
            root.update()
            old_width=app._spreadsheet_col_w(0)
            before=app._history_index
            x=old_width
            app._on_spreadsheet_colheader_press(SimpleNamespace(x=x))
            assert app._canvas_edit_gate.active
            for dx in (12,25,35):
                app._on_spreadsheet_colheader_drag(SimpleNamespace(x=x+dx))
            assert app._history_index==before
            app._on_spreadsheet_colheader_release(SimpleNamespace(x=x+35))
            assert app._history_index==before+1
            assert app._spreadsheet_col_w(0)!=old_width
            app.undo_project()
            assert app._spreadsheet_col_w(0)==old_width
            app.redo_project()

            # Fill-handle relative references also forms one undoable action.
            app.spreadsheet_selected=(0, 0)
            app.spreadsheet_range_anchor=(0, 0)
            app.spreadsheet_range_end=(0, 0)
            before=app._history_index
            app._spreadsheet_fill_to((2, 0))
            assert app.material_spreadsheet['cells']['A3']=='=15*2'
            assert app._history_index==before+1
            app.undo_project()
            assert 'A3' not in app.material_spreadsheet['cells']
            app.redo_project()
            assert app.material_spreadsheet['cells']['A3']=='=15*2'

            # A row insertion in the existing equipment/material dialog.
            category = next(iter(MATERIAL_CATEGORY_DEFS))
            initial = len(app.material_categories[category]['rows'])
            before=app._history_index
            app._add_material_row(category)
            assert len(app.material_categories[category]['rows'])==initial+1
            assert app._history_index==before+1
            app.undo_project()
            assert len(app.material_categories[category]['rows'])==initial
            app.redo_project()
            assert len(app.material_categories[category]['rows'])==initial+1

            # Material cell editing is committed explicitly, not by polling.
            editor = app.material_cell_widgets[category][(initial, 0)]
            editor.delete(0, tk.END)
            editor.insert(0, 'Phase 13 supplier')
            before = app._history_index
            app._on_material_cell_commit(category, initial, 0)
            assert app.material_categories[category]['rows'][initial]['Marque']=='Phase 13 supplier'
            assert app._history_index==before+1
            app.undo_project()
            assert app.material_categories[category]['rows'][initial].get('Marque','')==''
            app.redo_project()
            assert app.material_categories[category]['rows'][initial]['Marque']=='Phase 13 supplier'

            # Save/load remains backward compatible with existing JSON schema.
            path=Path(td)/'phase13.json'
            with patch('mixins.safe_project.messagebox.showinfo'):
                assert app.save_project(destination=path)
            assert app._load_project_file(path)
            assert app.material_spreadsheet['cells']['C1']=='8'
            assert len(app.material_categories[category]['rows'])==initial+1

            # Import a foreign spreadsheet as a single reversible command.
            csv_path=Path(td)/'workbook.csv'
            csv_path.write_text('=2*3;Engineering\n4;5\n', encoding='utf-8')
            before=app._history_index
            with patch('mixins.spreadsheet_tools.filedialog.askopenfilename',return_value=str(csv_path)), \
                 patch('mixins.spreadsheet_tools.messagebox.askyesno',return_value=True):
                app._import_spreadsheet_csv()
            assert app.material_spreadsheet['cells']['A1']=='=2*3'
            assert app._history_index==before+1
            app.undo_project()
            assert app.material_spreadsheet['cells']['C1']=='8'
            app.redo_project()
            assert app.material_spreadsheet['cells']['A1']=='=2*3'
            before=app._history_index
            with patch('mixins.spreadsheet_tools.messagebox.askyesno',return_value=True):
                app._clear_spreadsheet()
            assert app.material_spreadsheet['cells']=={}
            assert app._history_index==before+1
            app.undo_project()
            assert app.material_spreadsheet['cells']['A1']=='=2*3'
            assert not errors, errors
            print('PASS phase13: sheet cell, paste, row, resize, material row, Undo/Redo, JSON')
        finally:
            root.destroy()


if __name__ == '__main__':
    run()
