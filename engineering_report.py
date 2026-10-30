"""Desktop engineering report: current inputs, explicit omissions and vector PDF.

No external services and no inferred equipment ratings. ReportLab generates the
PDF generated directly with ReportLab; no LaTeX source is generated.
"""
from pathlib import Path
from datetime import datetime, timezone
from html import escape
import json
import os
import re
from project_validation import audit_project
from energy_charts import comparison_figure
from project_validation import natural

MISSING='-'


def scalar(value):
    if value is None or value=='':return MISSING
    if isinstance(value,float):return f'{value:,.4f}'.rstrip('0').rstrip('.')
    if isinstance(value,(dict,list,tuple)):return json.dumps(value,ensure_ascii=False)
    return str(value)


def report_content(app,assets,font="Times-Roman",progress=None):
    assets.mkdir(parents=True,exist_ok=True)
    from report_studies import refresh_report_energy
    app._prepare_project_save()
    refresh_report_energy(app,progress)
    data=app._project_snapshot()
    data.update(app._prepare_project_save())
    if hasattr(app,'_collect_project_data'):data.update(app._collect_project_data())
    for name in ('roof_image_path','roof_polygons','measures','project_notes','cable_calc_params',
                 'panel_tilt_deg','panel_azimuth_deg','panel_temp_coeff_pct','panel_noct_c',
                 'solar_latitude','solar_longitude','solar_utc_offset','north_offset_deg',
                 'pylon_img_pos','pylon_ref_img_pos','pylon_height_mm','pylon_width_mm','pylon_opacity',
                 'shadow_result','shadow_simulation_results','diagram_electrical_specs'):
        data[name]=getattr(app,name,None)
    data['panel_orientations']={','.join(map(str,k)):v for k,v in app.panel_orientations.items()}
    # Tuple keys in shadow result dictionaries are not JSON object keys.
    def serial(obj):
        if isinstance(obj,dict):return {str(k):serial(v) for k,v in obj.items()}
        if isinstance(obj,(list,tuple)):return [serial(v) for v in obj]
        return obj
    (assets/'project_inputs.json').write_text(json.dumps(serial(data),ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    blocks=[]
    def heading(t):blocks.append(('heading',t))
    def para(t):blocks.append(('text',t))
    def table(headers,rows):blocks.append(('table',headers,[[scalar(v) for v in r] for r in rows]))
    def figure(name,caption):blocks.append(('image',assets/name,caption))
    heading('1. Project and calculation status')
    para(f"Project: {app.project_name}. Exported {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Application R14. Engineering review document; no certification is asserted.")
    current=app._energy_results_current()
    table(['Item','Value'],[['Module count',len(app.panels)],['Module STC power (W)',app.panel_pmax_w],
        ['Installed DC nameplate (kWp)',(__import__('engineering_inputs').installed_power_w(data)/1000 if __import__('engineering_inputs').installed_power_w(data) is not None else None)],['Image scale (px/mm)',app.px_per_mm],
        ['Energy results current',current],['Source image',getattr(app,'roof_image_path',None)]])
    issues=audit_project(data)
    para('Layout checks: '+('; '.join(app._layout_issues()) or 'No overlap or out-of-zone module detected.'))
    para(f'Electrical/project audit: {len(issues)} open check(s).' if issues else 'No issue returned by the implemented checks. This is not a complete electrical design verification.')
    data['report_audit_issues']=issues
    if issues:
        grouped={}
        for issue in issues:
            match=re.match(r'^(String .*?): (.*)$',issue)
            subject,message=(match[1],match[2]) if match else ('Project',issue)
            grouped.setdefault(message,[]).append(subject)
        table(['Electrical / project check','Affected records','Count'],[[message,', '.join(subjects),len(subjects)] for message,subjects in grouped.items()])
    missing=[f'Zone {i+1}: installation height missing' for i,z in enumerate(app.roof_zones) if z.get('installation_height_m') is None]
    missing += [f'Polygon {i+1}: installation height missing' for i,z in enumerate(app.roof_polygons) if z.get('installation_height_m') is None]
    para('Missing cable inputs: '+('; '.join(missing) if missing else 'No missing area heights.'))
    heading('2. Plan, installation areas and dimensions')
    table(['Zone','Width (mm)','Height (mm)','Layout rotation (deg)','Cable elevation (m)','Shadow elevation (mm)'],[
        [i+1,abs(z['x2']-z['x1'])/app.px_per_mm if app.px_per_mm else None,
         abs(z['y2']-z['y1'])/app.px_per_mm if app.px_per_mm else None,z.get('angle_deg',0),
         z.get('installation_height_m'),z.get('z_mm')] for i,z in enumerate(app.roof_zones)])
    table(['Routing polygon','Vertices (image pixels)','Cable elevation (m)'],[
        [i+1,p.get('points'),p.get('installation_height_m')] for i,p in enumerate(app.roof_polygons)])
    para('Layout rotation is the in-plane rotation of the module placement grid, not the module tilt relative to horizontal. Module tilt is recorded separately. Panel grid rotates as a rigid lattice. Complete panel corners must remain inside the zone. Fire corridors, mounting gaps and maintenance access must be reserved in the installation boundaries. Dimensions in this section derive from the entered image scale.')
    from matplotlib.figure import Figure
    para('Vector plates at the end of this report include installation, string connections, cable paths and a numbered detail atlas. They retain sharp lines and selectable module identifiers at any zoom level.')
    if app.px_per_mm:
        rows=[]
        from math import hypot
        for m in app.measures:
            if not isinstance(m,dict):continue
            dx=m['p2'][0]-m['p1'][0];dy=m['p2'][1]-m['p1'][1];mode=m.get('axis','aligned')
            length=abs(dx) if mode=='horizontal' else abs(dy) if mode=='vertical' else hypot(dx,dy)
            rows.append([mode,m['p1'],m['p2'],length/app.px_per_mm])
        table(['Dimension','Start (px)','End (px)','Length (mm)'],rows)
    heading('3. Equipment and electrical schedule')
    from configuration_form import prepare,fields,get
    descriptors=fields(prepare(data))
    from mixins.material_tools import MATERIAL_CATEGORY_DEFS
    evaluated=app._compute_material_formulas()
    def equipment_value(category,row,key,value):
        if isinstance(value,str) and value.strip().startswith('='):
            columns=MATERIAL_CATEGORY_DEFS.get(category,('',[]))[1]
            return evaluated.get((category,row,columns.index(key)), '#ERR') if key in columns else '#ERR'
        return value
    def entered(field):
        value=get(data,field.path,None)
        if len(field.path)==5 and field.path[0]=='material_categories' and field.path[2]=='rows':
            value=equipment_value(field.path[1],field.path[3],field.path[4],value)
        return int(value)+1 if field.kind=='row' and value is not None else value
    table(['Input group','Technical input','Entered value'],[[field.section,field.label,entered(field)] for field in descriptors if not field.section.startswith(('String String','Equipment')) and entered(field) not in (None,'')])
    for category,content in app.material_categories.items():
        para('Equipment category: '+category)
        rows=content.get('rows',[])
        if rows:
            from mixins.material_tools import MATERIAL_COLUMNS_EN
            table(['Equipment row','Parameter','Entered value'],[[i+1,MATERIAL_COLUMNS_EN.get(key,key),equipment_value(category,i,key,value)] for i,row in enumerate(rows) for key,value in row.items()])
        else:para(MISSING)
    table(['String','Modules in electrical order','Inverter','MPPT'],[
        [sid,', '.join(str(app.panels.get(tuple(p),'MISSING')) for p in coords),
         app.string_mppt_assignment.get(sid,{}).get('block'),app.string_mppt_assignment.get(sid,{}).get('mppt')]
        for sid,coords in sorted(app.strings.items(),key=lambda item:natural(item[0])) if coords])
    for index,(name,block) in enumerate(app.blocks.items(),1):
        assignments=[(sid,a) for sid,a in app.string_mppt_assignment.items() if a.get('block')==name]
        groups={}
        for sid,a in assignments:groups.setdefault(a.get('mppt'),[]).append(sid)
        if not groups:continue
        fig=Figure(figsize=(9,max(2,len(groups)*.55)),dpi=160);ax=fig.subplots();ax.axis('off')
        for j,(mppt,strings) in enumerate(sorted(groups.items(),key=lambda x:str(x[0]))):
            y=len(groups)-j
            ax.text(.02,y,', '.join(strings),ha='left',va='center',fontsize=8)
            ax.annotate('',(.56,y),(.35,y),arrowprops={'arrowstyle':'->','color':'black'})
            ax.text(.6,y,f'MPPT {mppt}',va='center',fontsize=9)
            ax.plot([.76,.85,.85],[y,y,(len(groups)+1)/2],color='black',linewidth=.8)
        ax.text(.88,(len(groups)+1)/2,name,va='center',fontsize=10)
        ax.set_xlim(0,1.08);ax.set_ylim(0,len(groups)+1);fig.tight_layout();filename=f'single_line_{index}.png';fig.savefig(assets/filename);figure(filename,f'Functional DC topology for {name}, derived from current assignments. Protection and AC connection design are not inferred.')
    heading('4. DC cable routes and voltage-drop method')
    para('L_pole = sum(planar segment lengths) + sum(abs(height changes)) + reserve. L_loop = L_A + L_B. A starts at the first module, B at the last. Inter-module and AC wiring are excluded. Short gaps retain the upstream elevation up to the configured bridge threshold; longer unsupported spans use ground level.')
    table(['Routing input','Value'],list(app.routing_settings.items()))
    routes=[];route_issues=[]
    for sid,coords in sorted(app.strings.items(),key=lambda item:natural(item[0])):
        if not coords:continue
        rec=app._calculate_two_pole_route(sid)
        if rec:routes.append((sid,rec))
        else:route_issues.append(sid)
    if hasattr(app,'_route_signature'):
        app.electrical_route_plan_3d={'routes':dict(routes),'source_signature':app._route_signature(),'status':'Report calculation snapshot'}
    table(['String','A (m)','B (m)','Loop (m)','Current (A)','Voltage (V)','Section (mm2)','Drop (%)','Mass (kg)','Check status'],[
        [sid,r['terminal_A']['length_m'],r['terminal_B']['length_m'],r['loop_length_m'],r.get('current_a'),r.get('voltage_v'),r.get('working_section_mm2'),r.get('drop_at_working_section_pct'),r.get('mass_kg'),r.get('ampacity_status')] for sid,r in routes])
    table(['String / conductor','Planar (m)','Vertical steps (m)','Reserve (m)','Method'],[[sid+' / '+key[-1],r[key].get('horizontal_m'),r[key]['vertical_drop_m'],r[key]['terminal_reserve_m'],r[key]['method']] for sid,r in routes for key in ('terminal_A','terminal_B')])
    para('Routes unavailable: '+(', '.join(route_issues) if route_issues else 'None.'))
    para('Voltage drop: dU = rho I L_loop / S; dU_percent = 100 dU / U. Cross-section addresses voltage drop only. Ampacity, fault current, cable temperature, protective devices and installation conditions require separate design checks.')
    table(['Sizing input','Value'],list(app.cable_calc_params.items()))
    table(['String','Override inputs','kg/m','Mass (kg)','Ampacity / drop check'],[[sid,scalar(data.get('cable_string_params',{}).get(sid,{})),data.get('cable_mass_by_section',{}),r.get('mass_kg'),r.get('ampacity_status')] for sid,r in routes if data.get('cable_string_params',{}).get(sid) or data.get('cable_mass_by_section')])
    heading('5. Solar, thermal and shadow assumptions')
    fields=['solar_latitude','solar_longitude','solar_utc_offset','north_offset_deg','panel_tilt_deg','panel_azimuth_deg',
            'panel_temp_coeff_pct','panel_noct_c','pylon_height_mm','pylon_width_mm','pylon_opacity']
    table(['Input','Value'],[[k,data[k]] for k in fields])
    para('P = P_STC (G_effective / 1000) max(0, 1 + mu_P (T_cell - 25)/100). T_cell = T_ambient + (NOCT - 20) G_effective / 800. Shadow length = (H_obstacle - H_roof) / tan(solar elevation), for positive height difference and solar elevation. Energy integrates power over the calculation period. Shadow is a geometric approximation, not an electrical mismatch or bypass-diode simulation. Saved shadow details are included in the input snapshot; they are not asserted current without a fresh simulation.')
    from report_studies import shadow_blocks,spreadsheet_blocks
    study_blocks,annual=shadow_blocks(app,assets,progress)
    blocks.extend(study_blocks)
    data['report_annual_shadow_study']={key:value for key,value in annual.items() if key!='timeline'}
    spreadsheet_blocks(app,assets)  # Preserve companion CSV exports.
    from mixins.spreadsheet_tools import col_letter,cell_id
    sheet=getattr(app,'material_spreadsheet',{}) or {}
    if sheet:
        calculated=app._compute_spreadsheet_values();nrows=int(sheet.get('rows',20));ncols=int(sheet.get('cols',8));cells=sheet.get('cells',{})
        def sheet_value(row,col):
            raw=str(cells.get(cell_id(row,col),'') or '')
            return raw+'\nValue: '+scalar(calculated.get((row,col),'')) if raw.strip().startswith('=') else raw
        blocks.append(('sheet',['Row']+[col_letter(c) for c in range(ncols)],[[str(r+1)]+[sheet_value(r,c) for c in range(ncols)] for r in range(nrows)]))
    else:
        blocks.append(('heading','Complete spreadsheet'));para('No spreadsheet supplied.')
    heading('6. Energy and BESS comparison')
    para('PV serves the load first, surplus charges the battery, remaining PV is exported up to the grid limit, then curtailed. BESS discharge meets remaining load. No grid charging, arbitrage or ancillary-service revenue is modelled. Two cabinets double energy capacity and retain shared power limits.')
    table(['Input','Value'],list(app.energy_input_settings.items())+list(app.grid_connection_settings.items()))
    profile=app.hourly_consumption_profile or {}
    para(f"Imported consumption: {len(profile.get('hourly_kwh',[]))} hourly values, {len(profile.get('imputed_indices',[]))} filled values. Totals cover that period, not necessarily a complete year. Weather/production method: {app.self_consumption_summary.get('method',MISSING)}.")
    para('For a one-hour step: direct = min(PV, load). Charge = min(surplus, charge limit, remaining storage / eta). Discharge = min(deficit, discharge limit, available storage * eta). eta = sqrt(round-trip efficiency). Stored energy changes by charge * eta - discharge / eta. Load = direct + discharge + grid. PV = direct + charge + export + curtailment.')
    summaries=[app.self_consumption_summary,app.bess_summary,app.two_bess_summary]
    if current and all(s.get('annual') for s in summaries):
        keys=sorted(set().union(*(s['annual'] for s in summaries)))
        table(['Metric','PV only','1 BESS','2 BESS'],[[k.replace('_',' '),*[s['annual'].get(k) for s in summaries]] for k in keys])
        for chart_page in _report_energy_chart_pages(app,assets,summaries):
            heading(chart_page['title'])
            para(chart_page['subtitle'])
            for item in chart_page['items']:
                if item[0]=='image':figure(Path(item[1]).name,'')
                elif item[0]=='caption':para(item[1])
        monthly_keys=sorted(set().union(*(row.keys() for summary in summaries for row in summary.get('monthly',{}).values())))
        monthly_names=sorted(set().union(*(summary.get('monthly',{}) for summary in summaries)))
        table(['Month','Metric','PV only','1 BESS','2 BESS'],[[month,key.replace('_',' '),*[summary.get('monthly',{}).get(month,{}).get(key) for summary in summaries]] for month in monthly_names for key in monthly_keys])
        table(['Month','Case','PV kWh','Load kWh','Grid kWh','Export kWh'],[
            [month,label,row.get('pv_kwh'),row.get('load_kwh'),row.get('grid_kwh'),row.get('export_kwh')]
            for label,summary in zip(['PV only','1 BESS','2 BESS'],summaries) for month,row in sorted(summary.get('monthly',{}).items())])
        from energy_economics import evaluate_options
        economic_inputs=dict(app.economic_settings)
        from energy_economics import covers_full_year
        if not covers_full_year(profile):economic_inputs['annual_maintenance_eur']=economic_inputs.get('annual_maintenance_eur',0)*len(profile.get('hourly_kwh',[]))/8766
        economics=evaluate_options([s['annual'] for s in summaries],economic_inputs)
        from energy_economics import covers_full_year
        annual_period=covers_full_year(profile)
        table(['BESS count','Export price (EUR/kWh)','Benefit over period (EUR)','Investment (EUR)','Payback (years)'],[
            [r.get('bess_count'),r.get('export_eur_kwh'),r['total_benefit_eur'],r['capex_eur'],
             r['simple_payback_years'] if annual_period else 'Not calculated: partial year'] for r in economics])
        if annual_period:table(['BESS count','Export price','NPV (EUR)','Discounted payback (years)'],[[r['bess_count'],r['export_eur_kwh'],r['net_present_value_eur'],r['discounted_payback_years']] for r in economics])
        if not annual_period:para('Payback is withheld because consumption does not cover a complete year. Monetary benefits shown cover only the imported period.')
    else:para('Energy comparison unavailable: '+getattr(app,'_report_energy_error','Energy results are missing or stale. Recalculate Energy / BESS.')+' Stored historical results remain in the JSON snapshot for traceability only.')
    heading('7. Economic inputs and interpretation')
    table(['Input','Value'],list(app.economic_settings.items()))
    para('Avoided purchases = useful PV energy supplied to load x import price. Export revenue = exported energy x export price. Compare incremental battery value against PV-only. Simple payback excludes financing, tax, discounting, degradation, maintenance and replacement unless explicitly provided in another calculation. Do not annualise partial-period values without justification.')
    heading('8. Notes and review items')
    para(getattr(app,'project_notes','') or 'No project notes supplied.')
    para('Before construction: verify as-built dimensions, structural capacity, wind/snow loads, roof fixings, fire access, cold-weather string voltage, MPPT current, cable ampacity, protection coordination, earthing, manufacturer installation requirements and grid acceptance. The application does not supply those approvals.')
    heading('Cable inventory and mass')
    if hasattr(app,'_cable_mass_summary'):
        mass=app._cable_mass_summary();table(['Item','Value'],[['Declared total cable mass (kg)',mass['total_kg']],['Known subtotal (kg)',mass['known_kg']],['Incomplete cable records',mass['missing']]])
    table(['Additional cable','Length (m)','kg/m','Quantity'],[[c.get('name'),c.get('length_m'),c.get('linear_mass_kg_m'),c.get('quantity',1)] for c in data.get('cable_inventory',[])])
    para('Declared scope: DC string routes plus additional inventory. Manufacturer linear masses, corrected ampacity and protection ratings are entered inputs. Unlisted cables are not included.')
    para('Project model settings: '+scalar(data.get('model_settings',{})))
    heading('9. Calculation formulas')
    from home_reference import FORMULAS
    from matplotlib.mathtext import math_to_image
    from matplotlib.font_manager import FontProperties
    for group_index,(title,intro,formulas) in enumerate(FORMULAS):
        para(title+': '+intro)
        for formula_index,(formula,explanation) in enumerate(formulas):
            name=f'formula_{group_index}_{formula_index}.png'
            math_to_image('$'+formula+'$',str(assets/name),dpi=180,format='png',color='black',prop=FontProperties(family='STIXGeneral',math_fontfamily='stix'))
            blocks.append(('formula',assets/name,explanation,formula))
    heading('10. Complete input record')
    para('The accompanying project_inputs.json contains the full exported calculation inputs, per-panel geometry references, string order, MPPT assignments, material entries, stored simulation state and source profiles. Figure files and this report share the same export folder. Missing fields are explicitly marked; no manufacturer data are supplied by the report generator.')
    data['report_calculated_cable_routes']=dict(routes)
    (assets/'project_inputs.json').write_text(json.dumps(serial(data),ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    heading('11. Vector plans and physical-block details')
    from report_plans import vector_blocks
    blocks.extend(vector_blocks(app,assets,routes,font))
    return blocks


def report_title(app):
    """Prefer the project's display name over its save/export filename."""
    name = str(getattr(app, 'project_name', '') or '').strip()
    if not name:
        source = getattr(app, 'current_project_filepath', None)
        name = re.split(r'[\\/]', str(source))[-1] if source else 'Untitled project'
    return re.sub(r'\.json$', '', name, flags=re.I).replace('_', ' ').strip() or 'Untitled project'


def _ordered_blocks(blocks):
    """Keep the complete calculation record, while bringing drawings forward."""
    sections=[];current=[]
    for block in blocks:
        if block[0]=='heading':
            if current:sections.append(current)
            current=[]
        current.append(block)
    if current:sections.append(current)
    drawings=[b for b in blocks if b[0]=='vector'];roof=[b for b in blocks if b[0]=='image' and b[1].name=='roof_source.png']
    sheets=[b for b in blocks if b[0]=='sheet'];output=[]
    for group in sections:
        heading=group[0][1]
        if heading.startswith('11.'):continue
        if heading.startswith('4.'):
            cable=[b for b in drawings if b[3].stem=='cables_overview']
            output += [('heading','DC cable routing plan')]+cable
        output.extend(b for b in group if b[0] not in ('vector','sheet') and b not in roof)
        if heading.startswith('1.'):
            if roof:output += [('heading','Source roof plan')]+roof
            for name,label in [('layout_overview','Installation layout'),('strings_overview','String connections')]:
                output += [('heading',label)]+[b for b in drawings if b[3].stem==name]
    if sheets:output += [('heading','Complete spreadsheet')]+sheets
    for b in drawings:
        if b[3].stem.startswith('detail_'):output += [('heading','Physical block '+b[3].stem[7:].replace('_',' ')) ,b]
    return output


def export_report(app,path,progress=None):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, CondPageBreak, Flowable
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    path=Path(path);assets=path.with_name(path.stem+'_assets')
    font='Times-Roman';bold='Times-Bold'
    fontdir=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    normal=fontdir/'times.ttf';heavy=fontdir/'timesbd.ttf'
    if normal.exists() and heavy.exists():
        pdfmetrics.registerFont(TTFont('TimesNewRoman',str(normal)));pdfmetrics.registerFont(TTFont('TimesNewRomanBold',str(heavy)))
        font='TimesNewRoman';bold='TimesNewRomanBold'
    else:
        afmdir=Path('/usr/share/fonts/type1/urw-base35');pfbdir=Path('/usr/share/fonts/X11/Type1')
        if all((afmdir/(name+'.afm')).exists() and (pfbdir/(name+'.pfb')).exists() for name in ('NimbusRoman-Regular','NimbusRoman-Bold')):
            for name in ('NimbusRoman-Regular','NimbusRoman-Bold'):
                face=pdfmetrics.EmbeddedType1Face(str(afmdir/(name+'.afm')),str(pfbdir/(name+'.pfb')))
                pdfmetrics.registerTypeFace(face);pdfmetrics.registerFont(pdfmetrics.Font(name,face.name,'WinAnsiEncoding'))
            font='NimbusRoman-Regular';bold='NimbusRoman-Bold'
    pdfmetrics.registerFontFamily(font,normal=font,bold=bold,italic=font,boldItalic=bold)
    blocks=_ordered_blocks(report_content(app,assets,font,progress));project=report_title(app)
    page_size=landscape(A4);width=page_size[0]-100;available=page_size[1]-122
    body=ParagraphStyle('body',fontName=font,fontSize=10,leading=13,spaceAfter=9,textColor=colors.black)
    heading=ParagraphStyle('heading',parent=body,fontName=bold,fontSize=21,leading=25,spaceAfter=12,keepWithNext=True)
    cell=ParagraphStyle('cell',parent=body,fontSize=8,leading=10,wordWrap='CJK')
    def par(text,style=body):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    class Cover(Flowable):
        def __init__(self):super().__init__();self.width=width;self.height=available-5
        def draw(self):
            c=self.canv;c.setFillColor(colors.black)
            c.setFont(font,10);c.drawString(20,405,'ENGINEERING REPORT')
            size=min(32,32*(width-40)/max(pdfmetrics.stringWidth(project,bold,32),1));c.setFont(bold,size);c.drawString(20,350,project)
            c.setFont(font,14);c.drawString(20,323,'Photovoltaic installation and energy storage study')
            c.setLineWidth(.5);c.line(20,300,width-20,300)
            power=getattr(app,'panel_pmax_w',None);dc_w=__import__('engineering_inputs').installed_power_w(app._project_snapshot());dc=dc_w/1000 if dc_w is not None else None
            metrics=[(str(len(app.panels)),'Modules'),(scalar(dc)+' kWp' if dc is not None else MISSING,'Installed DC power'),(str(sum(bool(v) for v in app.strings.values())),'Strings'),(str(len(app.roof_zones)),'Installation zones')]
            for i,(value,label) in enumerate(metrics):
                x=20+i*(width-40)/4;c.setFont(bold,22);c.drawString(x,241,value);c.setFont(font,11);c.drawString(x,218,label)
            info=[('Module rating',scalar(power)+' W' if power is not None else MISSING),('Module tilt',scalar(getattr(app,'panel_tilt_deg',None))+' deg'),('Site coordinates',scalar(getattr(app,'solar_latitude',None))+' N / '+scalar(getattr(app,'solar_longitude',None))+' E'),('Annual shading study',str(app.model_settings.get('report_shadow_year',datetime.now().year)))]
            for i,(label,value) in enumerate(info):
                x=20+(i%2)*(width-40)/2;y=159-(i//2)*35;c.setFont(font,10);c.drawString(x,y,label);c.setFont(bold,11);c.drawString(x+110,y,value)
            c.setFont(font,9);c.drawString(20,55,'Engineering study. Calculation status and missing inputs are identified in the report.')
            c.line(20,30,width-20,30);c.drawString(20,12,datetime.now(timezone.utc).strftime('%d %B %Y'))
    class ReportDoc(SimpleDocTemplate):
        def afterFlowable(self,flowable):
            if isinstance(flowable,Paragraph) and flowable.style.name=='heading':
                self.notify('TOCEntry',(0,flowable.getPlainText(),self.page))
    story=[Cover(),PageBreak(),par('Report navigation',ParagraphStyle('navigation',parent=heading))]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc',parent=body,fontSize=9,leading=11,leftIndent=0,firstLineIndent=0,spaceBefore=2,spaceAfter=0)]
    toc.tableStyle=TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)])
    story += [toc,PageBreak()]
    previous=None
    for block in blocks:
        kind=block[0]
        if kind=='heading':
            if previous is not None:
                while story and isinstance(story[-1],Spacer):story.pop()
                story.append(CondPageBreak(available-1))
            story.append(par(block[1],heading))
        elif kind=='text':story.append(par(block[1]))
        elif kind in ('image','formula'):
            from PIL import Image as PILImage
            with PILImage.open(block[1]) as im:w,h=im.size
            if kind=='image' and previous!='heading':story.append(CondPageBreak(available-1))
            factor=min(width/w,(350 if kind=='image' else 95)/h,72/180 if kind=='formula' else 10)
            story.append(KeepTogether([Image(str(block[1]),width=w*factor,height=h*factor),Spacer(1,8),par(block[2])]))
        elif kind=='vector':
            if previous!='heading':story.append(CondPageBreak(available-1))
            story += [block[1],Spacer(1,8),par(block[2])]
        elif kind in ('table','sheet'):
            headers,rows=block[1:]
            if not rows:previous=kind;continue
            def make_table(size,col_widths):
                cs=ParagraphStyle('table_cell',parent=cell,fontSize=size,leading=size+2)
                data=[[par(h,ParagraphStyle('table_header',parent=cs,fontName=bold)) for h in headers]]+[[par('' if kind=='sheet' and v=='' else scalar(v),cs) for v in row] for row in rows]
                tab=Table(data,colWidths=col_widths,repeatRows=1,hAlign='LEFT',splitInRow=1)
                pad=3 if kind=='sheet' else 5
                tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,0),.6,colors.black),('LINEBELOW',(0,0),(-1,0),.6,colors.black),('LINEBELOW',(0,-1),(-1,-1),.4,colors.black),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),('LEFTPADDING',(0,0),(-1,-1),3 if kind=='sheet' else 8),('RIGHTPADDING',(0,0),(-1,-1),3 if kind=='sheet' else 8)]))
                return tab
            if kind=='sheet':
                weights=[28]+[max(35,min(160,max(pdfmetrics.stringWidth(str(row[c]).split('\n')[0],font,7) for row in rows)+12)) for c in range(1,len(headers))]
                widths=[width*w/sum(weights) for w in weights];size=8
                tab=make_table(size,widths)
                while tab.wrap(width,available)[1]>available-50 and size>6:
                    size-=.5;tab=make_table(size,widths)
                # One physical page, even for unusually large user sheets.
                tw,th=tab.wrap(width,available);factor=min(1,(available-50)/max(th,1))
                class FullSheet(Flowable):
                    def __init__(self,table,scale,height):super().__init__();self.table=table;self.factor=scale;self.width=width;self.height=height*scale
                    def draw(self):self.canv.saveState();self.canv.scale(self.factor,self.factor);self.table.drawOn(self.canv,0,0);self.canv.restoreState()
                story.append(FullSheet(tab,factor,th))
            else:
                if headers==['Electrical / project check','Affected records','Count']:widths=[width*.56,width*.39,width*.05]
                elif len(headers)==4 and headers[1]=='Modules in electrical order':widths=[90,width-280,100,90]
                elif len(headers)==10 and headers[0]=='String':widths=[75,48,48,55,52,55,60,48,55,width-496]
                else:widths=[width/len(headers)]*len(headers)
                story.append(make_table(8,widths))
            story.append(Spacer(1,10))
        previous=kind
    def footer(c,doc):
        c.setFillColor(colors.black);c.setStrokeColor(colors.black);c.setLineWidth(.4)
        if doc.page>1:c.line(50,page_size[1]-32,page_size[0]-50,page_size[1]-32)
        c.line(50,40,page_size[0]-50,40);c.setFont(font,8)
        c.drawString(50,25,'PV APP | '+project[:85]);c.drawRightString(page_size[0]-50,25,str(doc.page))
    doc=ReportDoc(str(path),pagesize=page_size,rightMargin=50,leftMargin=50,topMargin=48,bottomMargin=62,title=project,author='')
    doc.multiBuild(story,onFirstPage=footer,onLaterPages=footer)


