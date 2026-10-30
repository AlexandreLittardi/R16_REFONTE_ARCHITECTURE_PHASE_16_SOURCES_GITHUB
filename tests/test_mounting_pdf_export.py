"""Regression tests for the one-page A3 vector export (separate from installer dossier)."""
import tempfile
import unittest
from pathlib import Path

import fitz

from mounting_plan_pdf import write_plan_pdf
from test_mounting import fixture


class MountingA3PdfTests(unittest.TestCase):
    def test_vector_print_sheet_contains_panels_clamps_and_dimensions(self):
        app = fixture()
        app.mounting_plan['dimensions'].append(dict(
            p1=(0, 0), p2=(130.3, 0), label=(65.15, -24), axis='aligned'))
        with tempfile.TemporaryDirectory() as temp:
            filename = Path(temp) / 'Montage.pdf'
            write_plan_pdf(app, filename)
            document = fitz.open(filename)
            self.assertEqual(document.page_count, 1)
            page = document[0]
            self.assertAlmostEqual(page.rect.width, 1190.551, delta=0.1)
            self.assertAlmostEqual(page.rect.height, 841.89, delta=0.1)
            self.assertEqual(page.get_images(full=True), [])
            self.assertGreater(len(page.get_drawings()), 10)
            text = page.get_text()
            self.assertIn('MOUNTING PLAN', text)
            self.assertIn('1303.0 mm', text)
            self.assertIn('Montage & <essai>', text)
            self.assertIn('1', text)
            self.assertIn('2', text)
            document.close()

    def test_invalid_project_scale_not_exported(self):
        app = fixture()
        app.px_per_mm = 0
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                write_plan_pdf(app, Path(temp) / 'bad.pdf')

    def test_long_label_and_nonzero_rotation(self):
        app = fixture()
        app.mounting_plan['dimensions'].append(dict(
            p1=(0, 0), p2=(130.3, 0), label=(65, -24), axis='aligned',
            text_override='PROJET - TEXTE PERSONALISE'))
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'Montage.pdf'
            write_plan_pdf(app, out)
            with fitz.open(out) as pdf:
                self.assertIn('PROJET - TEXTE PERSONALISE', pdf[0].get_text())
