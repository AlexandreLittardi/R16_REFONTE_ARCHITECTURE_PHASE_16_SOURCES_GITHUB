"""Live Tk MPPT drop/auto/clear Undo/Redo regression (phase 12)."""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp


def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(tmp) / 'recent.json')
        root = tk.Tk()
        root.geometry('1320x850')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            app.panels = {(0, 0): 1, (0, 1): 2, (0, 2): 3}
            app.panel_blocks = {(0, 0): 'INV', (0, 1): 'INV', (0, 2): 'INV'}
            app.blocks = {'INV': {'color': '#456789', 'mppt_count': 2,
                                   'max_strings_per_mppt': 2}}
            app.strings = {'S1': [(0, 0)], 'S2': [(0, 1)], 'S3': [(0, 2)]}
            app.string_mppt_assignment = {}
            from domain.serialization import fingerprint
            app.layout_geometry = {f'{r},{c}': fingerprint(app._panel_rect((r,c)))
                                   for r,c in app.panels}
            app._refresh_equipment_tree()
            # This harness supplies fixed panels, without a generating roof zone.
            # Keep the Installation zone allocator from reflowing that fixture.
            allocator = patch.object(app, '_recalculate_zone_grids', return_value=None)
            allocator.start()
            app._record_history()
            before = app._history_index
            assert app.equip_tree.exists('string::S1')
            assert app.equip_tree.exists('mppt::INV::1')

            # The exact Treeview button release callback owns the edit boundary.
            def drop(source, destination):
                app._equip_drag_item = source
                with patch.object(app.equip_tree, 'identify_row', return_value=destination):
                    app._on_equip_tree_release(SimpleNamespace(y=10))

            drop('string::S1', 'mppt::INV::1')

            assert app.string_mppt_assignment['S1']['mppt'] == 1
            assert app._history_index == before + 1, ('first drop', before, app._history_index)

            app.undo_project()

            assert 'S1' not in app.string_mppt_assignment

            app.redo_project()

            assert app.string_mppt_assignment['S1']['mppt'] == 1

            # No-op repeat must preserve history position and redo chain.
            before = app._history_index
            drop('string::S1', 'mppt::INV::1')
            assert app._history_index == before
            with patch('mixins.equipment_tools.messagebox.showinfo'):
                drop('string::S1', 'block::INV')  # informational target; no edit
            assert app._history_index == before

            # A full MPPT rejects an additional string without a history step.
            drop('string::S2', 'mppt::INV::1')
            assert app.string_mppt_assignment['S2']['mppt'] == 1
            before_full = app._history_index
            with patch('mixins.equipment_tools.messagebox.showerror') as error:
                drop('string::S3', 'mppt::INV::1')
                assert error.called
            assert 'S3' not in app.string_mppt_assignment
            assert app._history_index == before_full
            app.undo_project()  # undo S2 only, retain S1
            assert 'S2' not in app.string_mppt_assignment
            assert app.string_mppt_assignment['S1']['mppt'] == 1
            before = app._history_index

            # A drop on 'unassigned' is a single undoable edit.
            drop('string::S1', 'unassigned')
            assert 'S1' not in app.string_mppt_assignment
            assert app._history_index == before + 1
            app.undo_project()
            assert app.string_mppt_assignment['S1']['mppt'] == 1
            app.redo_project()
            assert 'S1' not in app.string_mppt_assignment

            # Actual Equipment action menu callbacks, including modal prompts.
            menu_btn = next(w for w in app.tab_equipment.winfo_children()
                            if isinstance(w, tk.ttk.Menubutton) and 'MPPT actions' in w.cget('text'))
            menu = menu_btn['menu']
            menu_widget = root.nametowidget(menu)
            with patch('mixins.equipment_tools.messagebox.showinfo'):
                before = app._history_index
                menu_widget.invoke(0)  # auto assign
                assert len(app.string_mppt_assignment) == 3
                assert app._history_index == before + 1
            with patch('mixins.equipment_tools.messagebox.askyesno', return_value=False):
                before = app._history_index
                menu_widget.invoke(1)  # cancelled Clear
                assert app._history_index == before
            with patch('mixins.equipment_tools.messagebox.askyesno', return_value=True):
                before = app._history_index
                menu_widget.invoke(1)
                assert not app.string_mppt_assignment
                assert app._history_index == before + 1
            app.undo_project()
            assert len(app.string_mppt_assignment) == 3
            app.redo_project()
            assert not app.string_mppt_assignment
            assert not errors, errors
            print('PASS phase12: real tree drops and Equipment menus, no-op/cancel, Undo/Redo')
        finally:
            if 'allocator' in locals():
                allocator.stop()
            root.destroy()


if __name__ == '__main__':
    run()
