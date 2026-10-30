"""Pure intent routing for the shared canvas' primary mouse button.

The Installation editor owns polygon gestures; the DiagramEditorMixin owns
single-line diagram gestures.  No Tkinter and no canvas mutation here.
"""
from enum import Enum
from ui.tab_ids import TabId


class LeftGesture(Enum):
    INSTALLATION_POLYGON = 'installation_polygon'
    INSTALLATION_CANVAS = 'installation_canvas'
    DELEGATE = 'delegate'


def press_intent(tab, *, path_mode=None, polygon_index=None):
    if tab == TabId.INSTALLATION:
        if path_mode == 'select_polygon' and polygon_index is not None:
            return LeftGesture.INSTALLATION_POLYGON
        return LeftGesture.INSTALLATION_CANVAS
    return LeftGesture.DELEGATE


def drag_intent(tab, *, polygon_drag_mode=None, polygon_index=None):
    if tab == TabId.INSTALLATION:
        if polygon_drag_mode and polygon_index is not None:
            return LeftGesture.INSTALLATION_POLYGON
        return LeftGesture.INSTALLATION_CANVAS
    return LeftGesture.DELEGATE
