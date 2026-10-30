"""Stable semantic IDs for the 11 tabs of the existing notebook.

Values match the legacy numeric index so old saved projects and MRO callbacks
are unchanged. References should use names rather than magic numbers.
"""
from enum import IntEnum


class TabId(IntEnum):
    HOME = 0
    INSTALLATION = 1
    LAYOUT = 2
    STRINGING = 3
    MPPT = 4
    SHADOW = 5
    SPREADSHEET = 6
    SINGLE_LINE = 7
    CABLING = 8
    ENERGY = 9
    MOUNTING = 10


DRAWING_TABS = frozenset((TabId.INSTALLATION, TabId.LAYOUT,
    TabId.STRINGING, TabId.MPPT, TabId.SHADOW, TabId.SINGLE_LINE,
    TabId.CABLING, TabId.MOUNTING))

SHARED_CAMERA_TABS = frozenset((TabId.INSTALLATION, TabId.LAYOUT,
    TabId.STRINGING, TabId.MPPT, TabId.SHADOW, TabId.CABLING))
