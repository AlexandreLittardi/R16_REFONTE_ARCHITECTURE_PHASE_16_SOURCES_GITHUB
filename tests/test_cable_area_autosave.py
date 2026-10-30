"""Cable routing areas survive Save, Save as, and the actual autosave path."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from mixins.safe_project import SafeProjectMixin
from project_store import fingerprint, verify_routing_geometry


class SaveStub(SafeProjectMixin):
    def __init__(self, location):
        self.project_name = 'Routing test'
        self.projects_dir = str(location)
        self.current_project_filepath = str(location / 'existing_project.json')
        self.project_uid = 'routing-save-test'
        self.roof_pil_img = None
        self.roof_image_path = None
        self.root = Mock()
        self.lbl_project_info = Mock()
        self.home_active_label = Mock()
        self._remember_recent_project = Mock()
        self.document = {'project_name': self.project_name,
            'roof_polygons': [
                {'id': 1, 'points': [[1., 1.], [12., 1.], [12., 12.], [1., 12.]], 'installation_height_m': 11.0},
                {'id': 2, 'points': [[25., 5.], [45., 5.], [45., 25.], [25., 25.]]}],
            'roof_image_offset': [14., -24.],
            'cable_paths': [{'id': 1, 'points': [[10., 20.], [30., 40.]]}]}
        self._saved_signature = self._document_signature()

    def _capture_cable_inputs(self):
        pass

    def _collect_project_data(self):
        return copy.deepcopy(self.document)

    def _document_signature(self):
        return fingerprint(self._collect_project_data())


@patch("mixins.safe_project.messagebox.showinfo")
@patch("mixins.safe_project.messagebox.showerror")
class RoutingSaveTests(unittest.TestCase):
    def test_automatic_save_updates_original_project_and_recovery_copy(self, _error, _info):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            app = SaveStub(path)
            self.assertTrue(app.save_project())
            app.document['roof_polygons'][0]['points'] = [[x + 17.125, y - 3.25] for x,y in app.document['roof_polygons'][0]['points']]
            app.document['roof_image_offset'] = [-20., 15.]
            app.document['cable_paths'][0]['points'][0] = [9., 8.]
            self.assertTrue(app.save_project(silent=True))
            expected = app.document
            self.assertTrue(verify_routing_geometry(app.current_project_filepath, expected))
            recovery = path / '.recovery' / 'routing-save-test.json'
            self.assertTrue(recovery.exists())
            self.assertTrue(verify_routing_geometry(recovery, expected))
            self.assertEqual(json.loads(Path(app.current_project_filepath).read_text())['roof_polygons'][0]['points'][0], [18.125, -2.25])
            # A second autosave without edits does not make unnecessary backups.
            old_backup_count = len(list(path.glob('.backups/**/*')))
            self.assertTrue(app.save_project(silent=True))
            self.assertEqual(len(list(path.glob('.backups/**/*'))), old_backup_count)

    def test_explicit_save_as_persists_routing_areas_and_offsets(self, _error, _info):
        with tempfile.TemporaryDirectory() as folder:
            app = SaveStub(Path(folder))
            app.document['roof_polygons'][1]['points'][2] = [51.25, 31.75]
            new_path = Path(folder) / 'updated.json'
            self.assertTrue(app.save_project(destination=new_path))
            self.assertEqual(app.current_project_filepath, str(new_path))
            self.assertTrue(verify_routing_geometry(new_path, app.document))

    def test_verify_detects_stale_or_different_routing_areas(self, _error, _info):
        with tempfile.TemporaryDirectory() as folder:
            app = SaveStub(Path(folder))
            self.assertTrue(app.save_project())
            expected = copy.deepcopy(app.document)
            expected['roof_polygons'][0]['points'][0] = [500., 500.]
            with self.assertRaisesRegex(IOError, 'roof_polygons'):
                verify_routing_geometry(app.current_project_filepath, expected)

    def test_unsaved_new_project_keeps_recovery_without_unexpected_project_file(self, _error, _info):
        with tempfile.TemporaryDirectory() as folder:
            app = SaveStub(Path(folder))
            app.current_project_filepath = None
            self.assertTrue(app.save_project(silent=True))
            self.assertFalse((Path(folder) / 'existing_project.json').exists())
            self.assertTrue((Path(folder) / '.recovery' / 'routing-save-test.json').exists())


if __name__ == '__main__':
    unittest.main()
