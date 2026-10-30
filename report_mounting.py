"""Calibrated vector mounting sheets, independent of Tk and the view zoom."""
import datetime as dt
import math
from pathlib import Path
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from mounting import axes
from mounting_drawing import geometry, annotations, resolve_point,site_origin
from project_store import fingerprint
from report_plans import detail_tiles
from mounting_spacing import nearest_gaps
from mounting_quantities import fixing_inventory

INK = '#171717'
COLORS = {'edge': '#171717', 'intermediate': '#777777', 'standard': '#aaaaaa'}
LETTERS = {'edge': 'R', 'intermediate': 'I', 'standard': 'S'}
PT_MM = 72 / 25.4
WIDTH, HEIGHT = 742, 350


def scale_denominator(fit, ratio):
    needed = PT_MM / (ratio * fit)
    for decade in (1, 10, 100, 1000, 10000, 100000, 1000000):
        for value in (1, 1.5, 2, 2.5, 3, 4, 5, 7.5):
            if decade*value >= needed-1e-9:
                return decade*value
    return math.ceil(needed)


class Sheet:
    def __init__(self, app, code, title, bounds, box, ratio, font):
        self.drawing = Drawing(WIDTH, HEIGHT)
        self.font = font
        left, top, right, bottom = bounds
        x, y, w, h = box
        fit = min(w/max(right-left, 1e-8), h/max(bottom-top, 1e-8))
        self.denominator = scale_denominator(fit, ratio)
        self.scale = PT_MM/(self.denominator*ratio)
        self.left, self.bottom = left, bottom
        self.ox = x+(w-(right-left)*self.scale)/2
        self.oy = y+(h-(bottom-top)*self.scale)/2
        self.line((0, 31), (WIDTH, 31), width=.6)
        self.text((7, 18), title, 8, bold=True, anchor='start')
        name = str(getattr(app, 'project_name', '') or 'Projet sans nom')
        while stringWidth(name, font, 7) > 380:
            name = name[:-2]
        self.text((7, 7), name, 7, anchor='start')
        revision = fingerprint(app.mounting_plan)[:8].upper()
        self.text((WIDTH-7, 18), f'{code} | {dt.date.today():%d/%m/%Y} | Ref. {revision}', 7, anchor='end')
        self.text((WIDTH-7, 7), f'1:{self.denominator:g} at 100% | dimensions in mm', 7, anchor='end')

    def xy(self, p):
        return self.ox+(p[0]-self.left)*self.scale, self.oy+(self.bottom-p[1])*self.scale

    def line(self, a, b, color=INK, width=.45):
        self.drawing.add(Line(*a, *b, strokeColor=HexColor(color), strokeWidth=width))

    def polygon(self, pts, color=INK, fill=None, width=.45):
        self.drawing.add(Polygon([v for p in pts for v in p], strokeColor=HexColor(color),
                                 fillColor=HexColor(fill) if fill else None, strokeWidth=width))

    def text(self, p, text, size=7.5, color=INK, bold=False, anchor='middle', angle=0, background=False):
        font = 'Helvetica-Bold' if bold else self.font
        group = Group();w = stringWidth(str(text), font, size)
        start = -w/2 if anchor == 'middle' else -w if anchor == 'end' else 0
        if background:
            group.add(Rect(start-2, -size*.35-1, w+4, size+2, fillColor=white, strokeColor=None))
        group.add(String(0, -size*.3, str(text), fontName=font, fontSize=size,
                         textAnchor=anchor, fillColor=HexColor(color)))
        group.translate(*p);group.rotate(angle);self.drawing.add(group)

    def dimension(self, p1, p2, offset, label, vertical=False, side=1):
        a, b = ((offset, p1[1]), (offset, p2[1])) if vertical else ((p1[0], offset), (p2[0], offset))
        for p, q in ((p1, a), (p2, b), (a, b)):
            self.line(p, q, width=.35)
        for x, y in (a, b):
            self.line((x-2, y-2), (x+2, y+2), width=.6)
        # Very short spans are fully specified in the adjacent axis schedule.
        if math.dist(a, b) >= stringWidth(label, self.font, 7.2)+5:
            mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
            pos = (mid[0]+side*6, mid[1]) if vertical else (mid[0], mid[1]+side*6)
            self.text(pos, label, 7.2, angle=90 if vertical else 0, background=True)

    def primitives(self, shapes):
        for s in shapes:
            color = s.get('color', INK)
            if s['kind'] == 'line':
                pts = [self.xy(p) for p in s['points']]
                for a, b in zip(pts, pts[1:]):self.line(a, b, color)
            elif s['kind'] == 'polygon':
                self.polygon([self.xy(p) for p in s['points']], color, s.get('fill') or None, .35)
            elif s['kind'] == 'text':
                self.text(self.xy(s['point']), s['text'], 7.2, color, background=True)

    def scale_bar(self, ratio):
        ideal = 65/self.scale/ratio
        decade = 10**math.floor(math.log10(max(ideal, 1e-9)))
        length = max(v*decade for v in (.1, .2, .5, 1, 2, 5) if v*decade <= ideal)
        end = 727;start = end-length*ratio*self.scale
        self.line((start, 48), (end, 48), width=1)
        for x in (start, end):self.line((x, 45), (x, 51), width=.7)
        self.text(((start+end)/2, 59), f'{length:g} mm', 7)


