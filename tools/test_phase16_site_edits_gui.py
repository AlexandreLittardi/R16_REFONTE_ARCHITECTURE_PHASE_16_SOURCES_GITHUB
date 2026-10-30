"""Live Tk regression for Shadow and Cabling edit history (phase 16)."""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp
from infrastructure.json_repository import ProjectRepository


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(directory) / 'recent.json')
        root = tk.Tk()
        root.geometry('1320x860')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            app._auto_fit = False
            app.zoom_level = 1.0
            app.px_per_mm = 2.0
            app.roof_zones = [dict(
                id=1, x1=80., y1=80., x2=380., y2=340.,
                w_mm=150., h_mm=130., z_mm=0.,
                align_x='Centre', align_y='Centre',
                custom_data={'roof': 'west'})]
            app.ribbon_notebook.select(app.tab_shadow)
            root.update()
            app._record_history(prepare_zone_grids=False)
            baseline = app._history_index

            # Real Shadow canvas click routes through CanvasGrid to the single
            # explicit edit (all intermediate movement/state updates are private).
            app.shadow_mode = 'place_ref'
            cx, cy = 120, 130
            event = SimpleNamespace(x=cx-app.canvas.canvasx(0),
                                    y=cy-app.canvas.canvasy(0), state=0)
            app.on_left_press(event)
            assert app.pylon_ref_img_pos == (120., 130.), app.pylon_ref_img_pos
            assert app._history_index == baseline + 1, (baseline, app._history_index)
            app.undo_project()
            assert app.pylon_ref_img_pos is None
            app.redo_project()
            assert app.pylon_ref_img_pos == (120., 130.)

            app._place_shadow_image_point('obstacle', 150, 160)
            assert app.pylon_img_pos == (150., 160.)
            before = app._history_index
            # Identical placement adds no history record.
            app._place_shadow_image_point('obstacle', 150, 160)
            assert app._history_index == before

            app.entry_pylon_dx.delete(0, tk.END)
            app.entry_pylon_dx.insert(0, '18')
            app.entry_pylon_dy.delete(0, tk.END)
            app.entry_pylon_dy.insert(0, '-12')
            app._apply_pylon_delta_position()
            assert app.pylon_img_pos == (156., 106.), app.pylon_img_pos
            app.undo_project()
            assert app.pylon_img_pos == (150., 160.)
            app.redo_project()
            assert app.pylon_img_pos == (156., 106.)

            app.active_shadow_zone_idx = 0
            app._refresh_shadow_zone_list()
            app.entry_zone_height_shadow.delete(0, tk.END)
            app.entry_zone_height_shadow.insert(0, '725')
            app._apply_shadow_zone_height()
            assert app.roof_zones[0]['z_mm'] == 725.
            assert app.roof_zones[0]['custom_data'] == {'roof': 'west'}
            app.undo_project()
            assert app.roof_zones[0]['z_mm'] == 0.
            app.redo_project()
            assert app.roof_zones[0]['z_mm'] == 725.
            # Invalid edits must be rejected before opening a transaction.
            idx = app._history_index
            app.active_shadow_zone_idx = 0  # Undo/Redo resets UI selection.
            app.entry_zone_height_shadow.delete(0, tk.END)
            app.entry_zone_height_shadow.insert(0, 'nan')
            with patch('mixins.shadow_tools.messagebox.showerror') as error:
                app._apply_shadow_zone_height()
                assert error.called
            assert app._history_index == idx

            app._clear_pylon()
            assert app.pylon_img_pos is None and app.pylon_ref_img_pos is None
            app.undo_project()
            assert app.pylon_img_pos == (156., 106.)
            assert app.pylon_ref_img_pos == (120., 130.)
            app.redo_project()
            assert app.pylon_img_pos is None

            # Cabling manual gather and reset are independent single-step edits.
            app.ribbon_notebook.select(app.tab_notes)
            root.update()
            app._auto_fit = False
            app.zoom_level = 1.0
            app.path_mode = 'place_gather_point'
            before = app._history_index
            app._place_gather_point_at(140, 150)
            assert tuple(app.roof_zones[0]['gather_point']) == (140., 150.)
            assert app.roof_zones[0]['gather_point_manual'] is True
            assert app._history_index == before + 1
            app.undo_project()
            assert not app.roof_zones[0].get('gather_point_manual')
            app.redo_project()
            assert tuple(app.roof_zones[0]['gather_point']) == (140., 150.)
            before = app._history_index
            app._reset_gather_points()
            assert app._history_index == before + 1
            assert not app.roof_zones[0].get('gather_point_manual')
            assert 'gather_point' not in app.roof_zones[0]
            app.undo_project()
            assert tuple(app.roof_zones[0]['gather_point']) == (140., 150.)
            app.redo_project()
            assert 'gather_point' not in app.roof_zones[0]
            assert app.roof_zones[0]['custom_data'] == {'roof': 'west'}
            # After undo, a genuinely new edit replaces the redo branch.
            app.undo_project()
            assert tuple(app.roof_zones[0]['gather_point']) == (140., 150.)
            app._place_gather_point_at(155, 165)
            assert tuple(app.roof_zones[0]['gather_point']) == (155., 165.)
            assert app._history_index == len(app._history) - 1
            app.undo_project()
            assert tuple(app.roof_zones[0]['gather_point']) == (140., 150.)
            app.redo_project()
            assert tuple(app.roof_zones[0]['gather_point']) == (155., 165.)
            app._reset_gather_points()
            assert 'gather_point' not in app.roof_zones[0]

            dest = Path(directory) / 'phase16.json'
            ProjectRepository().write(dest, app._collect_project_data())
            saved = ProjectRepository().read(dest).snapshot()
            assert saved['roof_zones'][0]['custom_data'] == {'roof': 'west'}
            assert saved['roof_zones'][0]['z_mm'] == 725.
            assert 'gather_point' not in saved['roof_zones'][0]
            assert len(app.ribbon_notebook.tabs()) == 11
            assert not errors, [str(x) for x in errors]
            print('PASS phase16 GUI: shadow placement/offset/height/clear, cabling gather/reset, Undo/Redo and JSON')
        finally:
            root.destroy()


if __name__ == '__main__':
    main()