# ---------------------------------------------------------------------------
# Prototype-style PDF renderer
# ---------------------------------------------------------------------------
# This renderer deliberately keeps the engineering calculations/data sources
# above, but changes the PDF orchestration to a drawing-first, fixed-page
# review document matching PV_Engineering_Report_Prototype_v4.pdf.


def _prototype_project_filename(app):
    source=getattr(app,'current_project_filepath',None)
    if source:
        name=re.split(r'[\\/]',str(source))[-1]
        return name
    name=str(getattr(app,'project_name','Untitled project') or 'Untitled project')
    return name if name.lower().endswith('.json') else name.replace(' ','_')+'.json'


def _prototype_tag(app):
    stem=report_title(app)
    parts=[p for p in re.split(r'[_\-\s]+',stem) if p]
    # Drop generic prefixes and trailing numeric job identifiers.
    useful=[p for p in parts if p.lower() not in ('usine','project','projet') and not p.isdigit()]
    return (useful[0] if useful else stem)[:24].upper()


def _prototype_material_value(app, category, row_index, key, value):
    if isinstance(value,str) and value.strip().startswith('='):
        try:
            from mixins.material_tools import MATERIAL_CATEGORY_DEFS
            columns=MATERIAL_CATEGORY_DEFS.get(category,('',[]))[1]
            evaluated=app._compute_material_formulas()
            return evaluated.get((category,row_index,columns.index(key)),'#ERR') if key in columns else '#ERR'
        except Exception:
            return '#ERR'
    return value


