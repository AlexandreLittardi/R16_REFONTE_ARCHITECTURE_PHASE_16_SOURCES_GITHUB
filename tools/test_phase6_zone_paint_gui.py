"""Phase 6 GUI regression: grid planning is an edit boundary, not a repaint."""
import copy
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PVLayoutRibbonApp


def run():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(directory) / 'recent.json')
        root = tk.Tk()
        root.geometry('1280x800')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            assert len(app.ribbon_notebook.tabs()) == 11
            app.px_per_mm = 1.0
            app.roof_zones = [dict(id=1, x1=5.0, y1=10.0, x2=3200.0,
                                   y2=4200.0, angle_deg=0, align_x='Centre',
                                   align_y='Centre')]
            app.ribbon_notebook.select(app.tab_layout)
            root.update()  # tab changed: performs explicit reconciliation
            initial = copy.deepcopy(app.roof_zones)
            assert initial[0].get('rows', 0) > 0, initial
            uid = initial[0]['uid']
            for _ in range(5):
                app.draw_grid()
                app._panel_rect((initial[0]['row_base'], 0))
            assert app.roof_zones == initial, 'Repaint/geometry mutated a committed zone'
            assert app.roof_zones[0]['uid'] == uid
            # An external legacy edit has not been committed.  Pure rendering
            # must not silently shift the physical module grid.
            app.roof_zones[0]['x2'] -= 600
            uncommitted = copy.deepcopy(app.roof_zones)
            app.draw_grid()
            assert app.roof_zones == uncommitted, 'Repaint committed geometry edits'
            app._record_history(prepare_zone_grids=False)  # passive history poll
            assert app.roof_zones == uncommitted, 'Passive history poll allocated zone rows'
            app._record_history()  # explicit domain commit boundary
            assert app.roof_zones[0]['cols'] < initial[0]['cols']
            committed = copy.deepcopy(app.roof_zones)
            for _ in range(3):
                app._zoom_button_change(1.07)
                app.draw_grid()
            assert committed == app.roof_zones
            # Force the Shadow painter through its roof-photo branch as well.
            app.roof_pil_img = Image.new('RGB', (100, 100), '#f6f6f6')
            app.ribbon_notebook.select(app.tab_shadow)
            root.update()
            app.draw_grid()
            assert committed == app.roof_zones
            assert not errors, errors
            print('PASS phase 6: 11 tabs, stable zone rows/UIDs, zoom & paint read-only, commit on history')
        finally:
            root.destroy()


if __name__ == '__main__':
    run()