def motifs(items, plan=None):
    """Group identical effective positions, profiles and physical dimensions."""
    groups = {};assignment = {}
    hidden = set((plan or {}).get('hidden_dimensions',[]))
    overrides = (plan or {}).get('dimension_labels',{})
    def display_settings(uid):
        # Identical geometry but different user annotations must not be merged
        # into a single PDF detail sheet.
        prefix=f'panel:{uid}:'
        return (sorted(k[len(prefix):] for k in hidden if k.startswith(prefix)
                       and (':abc:' in k or ':chain:' in k)),
                sorted((k[len(prefix):],v) for k,v in overrides.items() if k.startswith(prefix)
                       and (':abc:' in k or ':chain:' in k)))
    for uid, item in items.items():
        if not item['config'] or item['issue'] or not item['fixings']:continue
        c = item['config']
        sig = fingerprint((c['width_mm'], c['height_mm'], c['edge'],
            [(f['side'], f['position_mm'], f['kind'], f['reference'], f['length_mm'], f['width_mm']) for f in item['fixings']],
            display_settings(uid)))
        if sig not in groups:groups[sig] = dict(code=f'M{len(groups)+1:02d}', item=item, panels=[])
        group = groups[sig];group['panels'].append(item['number']);assignment[uid] = group['code']
    return list(groups.values()), assignment


