"""Deterministic pointer transaction boundary, no Tk display required."""
import unittest
from unittest.mock import Mock
from application.edit_transactions import EditTransactionGate
from mixins.safe_project import SafeProjectMixin


class GateTests(unittest.TestCase):
    def test_owner_exclusive_and_single_close(self):
        g = EditTransactionGate()
        self.assertTrue(g.begin('installation:zone'))
        self.assertTrue(g.active)
        self.assertFalse(g.begin('layout:ctrl-paint'))
        self.assertFalse(g.finish('wrong'))
        self.assertTrue(g.finish('installation:zone'))
        self.assertFalse(g.finish())
        self.assertFalse(g.active)

    def test_aborted_and_empty_owner(self):
        g = EditTransactionGate()
        with self.assertRaises(ValueError):
            g.begin('')
        g.begin('cabling:area')
        g.abort()
        self.assertFalse(g.active)
        self.assertTrue(g.begin('cabling:area'))


class BoundaryTests(unittest.TestCase):
    class Owner(SafeProjectMixin):
        def __init__(self):
            self._guard_ready = True
            self._restoring = False
            self._history_job = 17
            self.root = Mock()
            self.snapshots = []
        def _record_history(self, **kwargs):
            if not getattr(getattr(self, '_canvas_edit_gate', None), 'active', False):
                self.snapshots.append('snapshot')

    def test_one_before_after_and_no_intermediate_poll(self):
        owner = self.Owner()
        self.assertTrue(owner._begin_canvas_edit('installation:zone'))
        self.assertEqual(owner.snapshots, ['snapshot'])
        owner.root.after_cancel.assert_called_once_with(17)
        owner._queue_history()
        owner._record_history()
        self.assertEqual(owner.snapshots, ['snapshot'])
        self.assertFalse(owner._begin_canvas_edit('other'))
        self.assertFalse(owner._finish_canvas_edit('other'))
        self.assertTrue(owner._finish_canvas_edit('installation:zone'))
        self.assertEqual(len(owner.snapshots), 2)
        self.assertFalse(owner._finish_canvas_edit('installation:zone'))
        self.assertEqual(len(owner.snapshots), 2)

    def test_restore_gate_is_closed_on_noop_cleanup(self):
        owner = self.Owner()
        owner._begin_canvas_edit('layout:ctrl-paint')
        owner._canvas_edit_gate.abort()
        self.assertFalse(owner._finish_canvas_edit())
        self.assertEqual(len(owner.snapshots), 1)


if __name__ == '__main__':
    unittest.main()
