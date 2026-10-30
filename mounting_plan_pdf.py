"""One-sheet, true-vector A3 mounting plan from the same scene as the live editor.

No SVG intermediate and no raster rendering: all modules, clamps, dimension
lines, arrowheads and labels are drawn as native PDF paths and text.
"""
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from mounting_drawing import bounds, construction_shapes, geometry, scene

PAGE_W, PAGE_H = landscape(A3)
BLACK = colors.HexColor('#171717')
GRAY = colors.HexColor('#555555')


def _rgb(value, default=BLACK):
    try:
        return colors.toColor(value or '#222222')
    except (ValueError, TypeError):
        return default


def _draw_text(pdf, element):
    x, y = element['point']
    size = max(.01, float(element.get('font', 11)))
    font = 'Helvetica-Bold' if element.get('bold') else 'Helvetica'
    txt = str(element.get('text', ''))
    pdf.saveState()
    pdf.translate(x, y)
    pdf.scale(1, -1)  # Undo the plan-coordinate flip for PDF glyphs.
    if element.get('angle'):
        pdf.rotate(float(element['angle']))
    pdf.setFont(font, size)
    # Native PDF text remains searchable/selectable. White text outlines work
    # like SVG's paint-order stroke and preserve contrast against thin lines.
    baseline = -.34 * size
    width = pdf.stringWidth(txt, font, size)
    if element.get('background'):
        pdf.setLineWidth(3.6)
        pdf.setStrokeColor(colors.white)
        bg = pdf.beginText()
        bg.setTextOrigin(-width / 2, baseline)
        bg.setFont(font, size)
        bg.setTextRenderMode(1)
        bg.textOut(txt)
        pdf.drawText(bg)
    pdf.setFillColor(_rgb(element.get('color')))
    pdf.drawCentredString(0, baseline, txt)
    pdf.restoreState()


def _draw_element(pdf, element):
    kind = element['kind']
    color = _rgb(element.get('color'))
    pdf.saveState()
    pdf.setStrokeColor(color)
    pdf.setLineWidth(float(element.get('width', 1)))
    pdf.setLineJoin(1)
    if kind in ('line', 'polygon'):
        pts = element['points']
        if pts:
            path = pdf.beginPath()
            path.moveTo(*pts[0])
            for pt in pts[1:]:
                path.lineTo(*pt)
            if kind == 'polygon':
                path.close()
            fill = element.get('fill')
            if fill and fill != 'none':
                pdf.setFillColor(_rgb(fill))
            pdf.drawPath(path, stroke=1, fill=int(bool(fill and fill != 'none')))
    elif kind == 'cross':
        x, y = element['point']
        r = element['size']
        pdf.line(x - r, y, x + r, y)
        pdf.line(x, y - r, x, y + r)
    elif kind == 'text':
        _draw_text(pdf, element)
    pdf.restoreState()


