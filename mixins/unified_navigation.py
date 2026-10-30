"""Identical canvas camera controls for all drawing tabs.

Middle drag pans the *camera*, never geometry. Wheel zooms about the pointer.
Heavy full-grid zoom renders are coalesced to one per short burst of input.
"""
import tkinter as tk
from view_navigation import place_viewport, zoom_view
from ui.tab_ids import TabId, SHARED_CAMERA_TABS


class UnifiedNavigationMixin:
    def _build_main_area(self):
        super()._build_main_area()
        for sequence, handler in (
            ('<ButtonPress-2>', self._navigation_pan_press),
            ('<B2-Motion>', self._navigation_pan_drag),
            ('<ButtonRelease-2>', self._navigation_pan_release),
            ('<MouseWheel>', self._navigation_wheel),
            ('<Button-4>', self._navigation_wheel),
            ('<Button-5>', self._navigation_wheel),
        ):
            # No add='+': previous per-tab callbacks must not run twice.
            self.canvas.bind(sequence, handler)

    def _navigation_pan_press(self, event):
        if self._get_active_tab_index() in (TabId.HOME, TabId.SPREADSHEET, TabId.ENERGY):
            return 'break'
        self._auto_fit = False
        self._navigation_pan = (event.x, event.y,
                                self.canvas.canvasx(0), self.canvas.canvasy(0))
        self.canvas.configure(cursor='fleur')
        return 'break'

    def _navigation_pan_drag(self, event):
        state = getattr(self, '_navigation_pan', None)
        if state is None:
            return 'break'
        sx, sy, left, top = state
        new_left, new_top = left + sx - event.x, top + sy - event.y
        if self._get_active_tab_index() == TabId.MOUNTING:
            self._set_mounting_viewport(new_left, new_top)
            self._draw_mounting_legend()
        else:
            place_viewport(self.canvas, new_left, new_top,
                           (getattr(self, '_navigation_world_content', None)
                            if self._get_active_tab_index() in SHARED_CAMERA_TABS else None))
            self._schedule_installation_photo_refresh()
        return 'break'

    def _navigation_pan_release(self, event):
        self._navigation_pan = None
        self.canvas.configure(cursor='')
        self._schedule_installation_photo_refresh()
        return 'break'

    def _navigation_wheel(self, event):
        tab = self._get_active_tab_index()
        if tab in (TabId.HOME, TabId.SPREADSHEET, TabId.ENERGY):
            return 'break'
        direction = (1 if getattr(event, 'num', None) == 4 else -1 if getattr(event, 'num', None) == 5 else
                     1 if getattr(event, 'delta', 0) > 0 else -1)
        if getattr(self, '_navigation_zoom_tab', None) != tab:
            self._navigation_zoom_steps = 0
        self._navigation_zoom_tab = tab
        self._navigation_zoom_steps = max(-24, min(24,
            getattr(self, '_navigation_zoom_steps', 0) + direction))
        self._navigation_zoom_pointer = (event.x, event.y)
        if not getattr(self, '_navigation_zoom_job', None):
            self._navigation_zoom_job = self.root.after(18, self._navigation_flush_zoom)
        return 'break'

    def _navigation_flush_zoom(self):
        self._navigation_zoom_job = None
        steps = getattr(self, '_navigation_zoom_steps', 0)
        self._navigation_zoom_steps = 0
        if not steps or self._get_active_tab_index() != self._navigation_zoom_tab:
            return
        x, y = self._navigation_zoom_pointer
        self._auto_fit = False
        if self._get_active_tab_index() == TabId.MOUNTING:
            self._mounting_zoom(1.2**steps, pointer=(x, y))
        else:
            target = max(.03, min(5., self.zoom_level * 1.15**steps))
            zoom_view(self, target, x, y)

    def _zoom_at_pointer(self, event, delta):
        """Programmatic zoom and wheel share exactly the same anchored camera."""
        if self._get_active_tab_index() == TabId.MOUNTING:
            return self._queue_mounting_zoom(1.2 if delta > 0 else 1/1.2, event)
        self._auto_fit = False
        zoom_view(self, max(.03, min(5., self.zoom_level *
                                  (1.15 if delta > 0 else 1/1.15))), event.x, event.y)
        return 'break'

    def _zoom_button_change(self, factor):
        if self._get_active_tab_index() == TabId.MOUNTING:
            self._mounting_zoom(factor)
        else:
            self._auto_fit = False
            zoom_view(self, max(.03, min(5., self.zoom_level*factor)),
                      self.canvas.winfo_width()/2, self.canvas.winfo_height()/2)

    def _reset_zoom(self):
        if self._get_active_tab_index() == TabId.MOUNTING:
            self._fit_mounting()
        else:
            self._auto_fit = False
            zoom_view(self, 1., self.canvas.winfo_width()/2, self.canvas.winfo_height()/2)
