from ui.tab_ids import SHARED_CAMERA_TABS
"""Canvas camera helpers. Model geometry is never changed by these functions."""
import math


def viewport_center(canvas):
    return (canvas.canvasx(0) + max(1, canvas.winfo_width()) / 2,
            canvas.canvasy(0) + max(1, canvas.winfo_height()) / 2)


def place_viewport(canvas, left, top, content=None):
    """Position a canvas in *canvas pixels*, including negative scroll origins.

    Tk's xview_moveto fraction refers to the scrollregion origin, NOT to zero.
    Always leave at least a screen around the view so zooming out and panning
    work with drawings smaller than the viewport.
    """
    w = max(1, canvas.winfo_width())
    h = max(1, canvas.winfo_height())
    bounds = content or canvas.bbox('all') or (0., 0., float(w), float(h))
    x0, y0, x1, y1 = bounds
    if not all(math.isfinite(v) for v in (left, top, x0, y0, x1, y1)):
        return
    region = (math.floor(min(x0 - w, left - w)),
              math.floor(min(y0 - h, top - h)),
              math.ceil(max(x1 + w, left + 2*w)),
              math.ceil(max(y1 + h, top + 2*h)))
    canvas.configure(scrollregion=region)
    canvas.xview_moveto((left - region[0]) / (region[2] - region[0]))
    canvas.yview_moveto((top - region[1]) / (region[3] - region[1]))
    return region


def zoom_view(app, value, x, y):
    """Zoom about a pointer in view coordinates (x,y); retain its world point."""
    old = float(app.zoom_level)
    target = float(value)
    if not 0.025 <= target <= 5 or abs(target - old) < 1e-10:
        return
    canvas = app.canvas
    world_x = canvas.canvasx(x) / old
    world_y = canvas.canvasy(y) / old
    app.zoom_level = target
    app.cell_size_px = max(1, round(40*target))
    app._auto_fit = False
    app.draw_grid()
    place_viewport(canvas, world_x * target - x, world_y * target - y)
    if app._get_active_tab_index() in SHARED_CAMERA_TABS and hasattr(app, '_refresh_installation_photo'):
        app._refresh_installation_photo()
