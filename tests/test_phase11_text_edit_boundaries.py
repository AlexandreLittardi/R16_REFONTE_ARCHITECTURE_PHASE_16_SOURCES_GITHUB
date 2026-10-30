"""Transactions for focus-based edits and keyboard Undo during an active edit."""
import unittest
from unittest.mock import Mock

from mixins.safe_project import SafeProjectMixin
from mixins.notes_tools import NotesToolsMixin


class FakeUi(NotesToolsMixin, SafeProjectMixin):
    def __init__(self):
        self._guard_ready = True
        self._restoring = False
        self.root = Mock()
        self._history_job = None
        self._canvas_edit_gate = None
        self.records = []
        self.value = 0
        self.txt_notes = object()
        self.cable_entries = {'current_a': object()}

    def _record_history(self, **kwargs):
        if not getattr(getattr(self, '_canvas_edit_gate', None), 'active', False):
            if not self.records or self.records[-1] != self.value:
                self.records.append(self.value)


class FocusTransactionsTest(unittest.TestCase):
    def test_undo_first_settles_uncommitted_text_transaction(self):
        ui = FakeUi()
        self.assertTrue(ui._begin_canvas_edit('notes:typing'))
        ui.value = 6
        positions = []
        ui._restore_history = lambda i: positions.append(i)
        ui._history_index = 1
        ui.undo_project()
        self.assertEqual(ui.records, [0, 6])
        self.assertEqual(positions, [0])
        self.assertFalse(ui._canvas_edit_gate.active)

    def test_undo_commits_numeric_entry_before_restore(self):
        ui = FakeUi()
        ui._capture_cable_inputs = lambda: setattr(ui, 'value', 8)
        ui._begin_canvas_edit('cabling:sizing-input')
        ui._history_index = 1
        positions = []
        ui._restore_history = lambda i: positions.append(i)
        ui.undo_project()
        self.assertEqual(ui.records, [0, 8])
        self.assertEqual(positions, [0])
        self.assertFalse(ui._canvas_edit_gate.active)

    def test_resume_open_typing_after_undo(self):
        ui = FakeUi()
        ui.root.focus_get.return_value = ui.txt_notes
        ui._resume_focused_text_edit()
        self.assertEqual(ui._canvas_edit_gate.owner, 'notes:typing')
        self.assertFalse(ui._resume_focused_text_edit())
        self.assertEqual(ui.records, [0])

    def test_resume_numeric_field_after_undo(self):
        ui = FakeUi()
        ui.root.focus_get.return_value = ui.cable_entries['current_a']
        ui._resume_focused_text_edit()
        self.assertEqual(ui._canvas_edit_gate.owner, 'cabling:sizing-input')

    def test_unrelated_focus_does_not_open_transaction(self):
        ui = FakeUi()
        ui.root.focus_get.return_value = object()
        ui._resume_focused_text_edit()
        self.assertIsNone(ui._canvas_edit_gate)

    def test_invalid_cable_input_does_not_commit_edit(self):
        ui = FakeUi()
        ui._capture_cable_inputs = lambda: False
        ui._begin_canvas_edit('cabling:sizing-input')
        ui._finish_cable_input_edit()
        self.assertEqual(ui.records, [0])
        self.assertFalse(ui._canvas_edit_gate.active)

if __name__ == '__main__':
    unittest.main()
