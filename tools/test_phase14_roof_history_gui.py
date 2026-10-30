"""Tk test: photograph placement, calibration, dimensions and undo/redo."""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp


def run():
    with tempfile.TemporaryDirectory() as td:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(td) / 'recents.json')
        root = tk.Tk()
        root.geometry('1200x800')
        errors = []
        root.report_callback_exception = lambda *exc: errors.append(exc)
        try:
            app = PVLayoutRibbonApp(root)
            app.ribbon_notebook.select(app.tab_roof)
            root.update()
            app._auto_fit = False
            app.zoom_level = 1.0
            # The image is a user edit; Undo/Redo must restore the previous image.
            first_img = Path(td) / 'roof1.png'
            second_img = Path(td) / 'roof2.png'
            Image.new('RGB',(640,420),'white').save(first_img)
            Image.new('RGB',(720,420),'white').save(second_img)
            initial = app._history_index
            with patch('mixins.zone_tools.filedialog.askopenfilename', return_value=str(first_img)):
                app.load_roof_image()
            assert app.roof_pil_img.size == (640,420)
            assert app._history_index == initial+1, ('import', initial, app._history_index)
            app.undo_project()
            assert app.roof_pil_img is None
            app.redo_project()
            assert app.roof_pil_img.size == (640,420)
            assert app.roof_image_path == str(first_img)
            before = app._history_index
            with patch('mixins.zone_tools.filedialog.askopenfilename', return_value=''):
                app.load_roof_image()
            assert app._history_index == before

            # Calibration is a single undo step, and rejected dimensions are no-op.
            before = app._history_index
            app._run_project_edit('installation:calibration', app._apply_scale_reference,
                                  (0.,0.),(200.,0.), 100.)
            assert app.px_per_mm == 2.
            assert app._history_index == before+1
            app.undo_project()
            assert app.px_per_mm != 2.
            app.redo_project()
            assert app.px_per_mm == 2.
            before = app._history_index
            with patch('mixins.canvas_grid.simpledialog.askfloat', return_value=None):
                app._activate_scale_mode()
                app.on_left_press(SimpleNamespace(x=20,y=20,state=0))
                app.on_left_release(SimpleNamespace(x=120,y=20,state=0))
            assert app._history_index == before, 'Canceled calibration must not create history'

            # Photo offset: mouse press to release = one record irrespective of drag events.
            app._select_background_move_tool()
            root.update()
            before = app._history_index
            app.on_left_press(SimpleNamespace(x=100,y=100,state=0))
            for x,y in ((110,105), (130,120), (150,140)):
                app.on_left_drag(SimpleNamespace(x=x,y=y,state=0))
            assert app._history_index == before
            assert app.roof_image_offset == (50.,40.), app.roof_image_offset
            app.on_left_release(SimpleNamespace(x=150,y=140,state=0))
            assert app._history_index == before+1
            app.undo_project()
            assert app.roof_image_offset == (0.,0.)
            app.redo_project()
            assert app.roof_image_offset == (50.,40.)
            app._stop_background_move_tool()

            # Reset is a reversible command, and resetting twice is a no-op.
            before = app._history_index
            app._reset_background_position()
            assert app.roof_image_offset == (0.,0.)
            assert app._history_index == before+1
            app._reset_background_position()
            assert app._history_index == before+1
            app.undo_project()
            assert app.roof_image_offset == (50.,40.)
            app.redo_project()
            assert app.roof_image_offset == (0.,0.)

            # Replacement photo is distinct from calibration and independently undoable.
            # Existing scale triggers a user prompt; declining rescale still imports.
            before = app._history_index
            with patch('mixins.zone_tools.filedialog.askopenfilename', return_value=str(second_img)), \
                    patch('mixins.zone_tools.messagebox.askyesno', return_value=False):
                app.load_roof_image()
            assert app.roof_pil_img.size == (720,420)
            assert app._history_index == before+1
            app.undo_project()
            assert app.roof_pil_img.size == (640,420)
            app.redo_project()
            assert app.roof_pil_img.size == (720,420)
            assert app.px_per_mm == 2.

            # Measurement creation/deletion is another distinct atomic action.
            before = app._history_index
            app._run_project_edit('installation:add-measure', app.measures.append,
                {'p1':(12.,12.),'p2':(212.,12.),'label':(110.,6.),'axis':'aligned'})
            assert app._history_index == before+1
            app.clear_measures()
            assert app.measures == []
            app.undo_project()
            assert len(app.measures) == 1
            app.redo_project()
            assert app.measures == []
            # A drawn measure has an explicit axis and survives Undo/Redo.
            before = app._history_index
            app._activate_measure_mode()
            app.on_left_press(SimpleNamespace(x=20,y=100,state=0))
            app.on_left_release(SimpleNamespace(x=160,y=100,state=0))
            assert len(app.measures) == 1
            assert app.measures[0]['axis'] == 'aligned'
            assert app._history_index == before+1
            app.undo_project()
            assert app.measures == []
            app.redo_project()
            assert len(app.measures) == 1
            # Moving its label closes the edit transaction on mouse release.
            label = app.measures[0]['label']
            zx = label[0] * app.zoom_level - app.canvas.canvasx(0)
            zy = label[1] * app.zoom_level - app.canvas.canvasy(0)
            before = app._history_index
            app.on_left_press(SimpleNamespace(x=zx,y=zy,state=0))
            assert app._canvas_edit_gate.owner == 'installation:dimension-label'
            app.on_left_drag(SimpleNamespace(x=zx+20,y=zy+12,state=0))
            app.on_left_release(SimpleNamespace(x=zx+20,y=zy+12,state=0))
            assert not app._canvas_edit_gate.active
            assert app._history_index == before+1
            moved = app.measures[0]['label']
            app.undo_project()
            assert app.measures[0]['label'] == label
            app.redo_project()
            assert app.measures[0]['label'] == moved

            # Opt-in replacement alignment scales only the image, not the survey.
            third_img = Path(td) / 'roof3.png'
            Image.new('RGB',(300,200),'white').save(third_img)
            with patch('mixins.zone_tools.filedialog.askopenfilename', return_value=str(third_img)), \
                 patch('mixins.zone_tools.messagebox.askyesno', return_value=True), \
                 patch('mixins.zone_tools.messagebox.showinfo'):
                app.load_roof_image()
            assert app._align_replacement_image
            assert app.roof_pil_img.size == (300,200)
            before = app._history_index
            app._run_project_edit('installation:calibration', app._apply_scale_reference,
                                  (0.,0.),(100.,0.), 100.)
            assert app.roof_pil_img.size == (600,400)
            assert app.px_per_mm == 2.
            assert app._history_index == before+1
            app.undo_project()
            assert app.roof_pil_img.size == (300,200)
            app.redo_project()
            assert app.roof_pil_img.size == (600,400)

            # Last project remains usable and its offset survives JSON.
            path = Path(td) / 'phase14.json'
            with patch('mixins.safe_project.messagebox.showinfo'):
                assert app.save_project(destination=path)
            assert app._load_project_file(path)
            assert app.roof_pil_img.size == (600,400)
            assert app.px_per_mm == 2.
            assert not errors, errors
            print('PASS phase14: import, calibration, drag, reset, measures, Undo/Redo, JSON')
        finally:
            root.destroy()


if __name__ == '__main__':
    run()