def overview(app, items, font, code='MT-01', bounds=None, origin=None, inventory=None):
    ratio = app.px_per_mm
    pts = [p for item in items.values() for p in item['poly']]
    left, top = min(p[0] for p in pts), min(p[1] for p in pts)
    right, bottom = max(p[0] for p in pts), max(p[1] for p in pts)
    # Automatic per-module chains are laid out in the motif details. Keeping
    # them out of the overview prevents hundreds of overlapping labels.
    plan = {'dimensions': [d for d in app.mounting_plan['dimensions'] if not d.get('auto')]}
    shapes = annotations(plan, items, ratio)
    context = []
    if bounds is None:
        from geometry_layout import rotate
        context = [p['points'] for p in getattr(app, 'roof_polygons', []) if p.get('points')]
        for z in getattr(app, 'roof_zones', []):
            if not all(k in z for k in ('x1','y1','x2','y2')):continue
            center = ((z['x1']+z['x2'])/2, (z['y1']+z['y2'])/2)
            context.append([rotate(p,center,z.get('angle_deg',0)) for p in
                ((z['x1'],z['y1']),(z['x2'],z['y1']),(z['x2'],z['y2']),(z['x1'],z['y2']))])
        points = pts+[origin] if origin is not None else list(pts)
        points += [p for poly in context for p in poly]+[p for s in shapes for p in s.get('points', [])]+[s['point'] for s in shapes if 'point' in s]
        bounds = min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)
    else:
        dims = [d for d in plan['dimensions'] if all(
            (p := resolve_point(d, k, items)) is not None and bounds[0] <= p[0] <= bounds[2]
            and bounds[1] <= p[1] <= bounds[3] for k in (1, 2))
            and bounds[0] <= d['label'][0] <= bounds[2] and bounds[1] <= d['label'][1] <= bounds[3]]
        plan = {'dimensions': dims}
        shapes = annotations(plan, items, ratio)
    sheet = Sheet(app, code, 'MOUNTING / GENERAL PLAN' if code == 'MT-01' else 'MOUNTING / ENLARGED VIEW',
                  bounds, (75, 75, 606, 240), ratio, font)
    for poly in context:sheet.polygon([sheet.xy(p) for p in poly], '#888888', width=.3)
    for item in items.values():
        poly = [sheet.xy(p) for p in item['poly']];missing = not item['config'] or item['issue']
        sheet.polygon(poly, '#222222' if missing else '#3d3d3d', '#eeeeee' if missing else '#ffffff')
        short = min(math.dist(poly[0], poly[1]), math.dist(poly[0], poly[3]))
        center = tuple(sum(p[i] for p in poly)/4 for i in (0, 1))
        angle = math.degrees(math.atan2(poly[1][1]-poly[0][1], poly[1][0]-poly[0][0]))
        if short >= max(11, len(str(item['number']))*3.2+3):
            sheet.text(center, item['number'], min(9, max(5, short*.24)), bold=True, angle=angle, background=True)
    rules=app.mounting_plan.get('edge_rules') or {}
    if rules.get('enabled'):
        # Use the full-project physical inventory for tiled views as well.
        # This prevents the same clamp being placed differently on two tiles.
        inventory=inventory or fixing_inventory(geometry(app),ratio,rules.get('max_gap_mm',50))
        physical=(f for f in inventory['physical_fixings']
                  if any(uid in items for uid,index in f['contacts']))
    else:
        physical=(f for it in items.values() for f in it['fixings'])
    for f in physical:
        sheet.polygon([sheet.xy(p) for p in f['world_polygon']], COLORS[f['kind']], COLORS[f['kind']], .25)
    sheet.primitives(annotations(plan, items, ratio, font=7.2/sheet.scale))
    a, b = sheet.xy((left, top)), sheet.xy((right, bottom))
    hidden=set(app.mounting_plan.get('hidden_dimensions',[]))
    if 'field:x' not in hidden:
        sheet.dimension(a, (b[0], a[1]), min(329, a[1]+20), app.mounting_plan.get('dimension_labels',{}).get('field:x',f'X = {(right-left)/ratio:.1f}'))
    if 'field:y' not in hidden:
        sheet.dimension((a[0], b[1]), a, max(31, a[0]-25), app.mounting_plan.get('dimension_labels',{}).get('field:y',f'Y = {(bottom-top)/ratio:.1f}'), True, -1)
    origin = origin if origin is not None else next(iter(items.values()))['poly'][0]
    if bounds[0] <= origin[0] <= bounds[2] and bounds[1] <= origin[1] <= bounds[3]:
        x, y = sheet.xy(origin)
        sheet.line((x-4, y), (x+4, y), '#222222', .8);sheet.line((x, y-4), (x, y+4), '#222222', .8)
        sheet.text((x-8, y+8), (app.mounting_plan.get('site') or {}).get('origin_label','O'), 8, '#222222', bold=True)
    sheet.text((8, 60), 'Shared intermediate clamp: ONE part between TWO frames.', 7, anchor='start')
    sheet.text((8, 48), 'R: end (black)   I: intermediate (gray)   S: uniform (light gray)   !: missing mounting', 7, anchor='start')
    sheet.scale_bar(ratio)
    return sheet.drawing, sheet.scale


