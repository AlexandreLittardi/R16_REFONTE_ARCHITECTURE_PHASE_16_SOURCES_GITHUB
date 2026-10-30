"""Shared natural sorting for string and inverter names."""
import re


def natural_sort_key(value):
    """Sort INV2 before INV10 and String 2 before String 10."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(value))]