def write_plan_pdf(app, path):
    """Export the full mounting plan as one A3 landscape vector PDF.

    Geometry and dimension calculations are exactly those used by the SVG
    and editor; the PDF page size does not alter any dimension value.
    """
    if not math.isfinite(float(getattr(app, 'px_per_mm', 0))) or app.px_per_mm <= 0:
        raise ValueError('Calibrer le plan avant l\'export PDF.')
    items = geometry(app)
    if not items:
        raise ValueError('No modules to export in the Mounting drawing.')
    shapes = scene(app, items, construction=False)
    shapes.extend(construction_shapes(
        app, items, selected=getattr(app, 'selected_panel_coords', ()),
        detailed=True, force_detail=True))
    left, top, right, bottom = bounds(shapes)
    w, h = right-left, bottom-top
    if not all(math.isfinite(v) for v in (left, top, right, bottom)) or w <= 0 or h <= 0:
        raise ValueError('Geometrie de plan invalide pour le PDF.')

    pdf = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    project = str(getattr(app, 'project_name', 'PV project'))
    pdf.setTitle(f'{project} - A3 vector mounting drawing')
    pdf.setAuthor('R16 - Mounting')
    pdf.setSubject('Mounting plan and dimensions - vector drawing')

    margin = 12 * mm
    plot_left, plot_right = margin + 7*mm, PAGE_W - margin - 7*mm
    plot_bottom, plot_top = 48*mm, PAGE_H - 42*mm
    plot_w, plot_h = plot_right-plot_left, plot_top-plot_bottom
    factor = min(plot_w/w, plot_h/h)
    rendered_w, rendered_h = w*factor, h*factor
    draw_left = plot_left + (plot_w-rendered_w)/2
    draw_bottom = plot_bottom + (plot_h-rendered_h)/2

    pdf.setStrokeColor(BLACK)
    pdf.setLineWidth(.9)
    pdf.rect(margin, margin, PAGE_W-2*margin, PAGE_H-2*margin, fill=0, stroke=1)
    pdf.setFont('Helvetica-Bold', 18)
    pdf.setFillColor(BLACK)
    pdf.drawString(margin+7*mm, PAGE_H-24*mm, 'MOUNTING PLAN - MODULE LAYOUT')
    pdf.setFont('Helvetica', 10)
    pdf.setFillColor(GRAY)
    pdf.drawRightString(PAGE_W-margin-7*mm, PAGE_H-23*mm, 'A3 LANDSCAPE | VECTOR DRAWING')
    pdf.setStrokeColor(colors.HexColor('#999999'))
    pdf.setLineWidth(.45)
    pdf.line(margin+7*mm, PAGE_H-30*mm, PAGE_W-margin-7*mm, PAGE_H-30*mm)

    pdf.saveState()
    # Clip the drawing to its viewport, but not the page title or cartouche.
    clip = pdf.beginPath()
    clip.rect(plot_left, plot_bottom, plot_w, plot_h)
    pdf.clipPath(clip, stroke=0, fill=0)
    pdf.translate(draw_left-left*factor, draw_bottom+bottom*factor)
    pdf.scale(factor, -factor)
    for shape in shapes:
        _draw_element(pdf, shape)
    pdf.restoreState()

    nominal_scale = (72./25.4)/(app.px_per_mm*factor)
    scale_string = f'1:{nominal_scale:.0f}'
    base = margin+7*mm
    pdf.setFillColor(BLACK)
    pdf.setStrokeColor(colors.HexColor('#999999'))
    pdf.line(base, 40*mm, PAGE_W-margin-7*mm, 40*mm)
    pdf.setFont('Helvetica-Bold', 11)
    project_one_line = project.replace('\n', ' ').replace('\r', ' ')
    pdf.drawString(base, 33*mm, project_one_line[:85])
    pdf.setFont('Helvetica', 9)
    pdf.drawString(base, 27*mm, f"{len(items)} modules | Dimensions and coordinates in mm | Print scale {scale_string} (A3, 100%)")
    pdf.setFillColor(GRAY)
    pdf.setFont('Helvetica', 8)
    pdf.drawString(base, 20*mm, 'Distances follow project calibration. Verify dimensions and clamp references on site before installation.')
    site = (getattr(app, 'mounting_plan', None) or {}).get('site') or {}
    if site.get('origin') is None:
        pdf.drawRightString(PAGE_W-margin-7*mm, 20*mm, 'TEMPORARY SITE DATUM')
    else:
        pdf.drawRightString(PAGE_W-margin-7*mm, 20*mm, 'SITE DATUM SET - VERIFY ON SITE')
    # 10-metre graphical scale, if it fits the page footer.
    bar_len = 10000*app.px_per_mm*factor
    bx = PAGE_W-margin-7*mm-bar_len
    by = 31*mm
    if bx > PAGE_W/2:
        pdf.setStrokeColor(BLACK)
        pdf.setLineWidth(1.3)
        pdf.line(bx,by,bx+bar_len,by)
        for frac in (0,.5,1):
            x=bx+bar_len*frac
            pdf.line(x,by-3,x,by+3)
        pdf.setFillColor(BLACK)
        pdf.setFont('Helvetica',8)
        pdf.drawCentredString(bx,by+5,'0')
        pdf.drawCentredString(bx+bar_len*.5,by+5,'5 m')
        pdf.drawCentredString(bx+bar_len,by+5,'10 m')

    pdf.showPage()
    pdf.save()
    return Path(path)