def motif_sheet(app, group, font):
    item = group['item'];c = item['config'];w, h = c['width_mm'], c['height_mm']
    sheet = Sheet(app, 'MT-'+group['code'], 'MOUNTING / DETAIL '+group['code'],
                  (0, 0, w, h), (75, 79, 250, 227), 1., font)
    poly = [sheet.xy(p) for p in ((0, 0), (w, 0), (w, h), (0, h))]
    sheet.polygon(poly, INK, '#ffffff', .7);sheet.text(sheet.xy((w/2, h/2)), group['code'], 16, bold=True)
    sheet.text((poly[0][0]+8, poly[0][1]-9), '1', 7, anchor='start')
    sheet.dimension(poly[0], poly[1], poly[0][1]+24, f'{w:.1f}')
    length, cross, along_y = axes(c)
    abc = c['count'] == 6 and c.get('top_offsets_mm') is not None and along_y
    # Keep overall height outside the three independent A/B/C datum lines.
    sheet.dimension(poly[3], poly[0], poly[0][0]-(105 if abc else 44), f'{h:.1f}', True, -1)
    uid=item['uid']
    hidden=set(app.mounting_plan.get('hidden_dimensions',[]))
    overrides=app.mounting_plan.get('dimension_labels',{})
    for side in (0, 1):
        fs = [f for f in item['fixings'] if f['side'] == side]
        if abc and side == 0:
            for station, name in enumerate('ABC'):
                first=sheet.xy((0,0));axis=sheet.xy((0,fs[station]['position_mm']))
                key=f'panel:{uid}:abc:{name}'
                if key not in hidden:
                    sheet.dimension(first,axis,first[0]-15-15*station,
                                    overrides.get(key,f'{name}={fs[station]["position_mm"]:.1f}'),True,-1)
        elif not abc:
            positions = [0]+[f['position_mm'] for f in fs]+[length]
            for j, (start, end) in enumerate(zip(positions, positions[1:])):
                p1 = sheet.xy((side*cross, start) if along_y else (start, side*cross))
                p2 = sheet.xy((side*cross, end) if along_y else (end, side*cross))
                offset = (p1[0]+(-22 if side == 0 else 22)) if along_y else (p1[1]+(20 if side == 0 else -20))
                label = ('A=' if j == 0 else 'B=' if j == len(positions)-2 else '')+f'{end-start:.1f}'
                sign = (-1 if side == 0 else 1) if along_y else (1 if side == 0 else -1)
                key=f'panel:{uid}:chain:{side}:{j}'
                if key not in hidden:
                    sheet.dimension(p1, p2, offset, overrides.get(key,label), along_y, sign)
        for f in fs:
            color = COLORS[f['kind']];sheet.polygon([sheet.xy(p) for p in f['polygon']], color, color, .35)
            x, y = sheet.xy((f['x'], f['y']))
            label = (x+(12 if side == 0 else -12), y) if along_y else (x, y+(-12 if side == 0 else 12))
            sheet.text(label, f'F{f["index"]+1}', 7, color, background=True)
    sheet.text((395, 320), 'CLAMP CONTACTS / AXES', 9, bold=True, anchor='start')
    sheet.text((395, 303), 'Point   Side    Axe mm     Type     Lf × lf mm', 7.5, anchor='start')
    sheet.line((390, 293), (735, 293), width=.5)
    for index, f in enumerate(item['fixings']):
        name=f'F{f["index"]+1}' + (f' / {"ABC"[f["index"]//2]}' if abc else '')
        for x, value in ((399, name), (443, str(f['side']+1)), (490, f'{f["position_mm"]:.1f}'),
                         (560, LETTERS[f['kind']]), (610, f'{f["length_mm"]:g} × {f["width_mm"]:g}')):
            sheet.text((x, 282-index*14), value, 7.5, anchor='start')
    for y, text in ((92, 'A/B/C: three dimensions from top edge to clamp axes.' if abc else
                              'Axis measured from top (vertical) or left (horizontal).'),
                    (79, 'Side 1: left / top; side 2: right / bottom.'),
                    (66, 'Lf: parallel to edge; lf: perpendicular to edge.'),
                    (53, 'Shared I contacts: one physical clamp between two modules.')):
        sheet.text((395, y), text, 7.2, anchor='start')
    return sheet.drawing


