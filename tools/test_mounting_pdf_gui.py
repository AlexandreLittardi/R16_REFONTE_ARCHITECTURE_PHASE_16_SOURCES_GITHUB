"""Smoke check: PDF replaces SVG in the Montage export menu and is vector."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
import tkinter as tk
from PIL import Image
from app import PVLayoutRibbonApp


def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['PV_APP_RECENTS_FILE'] = str(Path(tmp) / 'recents.json')
        root = tk.Tk()
        root.geometry('1200x800')
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app = PVLayoutRibbonApp(root)
            root.update()
            menu = app._mounting_menus['export']
            labels = [menu.entrycget(i, 'label') for i in range(menu.index('end') + 1)]
            assert 'Full drawing PDF A3 (vector)' in labels, labels
            assert not any('SVG' in label for label in labels), labels
            app.project_name = 'Demo PDF vectoriel'
            app.px_per_mm = .1
            app.panel_width_mm = 1303
            app.panel_height_mm = 2384
            app.roof_pil_img = Image.new('RGB', (800, 700), 'white')
            app.roof_zones = [dict(id=1,x1=100,y1=100,x2=600,y2=600,angle_deg=0)]
            app.generate_panels_from_zones()
            app.ribbon_notebook.select(app.tab_mounting)
            root.update()
            path = Path(tmp) / 'export.pdf'
            with patch('mixins.mounting_ui.filedialog.asksaveasfilename', return_value=str(path)), \
                 patch('mixins.mounting_ui.messagebox.showinfo'):
                app._export_mounting('plan_pdf')
            assert path.exists(), 'No PDF created from Montage menu'
            with fitz.open(path) as pdf:
                assert len(pdf) == 1
                assert not pdf[0].get_images(full=True), 'Raster image included'
                assert len(pdf[0].get_drawings()) > len(app.panels)
                assert pdf[0].rect.width > pdf[0].rect.height
            assert not errors, str(errors)
            print('PASS Montage GUI A3 PDF native vectors, SVG removed from menu')
        finally:
            root.destroy()

if __name__ == '__main__':
    run()
