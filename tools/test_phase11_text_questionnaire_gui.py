"""Phase 11 Tk regression: one typed edit / one questionnaire Apply = one history step."""
import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(directory)/'recent.json')
        root=tk.Tk();root.geometry('1350x890')
        errors=[]
        root.report_callback_exception=lambda *args:errors.append(args)
        try:
            app=PVLayoutRibbonApp(root)
            root.update()
            app.ribbon_notebook.select(app.tab_notes)
            root.update()
            notebook=app.side_panel_notes.winfo_children()[0]
            notebook.select(app.txt_notes.master.master)
            root.update()
            app._record_history()
            baseline=app._history_index
            original=app.project_notes
            app.txt_notes.focus_force();root.update()
            assert app._canvas_edit_gate.active, 'Text focus must begin an edit'
            app.txt_notes.insert('end-1c','Phase 11 note')
            root.update()
            app._poll_history()
            assert app._history_index==baseline, 'Polling must not split typing'
            notebook.select(app.cable_entries['current_a'].master.master)
            root.update()
            app.cable_entries['current_a'].focus_force();root.update()
            assert app._history_index==baseline+1, (baseline,app._history_index)
            assert app.project_notes.endswith('Phase 11 note')
            app.undo_project()
            assert app.project_notes==original
            app.redo_project()
            assert app.project_notes.endswith('Phase 11 note')

            # Focus-based edit of cable sizing value: one history step.
            target=app.cable_entries['current_a'];target.focus_force();root.update()
            app._record_history()
            before=app._history_index
            old_value=app.cable_calc_params['current_a']
            target.delete(0,tk.END)
            target.insert(0,'12.5' if old_value!=12.5 else '13.5')
            root.update();app._poll_history()
            assert app._history_index==before
            notebook.select(app.txt_notes.master.master)
            root.update()
            app.txt_notes.focus_force();root.update()
            assert app._history_index==before+1
            now=app.cable_calc_params['current_a']
            assert now!=old_value, (now,old_value)
            app.undo_project()
            assert app.cable_calc_params['current_a']==old_value
            app.redo_project()
            assert app.cable_calc_params['current_a']==now

            # Apply the questionnaire without imports; defaults are valid.
            app._show_project_configuration()
            root.update()
            win=app._configuration_questionnaire
            assert win.winfo_exists()
            before=app._history_index
            old_name=app.project_name
            def descend(widget):
                yield widget
                for child in widget.winfo_children():
                    yield from descend(child)
            widgets=list(descend(win))
            button=next((w for w in widgets if isinstance(w,ttk.Button)
                         and w.cget('text')=='Apply all inputs'),None)
            project_label=next((w for w in widgets if isinstance(w,ttk.Label)
                                and w.cget('text').startswith('Project name')),None)
            assert button is not None and project_label is not None
            row=project_label.grid_info()['row']
            editor=next((w for w in project_label.master.winfo_children()
                        if isinstance(w,ttk.Entry) and w.grid_info().get('row')==row),None)
            assert editor is not None,'Questionnaire project-name input missing'
            editor.delete(0,tk.END);editor.insert(0,'Phase11 engineering project')
            with patch('mixins.configuration_questionnaire.messagebox.showerror') as err:
                button.invoke()
                root.update()
                assert not err.called, err.call_args
            assert not win.winfo_exists(),'Valid Apply should close the dialog'
            assert not app._canvas_edit_gate.active
            assert app._history_index==before+1, (before,app._history_index)
            assert app.project_name=='Phase11 engineering project'
            app.undo_project()
            assert app.project_name==old_name, (app.project_name,old_name)
            app.redo_project()
            assert app.project_name=='Phase11 engineering project'
            assert not errors,errors
            print('PASS phase11: notes, cable sizing, questionnaire Apply and Undo/Redo')
        finally:
            root.destroy()

if __name__=='__main__':main()
