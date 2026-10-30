"""Independent A3 PDF delivery package for installers (no LaTeX, all vector)."""
import datetime as dt
import math
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.graphics import renderPDF
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from xml.sax.saxutils import escape
from mounting_drawing import geometry,site_origin
from mounting_spacing import nearest_gaps
from mounting_quantities import fixing_inventory
from mounting import axes
from report_mounting import overview,motifs,motif_sheet
from project_store import fingerprint

PAGE_W,PAGE_H=landscape(A3)
MARGIN=48
DARK=colors.HexColor('#161616')
TEAL=colors.HexColor('#202020')
GRAY=colors.HexColor('#555555')
PALE=colors.HexColor('#f2f2f2')
STYLE=ParagraphStyle('cell',fontName='Helvetica',fontSize=8.5,leading=11,textColor=DARK)
HEAD=ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=8.3,leading=11,textColor=colors.white)
SMALL=ParagraphStyle('sub',fontName='Helvetica',fontSize=9,leading=13,textColor=DARK)


def fmt(value):return f'{value:.1f}'


def write_installer_pdf(app,path):
    """Physical A3 drawing, fixing schedule and prerequisites. All data from app.

    This is an installation geometry deliverable, NOT a structural approval.
    """
    if getattr(app,'px_per_mm',0)<=0:raise ValueError('The drawing must be calibrated in mm.')
    items=geometry(app)
    if not items:raise ValueError('No modules to display.')
    site=app.mounting_plan.get('site') or {}
    origin,confirmed=site_origin(app,items)
    groups,assign=motifs(items,app.mounting_plan)
    rules=app.mounting_plan.get('edge_rules') or {}
    inventory=fixing_inventory(items,app.px_per_mm,rules.get('max_gap_mm',50))
    roof=site.get('roof_reference') or 'TO BE CONFIRMED'
    support=site.get('support_reference') or 'TO BE CONFIRMED'
    anchor=site.get('anchor_reference') or 'TO BE CONFIRMED'
    origin_label=site.get('origin_label') or 'O'
    rev=site.get('revision') or '-'
    docref=site.get('drawing_reference') or 'MT-01'
    issued=dt.date.today().strftime('%d/%m/%Y')
    stamp=f'{fingerprint(app.mounting_plan)[:10].upper()}'
    issues=[f"P{it['number']}: {it['issue'] or 'montage not defined'}" for it in items.values() if not it['config'] or it['issue']]
    if not confirmed:issues.insert(0,'Site datum is temporary: confirm on the roof and drawing.')
    pdf=canvas.Canvas(str(path),pagesize=(PAGE_W,PAGE_H),pageCompression=1)
    pdf.setTitle(f"{app.project_name} - PV Installation Package")
    pdf.setAuthor('Mounting drawing - project data')
    total=[0]

    def text(x,y,value,size=9,bold=False,color=DARK):
        pdf.setFillColor(color);pdf.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
        pdf.drawString(x,y,str(value))

    def page(title,subtitle=''):
        total[0]+=1
        pdf.setStrokeColor(TEAL);pdf.setLineWidth(2)
        pdf.line(MARGIN,PAGE_H-71,PAGE_W-MARGIN,PAGE_H-71)
        text(MARGIN,PAGE_H-46,'INSTALLATION PACKAGE | PHOTOVOLTAIC',15,True,TEAL)
        text(MARGIN,PAGE_H-63,title,11,True,DARK)
        text(MARGIN,PAGE_H-89,subtitle,8,False,GRAY)
        pdf.setStrokeColor(colors.HexColor('#aaaaaa'));pdf.setLineWidth(.5)
        pdf.line(MARGIN,44,PAGE_W-MARGIN,44)
        text(MARGIN,29,f'{docref}  |  Revision {rev}  |  {issued}  |  Fingerprint {stamp}',8,False,GRAY)
        pdf.setFont('Helvetica',8);pdf.setFillColor(GRAY)
        pdf.drawRightString(PAGE_W-MARGIN,29,f'Page {total[0]}  ·  Dimensions in mm · A3 landscape / 100%')

    def block(label,value,x,y,width=355):
        text(x,y,label.upper(),8,True,GRAY)
        p=Paragraph(escape(str(value)).replace('\n','<br/>'),SMALL)
        _,height=p.wrap(width,90);p.drawOn(pdf,x,y-height-5)
        return y-height-5

    def table(headers,rows,widths,x,y,limit_y=65,compact=False):
        def cell(v,style=STYLE):return Paragraph(escape(str(v)),style)
        data=[[cell(v,HEAD) for v in headers]]+[[cell(v) for v in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),DARK),('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),3 if compact else 6),
            ('BOTTOMPADDING',(0,0),(-1,-1),3 if compact else 6),('LEFTPADDING',(0,0),(-1,-1),7),
            ('LINEBELOW',(0,-1),(-1,-1),.45,colors.HexColor('#999999'))]))
        _,h=t.wrap(sum(widths),y-limit_y)
        if y-h<limit_y:raise ValueError('Table is too tall for the page.')
        t.drawOn(pdf,x,y-h)
        return y-h

    page('01 / DIMENSIONED GENERAL PLAN',f"Project: {app.project_name}   ·   Drawing {docref}   ·   Revision {rev}")
    drawing,_=overview(app,items,'Helvetica',origin=origin,inventory=inventory)
    scale=min((PAGE_W-2*MARGIN)/742,(PAGE_H-275)/350)
    pdf.saveState();pdf.translate((PAGE_W-742*scale)/2,200)
    pdf.scale(scale,scale);renderPDF.draw(drawing,pdf,0,0);pdf.restoreState()
    y=173
    block('Coordinate datum',f"{origin_label} : " + ('datum set (verify on site)' if confirmed else 'TEMPORARY (corner 1 of first module)'),MARGIN,y,495)
    block('Supports / rails',support,MARGIN+580,y,495)
    block('Roof reference',roof,MARGIN,y-46,495)
    block('Fasteners / anchors',anchor,MARGIN+580,y-46,495)
    text(MARGIN,59,'Geometric plan: dimensions refer to clamp centerlines. Do not use this document alone to validate anchorage.',8,False,GRAY)
    pdf.showPage()

    page('02 / SITE DATA AND CHECKS',f"{len(items)} modules  |  {inventory['points_total']} contacts  |  {inventory['pieces_total']} estimated physical clamps  |  {len(groups)} configurations")
    y=PAGE_H-119
    for name,value in [('Roof / area',roof),('Rails and supports',support),('Anchors / fasteners',anchor),
                       ('Intermediate clamp gap (mm)',f"{rules.get('joint_gap_mm',0):g} (minimum setting; actual geometric gap shown in gap schedule)"),
                       ('Origin datum',f'{origin_label} - '+('set, verify on site' if confirmed else 'TEMPORARY'))]:
        y=block(name,value,MARGIN,y,PAGE_W-2*MARGIN)-24
    y-=8
    text(MARGIN,y,'CHECKS REQUIRED BEFORE INSTALLATION',11,True,TEAL);y-=21
    checks=['Drawing calibration and site datum surveyed and verified on site.',
            'Actual purlin/rail locations, obstructions, joints and roof waterproofing checked.',
            'Clamp references and module compatibility confirmed by manufacturers.',
            'Clamp strength, pull-out resistance, wind/snow and structure verified separately.',
            'Fasteners, drilling pitch, tightening torques and corrosion protection confirmed.']
    for check in checks:
        pdf.setStrokeColor(TEAL);pdf.rect(MARGIN,y-3,9,9,fill=0,stroke=1)
        text(MARGIN+19,y,check,10);y-=29
    if site.get('installer_notes'):
        y-=12;text(MARGIN,y,'PROJECT INSTALLATION INSTRUCTIONS',11,True,TEAL);y-=20
        p=Paragraph(escape(site['installer_notes']).replace('\n','<br/>'),SMALL)
        w,h=p.wrap(PAGE_W-2*MARGIN,150);p.drawOn(pdf,MARGIN,y-h);y-=h+14
    if issues:
        text(MARGIN,y,'MISSING OR INCOMPATIBLE INFORMATION',11,True,colors.HexColor('#000000'));y-=18
        for item in issues[:12]:
            p=Paragraph(escape(item),SMALL);w,h=p.wrap(PAGE_W-2*MARGIN,34)
            p.drawOn(pdf,MARGIN,y-h);y-=h+4
            if y<65:break
    pdf.showPage()

    totals=inventory['points']
    pieces=inventory['pieces']
    profiles=[[{'edge':'End','intermediate':'Int.','standard':'Uniform'}[kind],ref,fmt(l),fmt(w),count,pieces[(kind,ref,l,w)]]
              for (kind,ref,l,w),count in sorted(totals.items())]
    if profiles:
        for part in range(0,len(profiles),24):
            page('03 / CLAMP BILL OF MATERIALS',
                 f"End {inventory['pieces_by_kind'].get('edge',0)} | Intermediates {inventory['pieces_by_kind'].get('intermediate',0)} | Uniforms {inventory['pieces_by_kind'].get('standard',0)} | TOTAL {inventory['pieces_total']} pieces")
            table(['Type','Manufacturer reference','Lf (mm)','lf (mm)','Contacts','Pieces'],profiles[part:part+24],
                  [127,473,105,105,135,135],MARGIN,PAGE_H-119)
            text(MARGIN,90,"Contacts = points per module; pieces = physical clamps (shared clamps counted once).",8,False,GRAY)
            text(MARGIN,74,f"Unpaired intermediate contacts: {inventory['unpaired_intermediate']} ; verify references and axes on site.",8,False,GRAY)
            pdf.showPage()

    for group in groups:
        item=group['item'];c=item['config'];fs=item['fixings']
        names=', '.join(str(n) for n in group['panels'])
        page('04 / INSTALLATION DETAIL '+group['code'],f"Modules: {names[:145]}{'...' if len(names)>145 else ''}")
        detail=motif_sheet(app,group,'Helvetica')
        sc=1.0
        pdf.saveState();pdf.translate((PAGE_W-742)/2,363);pdf.scale(sc,sc);renderPDF.draw(detail,pdf,0,0);pdf.restoreState()
        axis='Local Y (from corner 1, downwards)' if axes(c)[2] else 'Local X (from corner 1, rightwards)'
        abc=c['count']==6 and c.get('top_offsets_mm') is not None and axes(c)[2]
        text(MARGIN,337,(f'6 clamps: A={c["top_offsets_mm"][0]:g} mm   B={c["top_offsets_mm"][1]:g} mm   '
                           f'C={c["top_offsets_mm"][2]:g} mm  |  3 pairs, measured from TOP EDGE.'
                           if abc else f'Position of each centerline: {axis}   |   Measured from the start edge of the module.'),
             9,True,TEAL)
        rows=[[(f'F{f["index"]+1} / {"ABC"[f["index"]//2]}' if abc else f'F{f["index"]+1}'),
               f['side']+1,fmt(f['position_mm']),
                {'edge':'End','intermediate':'Int.','standard':'Uniform'}[f['kind']],
                f['reference'] or 'TO BE CONFIRMED',f"{f['length_mm']:g} × {f['width_mm']:g}"] for f in fs]
        # Up to 12 fixings, fits under detail with row height ~23.
        table(['Point','Side','Axis (mm)','Type','Reference','Lf × lf (mm)'],rows,
              [82,88,155,180,340,210],MARGIN,320,limit_y=54,compact=True)
        pdf.showPage()

    # A fixing list alone is not enough for staking out a whole array: include
    # each panel's datum, detail reference and in-plane rotation as a separate schedule.
    panels=[]
    for uid,item in sorted(items.items(),key=lambda pair:pair[1]['number']):
        p1,p2=item['poly'][:2]
        panels.append([item['number'],assign.get(uid,'TO BE SPECIFIED'),
            fmt((p1[0]-origin[0])/app.px_per_mm),fmt((p1[1]-origin[1])/app.px_per_mm),
            fmt(math.degrees(math.atan2(p2[1]-p1[1],p2[0]-p1[0]))),
            len(item['fixings']),
            (f"{item['config']['width_mm']:g} × {item['config']['height_mm']:g}"
             if item['config'] else 'TO BE SPECIFIED')])
    for start in range(0,len(panels),24):
        page('05 / MODULE PLACEMENT',
             f'Datum {origin_label}: '+('set, verify on site' if confirmed else 'TEMPORARY')+
             '  ·  X rightwards / Y downwards  ·  plan angle from corner 1 to corner 2')
        table(['M.','Detail','Corner 1 X','Corner 1 Y','Rotation (°)','Points','Width × height (mm)'],
              panels[start:start+24],[80,150,185,185,150,110,220],MARGIN,PAGE_H-119)
        text(MARGIN,80,'Coordinates in calibrated drawing. No slope correction or topographic projection.',9,False,GRAY)
        pdf.showPage()

    # Explicit free spaces between aligned neighboring panels, measured from
    # the current calepinage in the local module U/V axes. A dash means no
    # forward aligned neighbor: no spacing is invented for isolated panels.
    gaps=nearest_gaps(items,app.px_per_mm)
    gaps_rows=[]
    for uid,it in sorted(items.items(),key=lambda pair:pair[1]['number']):
        g=gaps[uid]
        def target(value):
            return (f'P{value[0]}',fmt(value[1])) if value is not None else ('—','—')
        nu,du=target(g['u']);nv,dv=target(g['v'])
        gaps_rows.append([it['number'],nu,du,nv,dv])
    for start in range(0,len(gaps_rows),25):
        page('06 / MODULE-TO-MODULE GAPS',
             'U: from corner 1 to 2 | V: from corner 1 to 4 | clear gap between parallel edges (mm)')
        table(['Module','Neighbor +U','Gap U (mm)','Neighbor +V','Gap V (mm)'],
              gaps_rows[start:start+25],[125,225,230,225,230],MARGIN,PAGE_H-119,compact=True)
        text(MARGIN,78,'Dimensions computed from Layout; —: no aligned parallel neighbor. Plan-projected distances.',8,False,GRAY)
        pdf.showPage()

    # One coordinate per *physical* clamp. Per-panel contact coordinates are
    # included separately below: they must not be mistaken for extra parts.
    physical_rows=[]
    for number,part in enumerate(inventory['physical_fixings'],1):
        x,y=part['point']
        contacts=' + '.join(f"P{items[uid]['number']}/F{index+1}" for uid,index in part['contacts'])
        physical_rows.append([f'M{number}',
            {'edge':'End','intermediate':'Int.','standard':'Uniform'}[part['kind']],
            fmt((x-origin[0])/app.px_per_mm),fmt((y-origin[1])/app.px_per_mm),
            contacts,f"{part['length_mm']:g} × {part['width_mm']:g}",part['reference']])
    for start in range(0,len(physical_rows),24):
        page('07 / PHYSICAL CLAMP COORDINATES',
             'ONE row per installed clamp; axis at clamp center; coordinates from site datum')
        table(['Piece','Type','Axis X (mm)','Axis Y (mm)','Module contacts','Lf × lf (mm)','Reference'],
              physical_rows[start:start+24],[70,133,138,138,220,128,250],MARGIN,PAGE_H-119,compact=True)
        text(MARGIN,80,'A shared intermediate clamp is centered on the joint and connects two contact points.',8,False,GRAY)
        pdf.showPage()

    schedule=[]
    for uid,item in sorted(items.items(),key=lambda pair:pair[1]['number']):
        for f in item['fixings']:
            x=fmt((f['point'][0]-origin[0])/app.px_per_mm)
            y=fmt((f['point'][1]-origin[1])/app.px_per_mm)
            schedule.append([item['number'],f['index']+1,f['side']+1,fmt(f['position_mm']),x,y,
                {'edge':'End','intermediate':'Int.','standard':'Uniform'}[f['kind']],
                f['reference'] or 'TO BE CONFIRMED',f"{f['length_mm']:g} × {f['width_mm']:g}",assign.get(uid,'-')])
    for start in range(0,len(schedule),24):
        page('08 / CLAMP CONTACT COORDINATES',f"X/Y in mm from {origin_label} ({'set, verify on site' if confirmed else 'TEMPORARY'})  ·  clamp centerlines  ·  rows {start+1} to {min(start+24,len(schedule))}")
        table(['M.','F.','Edge','Local axis','Site X','Site Y','Type','Reference','Lf × lf','Detail'],
              schedule[start:start+24],[49,49,64,107,112,112,111,246,113,93],MARGIN,PAGE_H-119)
        text(MARGIN,80,'Calibrated drawing projected coordinates; not GPS coordinates or drilling locations.',9,False,GRAY)
        pdf.showPage()
    # Annotation strings are presentation-only; never use them as measured
    # fixing coordinates. List all overrides explicitly for site traceability.
    overrides=app.mounting_plan.get('dimension_labels',{})
    manual=[(f'Annotation #{index+1}',d['text_override']) for index,d in
            enumerate(app.mounting_plan.get('dimensions',[])) if d.get('text_override')]
    labels=list(overrides.items())+manual
    for start in range(0,len(labels),12):
        page('09 / CUSTOM DIMENSION LABELS',
             'Free text does NOT replace geometric values or coordinate schedules')
        table(['Drawing identifier','Displayed custom text'],
              labels[start:start+12],[480,605],MARGIN,PAGE_H-119,compact=True)
        text(MARGIN,75,'Measured positions and distances are those listed in the calculated schedules.',9,False,GRAY)
        pdf.showPage()
    pdf.save()
    return dict(panels=len(items),fixing_points=len(schedule),fixing_pieces=inventory['pieces_total'],issues=issues,pages=total[0])
