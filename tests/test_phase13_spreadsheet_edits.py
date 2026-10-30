"""Pure-domain worksheet command tests (Tkinter not imported)."""
import copy
import unittest
from domain.spreadsheet_edits import (cell_address, write_cell, paste_block,
                                       append_axis, remove_last_axis)


class WorksheetCommandsTests(unittest.TestCase):
    def setUp(self):
        self.state = {'rows': 3, 'cols': 3, 'cells': {'A1': '12', 'B1': '=A1*2'},
                      'col_widths': [100, 150, 200], 'row_heights': [20, 30, 40],
                      'extension': {'keep': True}}

    def test_cell_addresses(self):
        self.assertEqual(cell_address(0, 0), 'A1')
        self.assertEqual(cell_address(10, 26), 'AA11')
        self.assertEqual(cell_address(0, 51), 'AZ1')
        for row, col in ((-1, 0), (0, -1), (0.0, 0)):
            with self.subTest(row=row, col=col):
                with self.assertRaises(ValueError):
                    cell_address(row, col)

    def test_write_cell_idempotent_and_zero_preserved(self):
        self.assertFalse(write_cell(self.state, 0, 0, '12'))
        self.assertTrue(write_cell(self.state, 1, 2, '0'))
        self.assertEqual(self.state['cells']['C2'], '0')
        self.assertTrue(write_cell(self.state, 0, 1, ''))
        self.assertNotIn('B1', self.state['cells'])
        self.assertFalse(write_cell(self.state, 0, 1, ''))
        self.assertEqual(self.state['extension'], {'keep': True})

    def test_outside_cell_rejected_without_mutation(self):
        original = copy.deepcopy(self.state)
        with self.assertRaises(ValueError):
            write_cell(self.state, 3, 0, 'x')
        self.assertEqual(self.state, original)

    def test_paste_block_clips_and_removes_blanks(self):
        self.assertTrue(paste_block(self.state, 0, 0, [['', '15'], ['=B1*3', 'hello']]))
        self.assertEqual(self.state['cells'], {'B1': '15', 'A2': '=B1*3', 'B2': 'hello'})
        self.assertFalse(paste_block(self.state, 2, 2, [[''], ['ignored']]))
        self.assertTrue(paste_block(self.state, 2, 2, [['last', 'out'], ['out']]))
        self.assertEqual(self.state['cells']['C3'], 'last')

    def test_paste_rejects_invalid_block_atomically(self):
        before = copy.deepcopy(self.state)
        with self.assertRaises(ValueError):
            paste_block(self.state, 0, 0, [['valid'], ['oops', 99]])
        self.assertEqual(self.state, before)

    def test_append_axes_limit(self):
        self.assertTrue(append_axis(self.state, 'row', 4))
        self.assertFalse(append_axis(self.state, 'row', 4))
        self.assertTrue(append_axis(self.state, 'col', 4))
        self.assertFalse(append_axis(self.state, 'col', 4))

    def test_remove_last_row_cleans_dims_and_cells(self):
        self.state['cells']['B3'] = 'value'
        self.assertTrue(remove_last_axis(self.state, 'row'))
        self.assertNotIn('B3', self.state['cells'])
        self.assertEqual(self.state['rows'], 2)
        self.assertEqual(self.state['row_heights'], [20, 30])
        self.assertEqual(self.state['extension'], {'keep': True})

    def test_remove_last_col_cleans_dims_and_cells(self):
        self.state['cells']['C2'] = 'value'
        self.assertTrue(remove_last_axis(self.state, 'col'))
        self.assertNotIn('C2', self.state['cells'])
        self.assertEqual(self.state['cols'], 2)
        self.assertEqual(self.state['col_widths'], [100, 150])

    def test_minimum_one_axis_retained(self):
        self.state['rows'] = 1
        self.state['cols'] = 1
        original = copy.deepcopy(self.state)
        self.assertFalse(remove_last_axis(self.state, 'row'))
        self.assertFalse(remove_last_axis(self.state, 'col'))
        self.assertEqual(self.state, original)


if __name__ == '__main__':
    unittest.main()

class FillHandleTests(unittest.TestCase):
    def test_relative_formula_shift(self):
        from domain.spreadsheet_edits import shift_formula
        self.assertEqual(shift_formula('=A1+B2', 2, 3), '=D3+E4')
        self.assertEqual(shift_formula('=A1', -4, -4), '=A1')
        self.assertEqual(shift_formula('plain text', 1, 1), 'plain text')

    def test_fill_formula_maintains_source(self):
        from domain.spreadsheet_edits import fill_range
        sheet = {'rows': 5, 'cols': 3, 'cells': {'A1': '=B1*3'}}
        self.assertTrue(fill_range(sheet, (0, 0), (0, 0), (2, 0)))
        self.assertEqual(sheet['cells'], {'A1': '=B1*3', 'A2': '=B2*3', 'A3': '=B3*3'})

    def test_fill_numeric_vertical_series(self):
        from domain.spreadsheet_edits import fill_range
        sheet = {'rows': 5, 'cols': 2, 'cells': {'A1': '2', 'A2': '4'}}
        self.assertTrue(fill_range(sheet, (0, 0), (1, 0), (4, 0)))
        self.assertEqual(sheet['cells']['A5'], '10.0')
        self.assertEqual(sheet['cells']['A2'], '4')

    def test_fill_numeric_horizontal_series_and_noop(self):
        from domain.spreadsheet_edits import fill_range
        sheet = {'rows': 2, 'cols': 4, 'cells': {'A1': '1', 'B1': '3'}}
        self.assertTrue(fill_range(sheet, (0, 0), (0, 1), (0, 3)))
        self.assertEqual(sheet['cells']['C1'], '5.0')
        self.assertFalse(fill_range(sheet, (0, 0), (0, 1), (0, 1)))

    def test_reject_bad_source_without_mutation(self):
        from domain.spreadsheet_edits import fill_range
        sheet = {'rows': 2, 'cols': 2, 'cells': {'A1': '10'}}
        before = copy.deepcopy(sheet)
        with self.assertRaises(ValueError):
            fill_range(sheet, (0, 0), (4, 0), (1, 0))
        self.assertEqual(sheet, before)
