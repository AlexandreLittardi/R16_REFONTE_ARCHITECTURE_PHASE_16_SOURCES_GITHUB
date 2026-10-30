"""Tk-independent equipment drop commands, validation, and no-op semantics."""
import unittest

from domain.mppt_edits import interpret_equipment_drop, propose_mppt_assignment


class MpptAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.strings = {'S1': [(0, 0)], 'S2': [(0, 1)],
                        'S3': [(0, 2), (0, 3)], 'empty': []}
        self.blocks = {'INV': {'mppt_count': 2, 'max_strings_per_mppt': 2}}

    def test_assign_returns_new_dict_without_mutating_input(self):
        old = {'S1': {'block': 'INV', 'mppt': 1}}
        result = propose_mppt_assignment(old, self.strings, self.blocks, 'S2', 'INV', 1)
        self.assertIsNone(result.error)
        self.assertEqual(len(result.assignments), 2)
        self.assertEqual(old, {'S1': {'block': 'INV', 'mppt': 1}})

    def test_idempotent_assignment_is_identical(self):
        old = {'S1': {'block': 'INV', 'mppt': 1}}
        result = propose_mppt_assignment(old, self.strings, self.blocks, 'S1', 'INV', 1)
        self.assertEqual(result.assignments, old)
        self.assertIsNot(result.assignments, old)

    def test_reject_incompatible_panel_count_and_keep_original(self):
        old = {'S1': {'block': 'INV', 'mppt': 1}}
        result = propose_mppt_assignment(old, self.strings, self.blocks, 'S3', 'INV', 1)
        self.assertEqual(result.error, 'different_panel_counts')
        self.assertEqual(result.existing_panel_count, 1)
        self.assertEqual(result.assignments, old)

    def test_reject_capacity_without_mutation(self):
        old = {'S1': {'block': 'INV', 'mppt': 1}, 'S2': {'block': 'INV', 'mppt': 1}}
        result = propose_mppt_assignment(old, self.strings, self.blocks, 'S3', 'INV', 1)
        # Panel mismatch is checked before capacity, just like the original UI.
        self.assertEqual(result.error, 'different_panel_counts')
        extended = dict(self.strings, S3=[(0, 4)])
        result = propose_mppt_assignment(old, extended, self.blocks, 'S3', 'INV', 1)
        self.assertEqual(result.error, 'mppt_full')
        self.assertEqual(result.assignments, old)

    def test_reject_absent_string_and_block(self):
        self.assertEqual(propose_mppt_assignment({}, self.strings, self.blocks, 'empty', 'INV', 1).error,
                         'empty_string')
        self.assertEqual(propose_mppt_assignment({}, self.strings, self.blocks, 'S1', 'other', 1).error,
                         'missing_block')

    def test_reject_invalid_mppt_range(self):
        for mppt in (0, -1, 3, '1', True):
            with self.subTest(mppt=mppt):
                self.assertEqual(propose_mppt_assignment({}, self.strings, self.blocks, 'S1', 'INV', mppt).error,
                                 'invalid_mppt')


class EquipmentDropTests(unittest.TestCase):
    def test_drop_on_mppt(self):
        result = interpret_equipment_drop('string::S1', 'mppt::INV::2')
        self.assertEqual((result.action, result.string_id, result.block_name, result.mppt_idx),
                         ('assign', 'S1', 'INV', 2))

    def test_drop_on_sibling_string_resolves_parent(self):
        result = interpret_equipment_drop('string::S1', 'string::S2', 'mppt::INV::1')
        self.assertEqual((result.action, result.block_name, result.mppt_idx), ('assign', 'INV', 1))

    def test_drop_on_unassigned_from_sibling(self):
        result = interpret_equipment_drop('string::S1', 'string::S2', 'unassigned')
        self.assertEqual(result.action, 'unassign')

    def test_drop_on_block_is_informational_not_an_edit(self):
        self.assertEqual(interpret_equipment_drop('string::S1', 'block::INV').action, 'choose_mppt')

    def test_invalid_and_click_only_drops_do_nothing(self):
        for dragged, target in (('', 'mppt::INV::1'), ('block::INV', 'mppt::INV::1'),
                                ('string::S1', 'string::S1'), ('string::S1', ''),
                                ('string::S1', 'mppt::INV::x'), ('string::S1', 'mppt::INV::0'),
                                ('string::S1', 'mppt::INVALID'), ('string::S1', 'other')):
            with self.subTest(dragged=dragged, target=target):
                self.assertIsNone(interpret_equipment_drop(dragged, target))

    def test_block_name_with_separator(self):
        result = interpret_equipment_drop('string::S1', 'mppt::Area::A::2')
        self.assertEqual(result.block_name, 'Area::A')


if __name__ == '__main__':
    unittest.main()
