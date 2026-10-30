"""Pure domain rules for background image movement and calibration."""
import math
import unittest
from domain.roof_registration import (
    shifted_photo_offset, calibrated_scale, replacement_scale_factor)


class RoofRegistrationTests(unittest.TestCase):
    def test_drag_offset_uses_image_pixels_not_zoomed_screen_units(self):
        self.assertEqual(shifted_photo_offset((4., -8.), 30., -12., 3.), (14., -12.))
        self.assertEqual(shifted_photo_offset((0., 0.), 0., 0., 1.), (0., 0.))

    def test_invalid_drag_values_rejected(self):
        for vals in [((0, 0), 10, 0, 0), ((0, 0), 0, 0, float('nan')),
                     ((0, 0), 1, math.inf, 1), ((math.nan, 0), 3, 4, 1)]:
            with self.subTest(vals=vals), self.assertRaises(ValueError):
                shifted_photo_offset(*vals)

    def test_calibration_preserves_exact_measurement(self):
        self.assertEqual(calibrated_scale((0, 0), (300, 400), 250), 2.)
        self.assertEqual(calibrated_scale((5., 0.), (55., 0.), 100.), .5)

    def test_calibration_rejects_invalid_segments_without_mutation(self):
        for a, b, length in [((0, 0), (5, 0), 100), ((0, 0), (30, 0), 0),
                             ((0, 0), (30, 0), -1), ((0, 0), (30, 0), math.nan),
                             ((math.inf, 0), (30, 0), 100), ((0, 0), (math.nan, 0), 100)]:
            with self.subTest(a=a,b=b,length=length), self.assertRaises(ValueError):
                calibrated_scale(a,b,length)

    def test_new_photo_alignment_preserves_survey_scale(self):
        self.assertEqual(replacement_scale_factor(2., 1.), 2.)
        self.assertEqual(replacement_scale_factor(1., 2.), .5)

    def test_invalid_alignment_factor_rejected(self):
        for old,new in ((0, 2), (-1, 2), (2, 0), (math.inf, 2), (2, math.nan)):
            with self.subTest(old=old,new=new), self.assertRaises(ValueError):
                replacement_scale_factor(old,new)
