"""Phase 10: synchronous toolbar and dialog history boundaries."""
import unittest
from unittest.mock import Mock

from mixins.safe_project import SafeProjectMixin


class Boundary(SafeProjectMixin):
    def __init__(self):
        self._guard_ready = True
        self._restoring = False
        self._history_job = 12
        self.root = Mock()
        self.records = []
        self.value = 0
        self._canvas_edit_gate = None

    def _record_history(self, **kwargs):
        if not getattr(getattr(self, '_canvas_edit_gate', None), 'active', False):
            if not self.records or self.records[-1] != self.value:
                self.records.append(self.value)


class CommandTransactionsTest(unittest.TestCase):
    def test_one_command_with_multiple_changes_one_step(self):
        b = Boundary()
        def action():
            b.value += 1
            b._queue_history()  # simulates wiring events during command
            b._record_history()
            b.value += 1
            return 'done'
        self.assertEqual(b._run_project_edit('layout:generate', action), 'done')
        self.assertEqual(b.records, [0, 2])
        self.assertEqual(b._history_job, None)

    def test_noop_and_cancel_create_no_step(self):
        b = Boundary()
        self.assertIsNone(b._run_project_edit('layout:cancel', lambda: None))
        self.assertEqual(b.records, [0])
        b._run_project_edit('layout:cancel', lambda: setattr(b, 'value', 0))
        self.assertEqual(b.records, [0])

    def test_nested_command_belongs_to_outer_owner(self):
        b = Boundary()
        def outer():
            b.value = 1
            b._run_project_edit('nested', lambda: setattr(b, 'value', 2))
            self.assertTrue(b._canvas_edit_gate.active)
            b.value = 3
        b._run_project_edit('parent', outer)
        self.assertEqual(b.records, [0, 3])
        self.assertFalse(b._canvas_edit_gate.active)

    def test_exception_closes_gate_and_preserves_partial_edits(self):
        b = Boundary()
        def fails():
            b.value = 9
            raise RuntimeError('cannot draw')
        with self.assertRaisesRegex(RuntimeError, 'cannot draw'):
            b._run_project_edit('failing', fails)
        self.assertEqual(b.records, [0, 9])
        self.assertFalse(b._canvas_edit_gate.active)
        b._run_project_edit('subsequent', lambda: setattr(b, 'value', 10))
        self.assertEqual(b.records, [0, 9, 10])

    def test_no_guard_yet_does_not_capture_history(self):
        b = Boundary()
        b._guard_ready = False
        b._run_project_edit('initializing', lambda: setattr(b, 'value', 1))
        self.assertEqual(b.records, [])
        self.assertFalse(b._canvas_edit_gate.active)


if __name__ == '__main__':
    unittest.main()