def _report_energy_chart_pages(app, assets, summaries):
    """Export the same comparison, monthly and daily figures as the Energy UI."""
    from energy_charts import comparison_figure
    from bess_charts import CASES, monthly_data, daily_data, energy_figure
    from battery_dispatch import BatterySettings, simulate_three_options
    from self_consumption import timestamps

    pages = []
    def save(fig, name, title, subtitle, caption):
        # Landscape report: keep all three axes and legends legible on one page.
        fig.set_size_inches(12, 6.2)
        target = assets / name
        fig.savefig(target, dpi=200)
        fig.clear()
        pages.append({'section':'08 / ENERGY AND BESS', 'title':title,
                      'subtitle':subtitle, 'status':'CALCULATED STUDY',
                      'items':[('image',target,'',380),('caption',caption)]})

    profile = getattr(app, 'hourly_consumption_profile', {}) or {}
    period = f"{profile.get('start_date', '?')} to {profile.get('end_date', '?')}"
    save(comparison_figure(summaries), 'energy_comparison.png', 'Energy supply and PV allocation',
         'PV only / one BESS / two BESS | imported period: ' + period,
         'Same comparison as the Energy tab. Totals cover the imported period, which may be shorter than a year.')
    if all(summary.get('monthly') for summary in summaries):
        months = sorted(summaries[0]['monthly'])
        imports = [[summary['monthly'][month]['grid_kwh'] for month in months] for summary in summaries]
        for case, label in enumerate(CASES):
            labels, data = monthly_data(summaries, case)
            # Keep the established one-BESS asset filename for existing tooling.
            name = 'energy_monthly.png' if case == 1 else f'energy_monthly_{case}_bess.png'
            save(energy_figure(data, labels, 'Monthly balances | ' + label, True, imports),
                 name, 'Monthly energy balance | ' + label, 'Imported period: ' + period,
                 'Load supply, PV allocation and grid purchases use the same axes, units and colours as the BESS monthly view.')

    pv = getattr(app, 'hourly_pv_kwh', []) or []
    settings = summaries[1].get('battery_settings') or summaries[1].get('settings')
    if profile and pv and settings:
        cfg = BatterySettings(**settings)
        export_limit = (getattr(app, 'grid_connection_settings', {}) or {}).get('export_limit_kw')
        comparison = getattr(app,'_energy_hourly_comparison',None) or simulate_three_options(profile,pv,cfg,export_limit)
        stamps = timestamps(profile)
        # A PDF has no day picker. Reproduce the UI's default: the first imported
        # local day, for all cases. Preserve 23/25-hour days and their UTC offsets.
        day = stamps[0].date()
        indices = [index for index, stamp in enumerate(stamps) if stamp.date() == day]
        labels = [stamps[index].strftime('%H:%M %z') for index in indices]
        for case, label in enumerate(CASES):
            rows = comparison['two_bess' if case == 2 else 'one_bess']['rows']
            start = indices[0]
            initial = rows[start-1][9] if start else cfg.initial_soc_pct
            data = daily_data([rows[index] for index in indices], case, export_limit, initial)
            fig = energy_figure(data, labels, f'{day.isoformat()} | {label}')
            if case:
                # The last hour and End ticks can be one interval apart on a
                # 25-hour day. Leave room for the final SOC label on the PDF.
                axis = fig.axes[2]
                ticks = list(axis.get_xticks())
                names = [tick.get_text() for tick in axis.get_xticklabels()]
                if len(ticks) > 1 and ticks[-1] - ticks[-2] < 2:
                    axis.set_xticks(ticks[:-2] + ticks[-1:], names[:-2] + names[-1:])
            save(fig,
                 f'energy_daily_{case}_bess.png', 'Hourly energy balance | ' + label,
                 f'First imported local day: {day.isoformat()} | {len(indices)} hourly intervals',
                 'Same daily view as the BESS tab. Battery charge/discharge are separate; SOC has its own percentage axis. This day does not represent the full imported period.')
    return pages