def mounting_pages(app, assets, font='Helvetica'):
    """Semantic vector pages for the engineering PDF (no LaTeX source)."""
    plan = getattr(app, 'mounting_plan', None)
    if not plan or not plan.get('panels'):return []
    assets = Path(assets)
    def page(title, items, subtitle=''):
        return dict(section='02 / DRAWINGS', title=title, subtitle=subtitle, items=items, status='MOUNTING / PROJECT DATA')
    if not app.px_per_mm or app.px_per_mm <= 0:
        return [page('Mounting / drawing unavailable', [('note', 'Calibrate the drawing before generating mounting dimensions.')])]
    items = geometry(app)
    if not items:
        return [page('Mounting / drawing unavailable', [('note', 'No saved mounted modules are present in the current Layout.')])]
    groups, assignment = motifs(items,plan)
    rules=plan.get('edge_rules') or {}
    inventory=fixing_inventory(items,app.px_per_mm,rules.get('max_gap_mm',50))
    origin_item = next(iter(items.values()));origin,confirmed = site_origin(app,items)
    origin_name=(plan.get('site') or {}).get('origin_label','O')
    def asset(name, drawing):
        renderPDF.drawToFile(drawing, str(assets/(name+'.pdf')));renderSVG.drawToFile(drawing, str(assets/(name+'.svg')))
        return ('vector', drawing)
    drawing, scale = overview(app, items, font, origin=origin, inventory=inventory)
    result = [page('Mounting / dimensioned general plan', [asset('mounting_general', drawing),
        ('caption', f'Datum {origin_name}: '+('datum set on roof' if confirmed else f'TEMPORARY, corner 1 of module {origin_item["number"]}')+'. X rightwards and Y downwards. '
         'Overall array X/Y dimensions, clear distances on the canvas and clamp positions in the details. Print at 100% to preserve scale.')],
        'Same module IDs as Layout; actual clamp footprints and dimensions in mm')]
    short = min(min(math.dist(i['poly'][0], i['poly'][1]), math.dist(i['poly'][0], i['poly'][3])) for i in items.values())
    digits = max(len(str(i['number'])) for i in items.values())
    if short*scale < max(30, digits*5+8):
        panels = [(i['coord'], i['number'], i['poly']) for i in items.values()]
        for n, (tile, bounds, members) in enumerate(detail_tiles(panels, 610, 230), 1):
            coords = {m[0] for m in members};subset = {u:i for u,i in items.items() if i['coord'] in coords}
            drawing, _ = overview(app, subset, font, f'MT-T{n:02d}', bounds, origin, inventory=inventory)
            result.append(page(f'Mounting / enlarged view {tile}', [asset(f'mounting_tile_{n:03d}', drawing),
                ('caption', 'Adjacent enlarged sheets overlap. Exact coordinates are listed in the placement schedule.')]))
    for group in groups:
        numbers = ', '.join(str(n) for n in group['panels'])
        if len(numbers) > 150:numbers = numbers[:145].rsplit(',', 1)[0]+'… (see placement schedule for remaining modules)'
        result.append(page('Mounting / detail '+group['code'], [asset('mounting_'+group['code'], motif_sheet(app, group, font)),
            ('caption', 'Modules: '+numbers+'. The clamped edge starts at top for vertical mounting, left for horizontal mounting. '
             'With six clamps, A/B/C are three independent distances from the top edge to the clamp centerlines.')], 'Local module orientation; corner 1 indicated in the detail'))
    rows = [[LETTERS[k], ref, length, width, count, inventory['pieces'][(k,ref,length,width)]]
            for (k, ref, length, width), count in inventory['points'].items()]
    for start in range(0, len(rows), 15):
        result.append(page('Mounting / clamp references', [
            ('table', ['Type', 'Reference', 'Lf mm', 'lf mm', 'Contacts', 'Pieces'], rows[start:start+15], [.1,.32,.13,.13,.16,.16]),
            ('note', f"Physical bill of materials: {inventory['pieces_by_kind'].get('edge',0)} end clamps, "
             f"{inventory['pieces_by_kind'].get('intermediate',0)} intermediate clamps, "
             f"{inventory['pieces_by_kind'].get('standard',0)} uniform clamps, total {inventory['pieces_total']} pièces. "
             'A compatible shared intermediate clamp is counted once. Verify on site.'),
            ('note', 'Drawings show configured clamp footprints and axes. Rails, anchors and drilling positions are not defined by these data.')]))
    rows = []
    for uid, item in items.items():
        p, q = item['poly'][:2];angle = math.degrees(math.atan2(q[1]-p[1], q[0]-p[0]))
        rows.append([item['number'], assignment.get(uid, 'TO BE SPECIFIED'), f'{(p[0]-origin[0])/app.px_per_mm:.1f}',
                     f'{(p[1]-origin[1])/app.px_per_mm:.1f}', f'{angle:.2f}', len(item['fixings'])])
    for start in range(0, len(rows), 18):
        result.append(page(f'Mounting / placement {start+1}–{min(start+18,len(rows))}', [
            ('table', ['Module', 'Detail', 'Corner 1 X mm', 'Corner 1 Y mm', 'Angle °', 'Points'], rows[start:start+18], [.13,.23,.18,.18,.14,.14]),
            ('note', f'Datum {origin_name}: '+('site reference set' if confirmed else 'TEMPORARY')+'. Calibrated drawing coordinates: X rightwards, Y downwards. '
             'Angle from corner 1 to corner 2 is clockwise positive. Use the general drawing datum dimensions for positioning on the roof.')]))
    spaces = nearest_gaps(items, app.px_per_mm)
    gap_rows = []
    for uid,it in sorted(items.items(),key=lambda pair:pair[1]['number']):
        record=spaces[uid]
        gap_rows.append([it['number'],
            ('P'+str(record['u'][0])) if record['u'] else '-',
            f"{record['u'][1]:.1f}" if record['u'] else '-',
            ('P'+str(record['v'][0])) if record['v'] else '-',
            f"{record['v'][1]:.1f}" if record['v'] else '-'])
    for start in range(0,len(gap_rows),18):
        result.append(page('Mounting / module gaps', [
            ('table', ['Module','Neighbor +U','Gap U mm','Neighbor +V','Gap V mm'],gap_rows[start:start+18],[.14,.22,.21,.22,.21]),
            ('note','U: corner 1 to corner 2; V: corner 1 to corner 4. Clear gaps between aligned parallel edges, computed from Layout. -: no neighbor on that side.')]))
    issues = [f'Module {i["number"]} : {i["issue"] or "mounting not specified"}' for i in items.values() if i['issue'] or not i['config']]
    missing = sum(resolve_point(d, k, items) is None for d in plan['dimensions'] for k in (1, 2))
    if missing:issues.append(f'{missing} missing dimension references: correct dimensions in Mounting.')
    for start in range(0, len(issues), 18):
        result.append(page('Mounting / missing data', [('note', '\n'.join(issues[start:start+18]))]))
    return result
