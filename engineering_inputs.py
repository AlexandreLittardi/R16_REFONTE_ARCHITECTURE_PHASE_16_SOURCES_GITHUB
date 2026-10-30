"""One source of electrical operating data for routes, schedules and energy."""
import copy
from project_validation import number

def evaluated_material(project):
    categories=project.get('material_categories',{})
    if not any(isinstance(v,str) and v.strip().startswith('=')
               for c in categories.values() for row in c.get('rows',[]) for v in row.values()):
        return categories
    from mixins.material_tools import MaterialToolsMixin, MATERIAL_CATEGORY_DEFS
    adapter=MaterialToolsMixin()
    for key in ('panels','strings','inverter_positions','cable_string_params','panel_pmax_w'):
        setattr(adapter,key,project.get(key,{} if key!='panel_pmax_w' else None))
    adapter.material_categories=categories
    computed=adapter._compute_material_formulas()
    result=copy.deepcopy(categories)
    for category,content in result.items():
        columns=MATERIAL_CATEGORY_DEFS.get(category,('',[]))[1]
        for i,row in enumerate(content.get('rows',[])):
            for j,key in enumerate(columns):
                if isinstance(row.get(key),str) and row[key].strip().startswith('='):
                    row[key]=computed.get((category,i,j),'#ERR')
    return result


def sizing_signature(project):
    return {'parameters':project.get('cable_calc_params',{}),
            'strings':project.get('cable_string_params',{}),
            'mass_by_section':project.get('cable_mass_by_section',{}),
            'module_rows':evaluated_material(project).get('modules',{}).get('rows',[])}


def panel_ratings(project, strict=True):
    project=dict(project,material_categories=evaluated_material(project))
    ratings={};rows=evaluated_material(project).get('modules',{}).get('rows',[])
    for sid,members in project.get('strings',{}).items():
        if not members:continue
        spec=module_for_string(project,sid)
        missing=project.get('cable_string_params',{}).get(sid,{}).get('_module_missing')
        value=number(spec.get('Pmax (W)',project.get('panel_pmax_w') if len(rows)<=1 and not missing else None))
        if value is None or value<=0:
            if strict:raise ValueError(f'{sid}: select a module with a valid evaluated Pmax.')
            continue
        for coord in members:ratings[coord]=value
    fallback=number(rows[0].get('Pmax (W)')) if len(rows)==1 else number(project.get('panel_pmax_w')) if not rows else None
    for coord in project.get('panels',{}):
        if coord not in ratings and coord not in {c for members in project.get('strings',{}).values() for c in members}:
            if fallback is not None and fallback>0:ratings[coord]=fallback
            elif strict:raise ValueError(f'{coord}: module equipment is not selected.')
    return ratings


def installed_power_w(project):
    ratings=panel_ratings(project,strict=False)
    return sum(ratings.values()) if set(ratings)==set(project.get('panels',{})) else None


def module_for_string(project,sid):
    rows=evaluated_material(project).get('modules',{}).get('rows',[])
    override=project.get('cable_string_params',{}).get(sid,{})
    if override.get('_module_missing'):return {}
    idx=override.get('module_row')
    if idx is not None and isinstance(idx,int) and 0<=idx<len(rows):return rows[idx]
    return rows[0] if len(rows)==1 else {}

def operating_values(project,sid):
    row=module_for_string(project,sid);override=project.get('cable_string_params',{}).get(sid,{})
    count=len(project.get('strings',{}).get(sid,[]))
    vmp=number(row.get('Vmp (V)'));imp=number(row.get('Imp (A)'))
    return {'current_a':number(override.get('current_a',imp)),
            'voltage_v':number(override.get('voltage_v',vmp*count if vmp else None)),
            'isc_a':number(override.get('isc_a',row.get('Isc (A)'))),
            'voc_v':number(row.get('Voc (V)'))}

def inverter_row(project,block):
    placement=project.get('inverter_positions',{}).get(block,{})
    link=project.get('equipment_links',{}).get(block)
    rows=evaluated_material(project).get('inverters',{}).get('rows',[])
    if isinstance(link,int) and 0<=link<len(rows):return copy.deepcopy(rows[link])
    if block in project.get('equipment_links',{}):return {}
    return placement.get('material_row',{})

def ac_limit_kw(project,block):
    row=inverter_row(project,block)
    kw=number(row.get('Puissance active (kW)'))
    if kw is not None and kw>0:return kw
    kva=number(row.get('Puissance (kVA)'))
    pf=number(row.get('Cos phi',project.get('electrical_design',{}).get('power_factor')))
    if kva is None or kva<=0 or pf is None or not 0<pf<=1:
        raise ValueError(f'{block}: enter active power (kW), or apparent power (kVA) and power factor in Equipment / Electrical design.')
    return kva*pf

def panel_connections(app):
    connected={};seen=set()
    project=app._project_snapshot()
    for sid,members in app.strings.items():
        if not members:continue
        a=app.string_mppt_assignment.get(sid,{})
        block=a.get('block');slot=a.get('mppt')
        spec=app.blocks.get(block,{})
        manufacturer=number(inverter_row(project,block).get('Nb entrées MPPT'))
        if manufacturer is not None and (manufacturer!=int(manufacturer) or manufacturer<1):raise ValueError(f'{block}: invalid manufacturer MPPT count.')
        maximum=int(manufacturer) if manufacturer is not None else int(spec.get('mppt_count',0))
        if not spec or not isinstance(slot,int) or not 1<=slot<=min(maximum,int(spec.get('mppt_count',0))):
            raise ValueError(f'{sid}: assign a valid inverter / MPPT before energy calculation.')
        for c in members:
            if c not in app.panels or c in seen:raise ValueError(f'{sid}: missing or duplicate module membership.')
            declared=app.panel_blocks.get(c)
            if declared and declared!=block:raise ValueError(f'{sid}: module block differs from its inverter assignment.')
            seen.add(c);connected[c]=block
    if seen!=set(app.panels):raise ValueError('Connect every module to exactly one string before calculating energy.')
    return connected