def _prototype_pages(app, assets, font='Times-Roman', progress=None):
    """Return semantic pages for the compact engineer-facing report."""
    from project_validation import natural
    from report_studies import shadow_blocks, spreadsheet_blocks
    from report_plans import vector_blocks

    app._prepare_project_save()
    try:
        from report_studies import refresh_report_energy
        refresh_report_energy(app,progress)
    except Exception as exc:
        app._report_energy_error=str(exc)

    data=app._project_snapshot()
    try:data.update(app._prepare_project_save())
    except Exception:pass
    if hasattr(app,'_collect_project_data'):
        try:data.update(app._collect_project_data())
        except Exception:pass

    from engineering_inputs import installed_power_w,panel_ratings,evaluated_material
    data['material_categories']=evaluated_material(data)
    rated=panel_ratings(data,strict=False)
    dc_w=installed_power_w(data)
    from project_store import serial
    snapshot=app._collect_project_data() if hasattr(app,'_collect_project_data') else data
    (assets/'project_inputs.json').write_text(json.dumps(serial(snapshot),ensure_ascii=False,indent=2),encoding='utf-8')
    pages=[]
    def page(section,title,subtitle='',items=None,status='PROJECT DATA'):
        pages.append({'section':section,'title':title,'subtitle':subtitle,'items':items or [],'status':status})

    # Calculated cable routes are also needed by the vector cable drawing.
    routes=[];route_failures={}
    for sid,coords in sorted(app.strings.items(),key=lambda item:natural(item[0])):
        if not coords:continue
        app._last_route_error=None
        try:
            rec=app._calculate_two_pole_route(sid)
            if not rec:route_failures[sid]=getattr(app,'_last_route_error',None) or 'Route/elevation inputs incomplete'
        except Exception as exc:rec=None;route_failures[sid]=str(exc)
        if rec:routes.append((sid,rec))

    # Generate vector/source assets once.
    vectors=vector_blocks(app,assets,routes,font)
    by_stem={b[3].stem:b for b in vectors if b[0]=='vector'}
    roof=next((b for b in vectors if b[0]=='image' and Path(b[1]).name=='roof_source.png'),None)

    # 01 / OVERVIEW - page 2 is inserted after all pages are known.
    page('01 / OVERVIEW','Report contents','Engineering report - drawings, schedules and calculation results',[],status='PROJECT DATA')

    power=getattr(app,'panel_pmax_w',None)
    module_rows=data.get('material_categories',{}).get('modules',{}).get('rows',[])
    inverter_rows=data.get('material_categories',{}).get('inverters',{}).get('rows',[])
    module0=module_rows[0] if module_rows else {}
    def first_number(rows,*keys):
        for row in rows:
            for key in keys:
                val=row.get(key)
                if val not in (None,''):
                    try:return float(str(val).replace(',','.'))
                    except Exception:continue
        return None
    ac_kw=first_number(inverter_rows,'Puissance active (kW)','Active power (kW)')
    if ac_kw is None:
        kva=first_number(inverter_rows,'Puissance (kVA)','Power (kVA)')
        pf=first_number(inverter_rows,'Cos phi','Power factor')
        if kva is not None and pf is not None:ac_kw=kva*pf
    cable_mass=data.get('cable_mass_by_section',{}) or {}
    linear_mass=next((v for v in cable_mass.values() if v not in (None,'')),None)
    year=int((getattr(app,'model_settings',{}) or {}).get('report_shadow_year',datetime.now().year))
    timezone=(getattr(app,'model_settings',{}) or {}).get('timezone','Europe/Rome')
    mod_w=getattr(app,'panel_width_mm',None);mod_h=getattr(app,'panel_height_mm',None)
    if mod_w is None:mod_w=data.get('panel_width_mm')
    if mod_h is None:mod_h=data.get('panel_height_mm')
    summary_rows=[
        ['Modules',len(app.panels),'Recorded'],
        ['Installed DC power',f'{dc_w/1000:.3f} kWp' if dc_w is not None else MISSING,'Recorded' if dc_w is not None else 'Module equipment incomplete'],
        ['Module rating',('Mixed equipment — see schedules' if len(module_rows)>1 else f'{float(power):.1f} W' if power is not None else MISSING),'Recorded' if power is not None else 'Not supplied'],
        ['Module dimensions',f'{float(mod_w):.1f} x {float(mod_h):.1f} mm' if mod_w is not None and mod_h is not None else MISSING,'Recorded' if mod_w is not None and mod_h is not None else 'Not supplied'],
        ['Inclination / azimuth',f'{float(getattr(app,"panel_tilt_deg",0)):.1f} / {float(getattr(app,"panel_azimuth_deg",0)):.1f} deg','Recorded'],
        ['Location',f'{float(getattr(app,"solar_latitude",0)):.2f} N / {float(getattr(app,"solar_longitude",0)):.2f} E','Recorded'],
        ['AC active inverter power',f'{ac_kw:.1f} kW' if ac_kw is not None else MISSING,'Recorded' if ac_kw is not None else 'Energy/BESS calculation blocked'],
        ['Cable linear mass',scalar(linear_mass),'Recorded' if linear_mass is not None else 'Cable mass unavailable'],
        ['Report shading study',f'{year} / {timezone}','Reused calculated study'],
    ]
    page('01 / OVERVIEW','Project summary and data status','Recorded inputs and calculation availability',[
        ('table',['Parameter','Recorded value','Status'],summary_rows,[.30,.38,.32])
    ])

    # 02 / DRAWINGS
    if roof:
        page('02 / DRAWINGS','Source roof plan','',[
            ('image',roof[1],roof[2],420)
        ])
    if 'layout_overview' in by_stem:
        b=by_stem['layout_overview']
        page('02 / DRAWINGS','Installation layout','Modules and installation areas',[
            ('vector',b[1]),('caption','Zone dimensions in metres.')
        ])
    if 'strings_overview' in by_stem:
        b=by_stem['strings_overview']
        page('02 / DRAWINGS','String connections','Electrical connection order by string',[
            ('vector',b[1]),('caption','S1 = String 1, etc. Zone dimensions in metres.')
        ])

    from report_mounting import mounting_pages
    pages.extend(mounting_pages(app,assets,font))

    # 03 / STRINGS - schedule chunks then electrical order chunks.
    strings=[(sid,coords) for sid,coords in sorted(app.strings.items(),key=lambda item:natural(item[0])) if coords]
    palette=('Cyan','Magenta')
    schedule=[]
    for i,(sid,coords) in enumerate(strings):
        ass=app.string_mppt_assignment.get(sid,{})
        values=[rated.get(c) for c in data['strings'].get(sid,[])]
        kwp=sum(values)/1000 if values and all(v is not None for v in values) else None
        schedule.append([sid,len(coords),f'{kwp:.2f}' if kwp is not None else MISSING,ass.get('block') or MISSING,ass.get('mppt') if ass.get('mppt') is not None else MISSING,palette[i%2]])
    for start in range(0,len(schedule),16):
        chunk=schedule[start:start+16];lo=start+1;hi=start+len(chunk)
        page('03 / STRINGS',f'String schedule | {lo}-{hi}','Every string, assigned inverter and MPPT',[
            ('table',['String','Modules','DC kWp','Inverter','MPPT','Drawing colour'],chunk,[.22,.13,.14,.17,.12,.22])
        ])
    order=[]
    for sid,coords in strings:
        ids=[]
        for p in coords:
            try:ids.append(str(app.panels.get(tuple(p),'MISSING')))
            except Exception:ids.append('MISSING')
        order.append([sid,', '.join(ids)])
    for start in range(0,len(order),12):
        chunk=order[start:start+12];lo=start+1;hi=start+len(chunk)
        page('03 / STRINGS',f'Module connection order | {lo}-{hi}','IDs follow the electrical connection order within each string',[
            ('table',['String','Module identifiers, in connection order'],chunk,[.20,.80])
        ])

    # 04 / GEOMETRY
    zone_rows=[]
    for i,z in enumerate(app.roof_zones,1):
        w=abs(z['x2']-z['x1'])/app.px_per_mm/1000 if app.px_per_mm else None
        d=abs(z['y2']-z['y1'])/app.px_per_mm/1000 if app.px_per_mm else None
        base=z.get('row_base',100*(i-1));rows=z.get('rows',0)
        count=sum(1 for c in app.panels if base<=c[0]<base+rows)
        zone_rows.append([i,f'{w:.2f}' if w is not None else MISSING,f'{d:.2f}' if d is not None else MISSING,f'{w*d:.1f}' if w is not None and d is not None else MISSING,count,f'{float(z.get("angle_deg",0)):.1f}',f'{float(z.get("installation_height_m",0)):.1f}' if z.get('installation_height_m') is not None else MISSING])
    page('04 / GEOMETRY','Installation-zone dimensions','Scaled plan dimensions; mounting exclusions remain project inputs',[
        ('table',['Zone','Width m','Depth m','Area m2','Modules','Layout rotation deg','Cable level m'],zone_rows,[.08,.13,.13,.13,.12,.23,.18]),
        ('note',f'Layout rotation is the in-plane angular rotation of the module placement grid within the installation zone. It is not the module tilt relative to horizontal. The entered module tilt is {scalar(getattr(app,"panel_tilt_deg",None))} degrees and is recorded separately in the technical-input schedule. Roof elevation for shading and cable installation elevation are also separate inputs.')
    ])

    # 05 / TECHNICAL INPUTS - concise site assumptions.
    site_rows=[
        ['Latitude',getattr(app,'solar_latitude',None),'deg N'],['Longitude',getattr(app,'solar_longitude',None),'deg E'],
        ['Image scale',getattr(app,'px_per_mm',None),'px/mm'],['Module tilt',getattr(app,'panel_tilt_deg',None),'deg'],
        ['Module azimuth',getattr(app,'panel_azimuth_deg',None),'deg'],['North correction',getattr(app,'north_offset_deg',None),'deg'],
        ['NOCT',getattr(app,'panel_noct_c',None),'deg C'],['Temperature coefficient',getattr(app,'panel_temp_coeff_pct',None),'%/deg C'],
        ['Obstacle height',getattr(app,'pylon_height_mm',None),'mm'],['Obstacle width',getattr(app,'pylon_width_mm',None),'mm'],
        ['Obstacle opacity',getattr(app,'pylon_opacity',None),'fraction'],
    ]
    site_rows=[[a,(f'{float(v):,.3f}' if isinstance(v,(int,float)) else scalar(v)),u] for a,v,u in site_rows]
    page('05 / TECHNICAL INPUTS','Site, solar and calculation assumptions','Entered values, displayed with human-readable units',[
        ('table',['Technical input','Value','Unit'],site_rows,[.50,.25,.25])
    ])

    # One concise page per populated material category (prototype: modules, inverters, custom).
    from mixins.material_tools import MATERIAL_COLUMNS_EN
    for category,content in (getattr(app,'material_categories',{}) or {}).items():
        rows=content.get('rows',[]) if isinstance(content,dict) else []
        if not rows:continue
        display=[]
        for ri,row in enumerate(rows):
            for key,value in row.items():
                if value in (None,''):continue
                display.append([ri+1,MATERIAL_COLUMNS_EN.get(key,key),_prototype_material_value(app,category,ri,key,value)])
        if not display:continue
        title=str(category).replace('_',' ').title()+' equipment schedule'
        page('05 / TECHNICAL INPUTS',title,'Manufacturer and electrical records; evaluated results replace formulas | rows 1-'+str(len(display)),[
            ('table',['Equipment row','Parameter','Value'],display,[.22,.45,.33])
        ])

    # 06 / ANNUAL SHADING
    try:
        _shadow_blocks,annual=shadow_blocks(app,assets,progress)
    except Exception as exc:
        annual={'year':year,'missing':[str(exc)]}
    if annual and 'missing' not in annual:
        rows=annual['rows'];months=annual['months'];pot=sum(r['potential_wh'] for r in rows);lost=sum(r['lost_wh'] for r in rows)
        page('06 / ANNUAL SHADING','Annual shading influence',f'{annual["year"]} | {annual.get("hours",0):,} elapsed hours | clear-sky geometric model',[
            ('metrics',[('Unshaded potential',f'{pot/1000:,.1f} kWh'),('With shading',f'{(pot-lost)/1000:,.1f} kWh'),('Shading loss',f'{lost/1000:,.1f} kWh'),('Annual loss',f'{100*lost/pot if pot else 0:.3f} %')]),
            ('subhead','Method'),('note','Integrate the current geometry, site orientation, thermal settings and obstacle model over the full calendar year. Shading loss is weighted by unshaded energy. This clear-sky study is distinct from the weather-driven energy/BESS calculation.'),
            ('image',assets/'annual_shadow_calendar.png','Daily/hourly shading-loss heatmap. Blank cells have no unshaded generation.',190)
        ],status='CALCULATED STUDY')
        page('06 / ANNUAL SHADING','Spatial shading heatmap','Energy-weighted loss for each module',[
            ('image',assets/'annual_shadow_roof.png','Warm colours indicate higher annual loss. See the colour bar for the numerical scale.',390)
        ],status='CALCULATED STUDY')
        month_rows=[[m,f'{r["potential_wh"]/1000:,.1f}',f'{r["produced_wh"]/1000:,.1f}',f'{r["lost_wh"]/1000:,.1f}',f'{100*r["lost_wh"]/r["potential_wh"] if r["potential_wh"] else 0:.3f}'] for m,r in months.items()]
        page('06 / ANNUAL SHADING','Monthly shading balance','A complete year, consistent with the heatmaps',[
            ('table',['Month','Unshaded kWh','Produced kWh','Lost kWh','Loss %'],month_rows,[.18,.23,.23,.20,.16])
        ],status='CALCULATED STUDY')
    else:
        page('06 / ANNUAL SHADING','Annual shading influence','Study unavailable',[
            ('note','Annual shadow study unavailable: '+', '.join(annual.get('missing',[]))+'.')
        ],status='PROJECT DATA')

    # Cable overview drawing is intentionally placed after shading, as in prototype.
    if 'cables_overview' in by_stem:
        b=by_stem['cables_overview']
        page('02 / DRAWINGS','DC cable routing plan','Conductor routes and gathering locations',[
            ('vector',b[1]),('caption','Routes are shown only where the required elevation inputs are available.')
        ])

    # 07 / CABLING
    cable_rows=[]
    for sid,r in routes:
        cable_rows.append([sid,f'{r["terminal_A"]["length_m"]:.1f}',f'{r["terminal_B"]["length_m"]:.1f}',f'{r["loop_length_m"]:.1f}',scalar(r.get('working_section_mm2')),(f'{r["drop_at_working_section_pct"]:.2f}' if r.get('drop_at_working_section_pct') is not None else MISSING),scalar(r.get('mass_kg')),r.get('ampacity_status') or 'Not checked'])
    for sid,reason in route_failures.items():cable_rows.append([sid,MISSING,MISSING,MISSING,MISSING,MISSING,MISSING,'Unavailable: '+reason])
    cable_rows.sort(key=lambda row:natural(row[0]))
    for start in range(0,len(cable_rows),14):
        chunk=cable_rows[start:start+14];lo=start+1;hi=start+len(chunk)
        page('07 / CABLING',f'Per-string cable sizing | {lo}-{hi}','One row per string, both conductor lengths and selected working section',[
            ('table',['String','A m','B m','Loop m','mm2','Drop %','Mass kg','Check status'],chunk,[.12,.09,.09,.10,.08,.10,.12,.30]),
            ('note','A and B are the two string-to-inverter conductors. Cross-section proposals must be checked against admissible current, installation conditions and protection coordination. Missing mass data remains explicit.')
        ])

    # 08 / ENERGY AND BESS - only project calculations are reported.
    current=False
    try:current=bool(app._energy_results_current())
    except Exception:pass
    summaries=[getattr(app,'self_consumption_summary',{}) or {},getattr(app,'bess_summary',{}) or {},getattr(app,'two_bess_summary',{}) or {}]
    if current and all(s.get('annual') for s in summaries):
        labels=['PV only','One BESS','Two BESS'];energy_rows=[]
        for case,(label,s) in enumerate(zip(labels,summaries)):
            a=s['annual']
            values=[a.get('pv_kwh'),a.get('self_kwh' if case==0 else 'useful_self_kwh'),
                    a.get('grid_kwh'),0. if case==0 else a.get('charge_ac_kwh'),
                    0. if case==0 else a.get('battery_losses_kwh'),a.get('export_kwh'),a.get('curtailed_kwh')]
            energy_rows.append([label]+[f'{v/1000:,.3f}' if v is not None else MISSING for v in values])
        page('08 / ENERGY AND BESS','Energy and BESS comparison','Energy results current | '+__import__('self_consumption').weather_method(getattr(app,'hourly_weather_profile',None)),[
            ('table',['Scenario','PV MWh','Self-use MWh','Grid MWh','To battery MWh','BESS loss MWh','Export MWh','Curtailment MWh'],energy_rows,[.16,.12,.13,.11,.13,.11,.12,.12])
        ],status='CALCULATED STUDY')

        months=sorted(set().union(*(s.get('monthly',{}).keys() for s in summaries)))
        rows=[]
        for m in months:
            r=summaries[1].get('monthly',{}).get(m,{})
            rows.append([m,f'{float(r.get("pv_kwh",0))/1000:.1f}',f'{float(r.get("load_kwh",0))/1000:.1f}',f'{float(r.get("export_kwh",0))/1000:.1f}'])
        page('08 / ENERGY AND BESS','Monthly energy table','Current one-BESS result',[
            ('table',['Month','PV MWh','Load MWh','Export MWh'],rows,[.28,.24,.24,.24])
        ],status='CALCULATED STUDY')
        pages.extend(_report_energy_chart_pages(app,assets,summaries))
    else:
        missing=[]
        if ac_kw is None:missing.append('active inverter rating')
        if not getattr(app,'hourly_consumption_profile',None):missing.append('hourly consumption profile')

        reason=getattr(app,'_report_energy_error',None) or (', '.join(missing) if missing else 'energy results are missing or no longer current')
        page('08 / ENERGY AND BESS','Energy and BESS calculation','Calculation unavailable',[
            ('table',['Status','Required action'],[['Not calculated',f'Complete or refresh: {reason}.']],[.28,.72])
        ],status='PROJECT DATA')

    if current and all(s.get('annual') for s in summaries):
        from energy_economics import evaluate_options,covers_full_year
        settings=dict(getattr(app,'economic_settings',{}));profile=app.hourly_consumption_profile
        annual_period=covers_full_year(profile)
        if not annual_period:settings['annual_maintenance_eur']=settings.get('annual_maintenance_eur',0)*len(profile['hourly_kwh'])/8766
        economics=evaluate_options([s['annual'] for s in summaries],settings)
        page('08 / ENERGY AND BESS','Economic comparison','Benefits cover the imported period; payback requires a complete year',[
            ('table',['BESS','Export EUR/kWh','Benefit EUR','Investment EUR','Payback years','NPV EUR'],
             [[r['bess_count'],r['export_eur_kwh'],r['total_benefit_eur'],r['capex_eur'],r['simple_payback_years'] if annual_period else 'Partial year',r['net_present_value_eur'] if annual_period else 'Partial year'] for r in economics],[.08,.16,.20,.19,.18,.19]),
            ('note','Initial storage energy is excluded from the PV credit. Battery charging is not added to useful self-consumption.')
        ],status='CALCULATED STUDY')
    page('11 / REVIEW','Project notes and review items','Recorded notes and remaining engineering checks',[
        ('note',getattr(app,'project_notes','') or 'No project notes supplied.'),
        ('note','Review structural loads, fire access, string voltage, protection coordination, earthing and grid acceptance before construction.'),
        ('table',['Review item'],[[issue] for issue in audit_project(data)],[1.])
    ])
    page('11 / REVIEW','Cable inventory and mass','DC string routes plus declared additional cables',[
        ('table',['Cable','Length m','kg/m','Quantity'],[[c.get('name'),c.get('length_m'),c.get('linear_mass_kg_m'),c.get('quantity',1)] for c in data.get('cable_inventory',[])],[.46,.18,.18,.18]),
        ('note','Unlisted cables are outside the inventory. Missing lengths or manufacturer masses are unavailable, not zero.'),
        ('table',['Mass input','Value'],list(app._cable_mass_summary().items()) if hasattr(app,'_cable_mass_summary') else [['Status','Not available']],[.60,.40])
    ])
    page('11 / REVIEW','Economic inputs','Recorded assumptions',[
        ('table',['Parameter','Value'],list(getattr(app,'economic_settings',{}).items()),[.65,.35])
    ])

    # 09 / SPREADSHEET - one page, full sheet.
    sheet=getattr(app,'material_spreadsheet',{}) or {}
    if sheet:
        from mixins.spreadsheet_tools import col_letter,cell_id
        calculated=app._compute_spreadsheet_values();nrows=int(sheet.get('rows',20));ncols=int(sheet.get('cols',8));cells=sheet.get('cells',{})
        def sheet_value(r,c):
            raw=str(cells.get(cell_id(r,c),'') or '')
            if raw.strip().startswith('='):return raw+'\nValue: '+scalar(calculated.get((r,c),''))
            return raw
        rows=[[str(r+1)]+[sheet_value(r,c) for c in range(ncols)] for r in range(nrows)]
        page('09 / SPREADSHEET',f'Complete spreadsheet | A-{col_letter(ncols-1)} | rows 1-{nrows}','Entire sheet on one page; formulas and evaluated values remain visible',[
            ('sheet',['Row']+[col_letter(c) for c in range(ncols)],rows)
        ])
        try:spreadsheet_blocks(app,assets)
        except Exception:pass

    # 10 / BLOCK DETAILS - one complete physical block per page.
    details=[(stem,b) for stem,b in by_stem.items() if stem.startswith('detail_')]
    def detail_key(item):
        m=re.search(r'(\d+)',item[0]);return int(m.group(1)) if m else 9999
    for stem,b in sorted(details,key=detail_key):
        label=stem[7:].replace('_',' ')
        m=re.search(r'(\d+)',label);zone=m.group(1) if m else ''
        count=''
        if zone:
            zi=int(zone)-1
            if 0<=zi<len(app.roof_zones):
                z=app.roof_zones[zi];base=z.get('row_base',100*zi);rr=z.get('rows',0);count=sum(1 for c in app.panels if base<=c[0]<base+rr)
        subtitle=(f'Zone {zone} | {count} modules' if zone else 'Physical installation block')
        page('10 / BLOCK DETAILS','Physical block '+label,subtitle,[('vector',b[1]),('caption','Zone dimensions in metres; module IDs and string connections shown.')])

    pages=[p for p in pages if p['section']!='11 / REVIEW']+[p for p in pages if p['section']=='11 / REVIEW']
    return pages


def export_report(app,path,progress=None):
    """Export the compact engineer-facing engineering PDF.

    Compared with the legacy renderer above, this version prevents the audit
    list and raw questionnaire from expanding the report to ~70 pages. It
    keeps drawings first, chunks the string/cable schedules predictably and
    reserves one complete page for each physical block.

    Progress is reported through the supplied callback so the application can
    display it in its main Home workspace.  The report renderer itself never
    creates Tk widgets and is safe to execute in the existing worker thread.
    """
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, Flowable, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_LEFT
    from PIL import Image as PILImage

    # Progress is rendered by the application (Home workspace), not by the
    # report generator.  This keeps Tk widgets out of the worker thread and
    # prevents the ribbon/toolbar from changing height.
    def _emit(value,message):
        if progress is not None:
            progress(max(0,min(100,int(round(value)))),100)

    def _progress_proxy(*args,**kwargs):
        # Map long internal calculations (annual shading, energy refresh, etc.)
        # into the calculation phase of the report progress bar.
        nums=[float(v) for v in args if isinstance(v,(int,float)) and not isinstance(v,bool)]
        strings=[v for v in args if isinstance(v,str) and v.strip()]
        if len(nums)>=2 and nums[1]>0:
            fraction=max(0.0,min(1.0,nums[0]/nums[1]))
            _emit(8+57*fraction,strings[-1] if strings else 'Calculating report studies...')
        elif nums:
            fraction=max(0.0,min(1.0,nums[0] if 0<=nums[0]<=1 else nums[0]/100.0))
            _emit(8+57*fraction,strings[-1] if strings else 'Calculating report studies...')

    _emit(3,'Preparing report data...')
    path=Path(path);assets=path.with_name(path.stem+'_assets');assets.mkdir(parents=True,exist_ok=True)
    font='Times-Roman';bold='Times-Bold'
    fontdir=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts';normal=fontdir/'times.ttf';heavy=fontdir/'timesbd.ttf'
    if normal.exists() and heavy.exists():
        pdfmetrics.registerFont(TTFont('TimesNewRoman',str(normal)));pdfmetrics.registerFont(TTFont('TimesNewRomanBold',str(heavy)));font='TimesNewRoman';bold='TimesNewRomanBold'
    else:
        afmdir=Path('/usr/share/fonts/type1/urw-base35');pfbdir=Path('/usr/share/fonts/X11/Type1')
        if all((afmdir/(name+'.afm')).exists() and (pfbdir/(name+'.pfb')).exists() for name in ('NimbusRoman-Regular','NimbusRoman-Bold')):
            for name in ('NimbusRoman-Regular','NimbusRoman-Bold'):
                try:
                    face=pdfmetrics.EmbeddedType1Face(str(afmdir/(name+'.afm')),str(pfbdir/(name+'.pfb')));pdfmetrics.registerTypeFace(face);pdfmetrics.registerFont(pdfmetrics.Font(name,face.name,'WinAnsiEncoding'))
                except Exception:pass
            font='NimbusRoman-Regular';bold='NimbusRoman-Bold'
    try:pdfmetrics.registerFontFamily(font,normal=font,bold=bold,italic=font,boldItalic=bold)
    except Exception:pass

    _emit(8,'Calculating studies and preparing pages...')
    pages=_prototype_pages(app,assets,font,_progress_proxy)
    _emit(68,'Laying out the report...')
    page_size=landscape(A4);PW,PH=page_size;LM=50;RM=50;TM=48;BM=54;usable=PW-LM-RM
    body=ParagraphStyle('proto_body',fontName=font,fontSize=8.6,leading=11.2,textColor=colors.black,spaceAfter=6)
    small=ParagraphStyle('proto_small',parent=body,fontSize=7.3,leading=9)
    title_style=ParagraphStyle('proto_title',parent=body,fontName=bold,fontSize=18,leading=21,spaceAfter=5)
    subtitle_style=ParagraphStyle('proto_subtitle',parent=body,fontSize=8.2,leading=10,spaceAfter=8)
    section_style=ParagraphStyle('proto_section',parent=body,fontSize=7.2,leading=8,textColor=colors.HexColor('#444444'),spaceAfter=9)
    subhead=ParagraphStyle('proto_subhead',parent=body,fontName=bold,fontSize=9.5,leading=11,spaceBefore=4,spaceAfter=3)
    def P(text,style=body):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)

    filename=report_title(app);tag=_prototype_tag(app);revision='REVISION 3'
    # Determine start pages before rendering. Cover = 1; semantic pages start at 2.
    section_starts={}
    for i,p in enumerate(pages,2):section_starts.setdefault(p['section'],i)
    total=1+len(pages)
    # Fill navigation page now that page numbers are known.
    nav_rows=[]
    for sec in ['01 / OVERVIEW','02 / DRAWINGS','03 / STRINGS','04 / GEOMETRY','05 / TECHNICAL INPUTS','06 / ANNUAL SHADING','07 / CABLING','08 / ENERGY AND BESS','09 / SPREADSHEET','10 / BLOCK DETAILS','11 / REVIEW']:
        if sec in section_starts:nav_rows.append([sec,section_starts[sec]])
    pages[0]['items']=[('table',['Section','Starts on page'],nav_rows,[.88,.12])]

    class Cover(Flowable):
        def __init__(self):
            super().__init__()
            # Platypus Frame keeps 6 pt padding on each side by default.
            # A flowable sized to the raw document area (usable x page height)
            # is therefore 12 pt too wide/high and raises LayoutError.
            self.width=max(1, usable-12)
            self.height=max(1, PH-TM-BM-12)
        def draw(self):
            c=self.canv;x=0;c.setFillColor(colors.black)
            c.setFont(font,7.5);c.drawString(x,455,'ENGINEERING REPORT')
            size=min(24,24*usable/max(pdfmetrics.stringWidth(filename,bold,24),1));c.setFont(bold,size);c.drawString(x,405,filename)
            c.setFont(font,11);c.drawString(x,382,'Photovoltaic installation and energy storage study')
            c.setLineWidth(.45);c.line(x,365,usable,365)
            power=getattr(app,'panel_pmax_w',None);dc_w=__import__('engineering_inputs').installed_power_w(app._project_snapshot());dc=dc_w/1000 if dc_w is not None else None
            metrics=[(str(len(app.panels)),'Modules'),(f'{dc:.2f} kWp' if dc is not None else MISSING,'Installed DC power'),(str(sum(bool(v) for v in app.strings.values())),'Strings'),(str(len(app.roof_zones)),'Installation zones')]
            for i,(value,label) in enumerate(metrics):
                xx=x+i*usable/4;c.setFont(bold,14);c.drawString(xx,318,value);c.setFont(font,7.7);c.drawString(xx,300,label)
            info=[('Module equipment','Mixed - see schedules' if len(getattr(app,'material_categories',{}).get('modules',{}).get('rows',[]))>1 else f'{scalar(power)} W' if power is not None else MISSING),('Module tilt',f'{scalar(getattr(app,"panel_tilt_deg",None))} degrees'),('Site coordinates',f'{scalar(getattr(app,"solar_latitude",None))} N / {scalar(getattr(app,"solar_longitude",None))} E'),('Annual shading study',str((getattr(app,'model_settings',{}) or {}).get('report_shadow_year',datetime.now().year)))]
            for i,(lab,val) in enumerate(info):
                xx=x+(i%2)*usable/2;yy=242-(i//2)*30;c.setFont(font,7.5);c.drawString(xx,yy,lab);c.setFont(bold,8);c.drawString(xx+96,yy,val)

            c.line(x,72,usable,72);c.drawString(x,53,datetime.now().strftime('%-d %B %Y') if os.name!='nt' else datetime.now().strftime('%#d %B %Y'))
            c.drawRightString(usable,53,f'01 / {total:02d}')

    def make_table(headers,rows,fractions,fontsize=7.7,sheet=False):
        widths=[usable*f for f in fractions]
        cs=ParagraphStyle('proto_cell_'+str(id(rows)),parent=small,fontSize=fontsize,leading=fontsize+2.0)
        hs=ParagraphStyle('proto_head_'+str(id(rows)),parent=cs,fontName=bold)
        data=[[P(h,hs) for h in headers]]+[[P('' if v is None else scalar(v),cs) for v in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1)
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEABOVE',(0,0),(-1,0),.45,colors.black),('LINEBELOW',(0,0),(-1,0),.45,colors.black),('LINEBELOW',(0,-1),(-1,-1),.35,colors.black),
            ('TOPPADDING',(0,0),(-1,-1),3.5 if not sheet else 2.0),('BOTTOMPADDING',(0,0),(-1,-1),3.5 if not sheet else 2.0),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)
        ]));return t

    class PageAnchor(Flowable):
        def __init__(self,index):super().__init__();self.semantic_index=index;self.width=0;self.height=0
        def draw(self):pass

    def build_story():
        story=[Cover(),PageBreak()]
        for pi,p in enumerate(pages,2):
            story.append(PageAnchor(pi))
            story += [P(p['section'],section_style),P(p['title'],title_style),P(p.get('subtitle',''),subtitle_style)]
            for item in p['items']:
                kind=item[0]
                if kind=='table':story += [make_table(item[1],item[2],item[3]),Spacer(1,7)]
                elif kind=='sheet':
                    headers,rows=item[1],item[2];n=len(headers);fractions=[.055]+[(.945/(n-1))]*(n-1)
                    t=make_table(headers,rows,fractions,fontsize=6.2,sheet=True);tw,th=t.wrap(usable,PH-150);factor=min(1,(PH-175)/max(th,1))
                    class ScaledTable(Flowable):
                        def __init__(self,tab,scale,h):super().__init__();self.tab=tab;self.scale=scale;self.width=usable;self.height=h*scale
                        def draw(self):self.canv.saveState();self.canv.scale(self.scale,self.scale);self.tab.drawOn(self.canv,0,0);self.canv.restoreState()
                    story.append(ScaledTable(t,factor,th))
                elif kind=='note':story += [P(item[1],small),Spacer(1,4)]
                elif kind=='caption':story += [Spacer(1,5),P(item[1],small)]
                elif kind=='subhead':story += [P(item[1],subhead)]
                elif kind=='metrics':
                    cells=[]
                    # Metrics need ReportLab Paragraph markup (<b>, <br/>, <font>).
                    # P() escapes all input by design, so using it here would render the
                    # tags literally. Escape only the dynamic values and pass the markup
                    # directly to Paragraph instead.
                    for label,value in item[1]:
                        markup=f'<b>{escape(str(value))}</b><br/><font size="7">{escape(str(label))}</font>'
                        cells.append(Paragraph(markup,body))
                    t=Table([cells],colWidths=[usable/len(cells)]*len(cells),hAlign='LEFT');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),8)]));story += [t,Spacer(1,4)]
                elif kind=='vector':
                    d=item[1]
                    # The existing drawing is 742x350 and fits comfortably at full size.
                    story += [d,Spacer(1,4)]
                elif kind=='image':
                    src=item[1]
                    if src and Path(src).exists():
                        with PILImage.open(src) as im:w,h=im.size
                        max_h=item[3] if len(item)>3 else 350;scale=min(usable/w,max_h/h)
                        img=Image(str(src),width=w*scale,height=h*scale);story += [img,Spacer(1,5)]
                        if item[2]:story.append(P(item[2],small))
            if pi<1+len(pages):story.append(PageBreak())
        return story

    def decorate(c,doc):
        page_no=doc.page
        c.saveState();c.setStrokeColor(colors.black);c.setFillColor(colors.black);c.setLineWidth(.35)
        # Top rule only on internal pages.
        if page_no>1:c.line(LM,PH-31,PW-RM,PH-31)
        c.line(LM,39,PW-RM,39);c.setFont(font,6.8)
        if page_no==1:
            pass
        else:
            candidates=[index for index,start in page_anchors.items() if start<=page_no]
            idx=max(candidates)-2 if candidates else -1
            status=pages[idx]['status'] if 0<=idx<len(pages) else 'PROJECT DATA'
            c.drawString(LM,24,f'PV APP | {tag} | {status}')
            c.drawRightString(PW-RM,24,f'{revision} / {page_no:02d} of {total:02d}')
        c.restoreState()

    import io
    class MeasuredDocument(SimpleDocTemplate):
        def afterFlowable(self,flowable):
            if hasattr(flowable,'semantic_index'):self.anchors[flowable.semantic_index]=self.page

    _emit(78,'Generating PDF...')
    page_anchors={i:i for i in range(2,2+len(pages))}
    # Content/layout is prepared once. Only lightweight rendering is repeated.
    for attempt in range(4):
        buffer=io.BytesIO()
        doc=MeasuredDocument(buffer,pagesize=page_size,rightMargin=RM,leftMargin=LM,
            topMargin=TM,bottomMargin=BM,title=filename,author='')
        doc.anchors={}
        doc.build(build_story(),onFirstPage=decorate,onLaterPages=decorate)
        if total==doc.page and page_anchors==doc.anchors:
            path.write_bytes(buffer.getvalue());break
        total=doc.page;page_anchors=doc.anchors
        starts={}
        for index,start in sorted(page_anchors.items()):starts.setdefault(pages[index-2]['section'],start)
        pages[0]['items']=[('table',['Section','Starts on page'],[[sec,start] for sec,start in starts.items()],[.88,.12])]
    else:raise RuntimeError('Report pagination did not stabilise.')
    _emit(94,'Finalizing the PDF report...')
    _emit(100,'Report complete')
    return {'pdf':str(path),'pages':total}
