"""Mounting geometry in module millimetres, independent of Tk and view zoom."""
import copy
import math


def default_site():
    """Project/installer datum and descriptive fields; never invent structural specs."""
    return dict(origin=None, origin_label='O', roof_reference='', support_reference='',
                anchor_reference='', installer_notes='', drawing_reference='MT-01', revision='A')


def validate_site(raw):
    site=default_site()
    if raw is not None:
        if not isinstance(raw,dict):raise ValueError('Invalid site references.')
        site.update({k:v for k,v in raw.items() if k in site})
    point=site['origin']
    if point is not None:
        if not isinstance(point,(list,tuple)) or len(point)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in point):
            raise ValueError('Invalid drawing origin.')
        site['origin']=[float(v) for v in point]
    for name in ('origin_label','roof_reference','support_reference','anchor_reference',
                 'installer_notes','drawing_reference','revision'):
        value=site[name]
        if not isinstance(value,str) or len(value)>2000:
            raise ValueError('Invalid site reference field: '+name)
        site[name]=value.strip()
    if not site['origin_label']:site['origin_label']='O'
    return site


def empty_plan():
    from mounting_edges import default_rules
    return {'version': 1, 'template': None, 'panels': {}, 'dimensions': [], 'hidden_dimensions': [], 'dimension_labels': {},
            'edge_rules':default_rules(), 'site':default_site()}


def default_config(width, height):
    length = max(width, height)
    return dict(width_mm=width, height_mm=height, edge='long', count=4,
                a_mm=round(length * .2, 1), b_mm=round(length * .2, 1),
                clamp_length_mm=50., clamp_width_mm=40., positions={})


def station_positions(config):
    """Return station axes in module mm measured from the mounting-axis origin.

    In six-point ABC mode the three values are *absolute* distances from the
    top edge (when along Y), not successive gaps. Legacy six-point projects
    without `top_offsets_mm` retain their original equal-spacing positions.
    """
    length, _, _ = axes(config)
    if config['count'] == 6 and config.get('top_offsets_mm') is not None:
        return list(config['top_offsets_mm'])
    n = config['count'] // 2
    return [config['a_mm'] + i * (length - config['a_mm'] - config['b_mm']) / (n-1)
            for i in range(n)]


def set_fixing_position(config, index, value):
    """Move a paired ABC station or one legacy fixing; never mutate input."""
    draft = copy.deepcopy(config)
    if not 0 <= index < draft['count']:
        raise ValueError('Invalid clamp index.')
    if draft['count'] == 6 and draft.get('top_offsets_mm') is not None:
        offsets = list(station_positions(draft))
        offsets[index // 2] = value
        draft['top_offsets_mm'] = offsets
        for side_index in (2 * (index // 2), 2 * (index // 2) + 1):
            draft.setdefault('positions', {}).pop(str(side_index), None)
    else:
        draft.setdefault('positions', {})[str(index)] = value
    return draft


def axes(config):
    w, h = config['width_mm'], config['height_mm']
    along_y = (h >= w) == (config['edge'] == 'long')
    return (h, w, along_y) if along_y else (w, h, along_y)


def validate_config(raw,footprint=True):
    if not isinstance(raw, dict):
        raise ValueError('Invalid mounting configuration.')
    c = copy.deepcopy(raw)
    for k in ('width_mm', 'height_mm', 'a_mm', 'b_mm', 'clamp_length_mm', 'clamp_width_mm'):
        try:
            c[k] = float(c[k])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f'{k} : nombre requis.') from None
        if not math.isfinite(c[k]) or c[k] < 0:
            raise ValueError(f'{k} : must be finite and positive.')
    if min(c['width_mm'], c['height_mm'], c['clamp_length_mm'], c['clamp_width_mm']) <= 0:
        raise ValueError('Dimensions must be strictly positive.')
    if c.get('edge') not in ('long', 'short'):
        raise ValueError('Choose the long or short side.')
    if type(c.get('count')) is not int or c['count'] not in (4, 6, 8, 10, 12):
        raise ValueError('Choose 4, 6, 8, 10 or 12 clamps.')
    length, cross, _ = axes(c)
    half = c['clamp_length_mm'] / 2 if footprint else 0
    abc = c.get('top_offsets_mm')
    if abc is not None and c['count'] != 6:
        raise ValueError('Top-edge A/B/C dimensions apply only to six-clamp configurations.')
    if abc is not None:
        if not isinstance(abc, (list,tuple)) or len(abc) != 3:
            raise ValueError('For six clamps, enter all three A/B/C distances.')
        try:
            abc = [float(v) for v in abc]
        except (ValueError,TypeError):
            raise ValueError('A, B and C must be numeric distances.') from None
        if any(not math.isfinite(v) for v in abc):
            raise ValueError('A, B and C must be finite.')
        if abc[0] < half or abc[-1] > length-half:
            raise ValueError('A, B and C clamp axes must stay within the module.')
        if any(b-a < (c['clamp_length_mm'] if footprint else 0)+1e-6 for a,b in zip(abc,abc[1:])):
            raise ValueError('A, B and C must be increasing with no overlaps.')
        c['top_offsets_mm'] = abc
    else:
        if c['a_mm'] < half or c['b_mm'] < half or c['a_mm'] + c['b_mm'] >= length:
            raise ValueError('A and B must keep clamps on the frame and A+B must be less than the clamped edge length.')
        spacing = (length - c['a_mm'] - c['b_mm']) / (c['count'] // 2 - 1)
        if footprint and spacing < c['clamp_length_mm']:
            raise ValueError('Clamps overlap or are too wide.')
    if footprint and c['clamp_width_mm'] >= cross:
        raise ValueError('Clamps are too wide for the module.')
    positions = c.setdefault('positions', {})
    if not isinstance(positions, dict):
        raise ValueError('Invalid clamp positions.')
    for key, value in positions.items():
        if key not in {str(i) for i in range(c['count'])}:
            raise ValueError('Invalid clamp index.')
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError('Invalid clamp position.') from None
        if not math.isfinite(value) or not half <= value <= length - half:
            raise ValueError('A clamp extends beyond the module frame.')
        positions[key] = value
    for side in range(2):
        values = [f['position_mm'] for f in fixings(c) if f['side'] == side]
        if any(b-a < (c['clamp_length_mm'] if footprint else 0) - 1e-6 for a, b in zip(values, values[1:])):
            raise ValueError('Clamps must remain ordered and must not overlap.')
    return c


def fixings(config,sizes=None):
    length, cross, along_y = axes(config)
    result = []
    for station, distance in enumerate(station_positions(config)):
        for side in range(2):
            i = len(result)
            t = config.get('positions', {}).get(str(i), distance)
            x, y = (side*cross, t) if along_y else (t, side*cross)
            spec=(sizes or {}).get(i,{})
            fixing_length=spec.get('length_mm',config['clamp_length_mm'])
            fixing_width=spec.get('width_mm',config['clamp_width_mm'])
            hl, hw = fixing_length/2,fixing_width/2
            dx, dy = (hw, hl) if along_y else (hl, hw)
            result.append(dict(spec,index=i, side=side, position_mm=t, x=x, y=y,
                               length_mm=fixing_length,width_mm=fixing_width,
                               kind=spec.get('kind','standard'),reference=spec.get('reference',''),
                               polygon=[(x-dx,y-dy),(x+dx,y-dy),(x+dx,y+dy),(x-dx,y+dy)]))
    return result


def validate_fixing_sizes(config,sizes):
    length,cross,along_y=axes(config)
    fs=fixings(config,sizes)
    for f in fs:
        if f['width_mm']>=cross or f['position_mm']<f['length_mm']/2-1e-6 or f['position_mm']>length-f['length_mm']/2+1e-6:
            raise ValueError(f"F{f['index']+1}: clamp dimensions incompatible with module frame or offset.")
    for side in (0,1):
        values=[f for f in fs if f['side']==side]
        for a,b in zip(values,values[1:]):
            if b['position_mm']-a['position_mm']<(a['length_mm']+b['length_mm'])/2-1e-6:
                raise ValueError('Clamp footprints overlap.')
    return fs


def resize_fixings(plan, uids, length_mm, width_mm):
    """Resize real footprints without changing station positions; commit atomically."""
    updated=copy.deepcopy(plan)
    targets=[uid for uid in uids if uid in updated['panels']]
    if not targets:
        raise ValueError('Select a module with configured mounting.')
    for uid in targets:
        c=updated['panels'][uid]
        c.update(clamp_length_mm=length_mm,clamp_width_mm=width_mm)
        updated['panels'][uid]=validate_config(c)
    updated['template']=copy.deepcopy(updated['panels'][targets[0]])
    return updated


def transform(poly, width, height, point):
    """Map module local axes onto the rotated layout rectangle."""
    u, v = point[0]/width, point[1]/height
    return tuple(poly[0][i] + u*(poly[1][i]-poly[0][i]) + v*(poly[3][i]-poly[0][i]) for i in (0,1))


def inverse(poly, width, height, point):
    u = tuple(poly[1][i]-poly[0][i] for i in (0,1))
    v = tuple(poly[3][i]-poly[0][i] for i in (0,1))
    d = tuple(point[i]-poly[0][i] for i in (0,1))
    det = u[0]*v[1]-u[1]*v[0]
    if abs(det) < 1e-12:
        raise ValueError('Degenerate module geometry.')
    return ((d[0]*v[1]-d[1]*v[0])/det*width, (u[0]*d[1]-u[1]*d[0])/det*height)


def dimension_geometry(p1, p2, label, axis='aligned'):
    if axis == 'horizontal':
        return (p1[0],label[1]), (p2[0],label[1]), abs(p2[0]-p1[0])
    if axis == 'vertical':
        return (label[0],p1[1]), (label[0],p2[1]), abs(p2[1]-p1[1])
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    length = math.hypot(dx,dy)
    if length < 1e-9:
        return p1,p2,0
    normal = (-dy/length,dx/length)
    offset = sum((label[i]-(p1[i]+p2[i])/2)*normal[i] for i in (0,1))
    return tuple(p1[i]+offset*normal[i] for i in (0,1)), tuple(p2[i]+offset*normal[i] for i in (0,1)), length


def validate_plan(raw):
    if raw is None:
        return empty_plan()
    if not isinstance(raw,dict) or raw.get('version') != 1:
        raise ValueError('Invalid mounting plan or unknown version.')
    plan = copy.deepcopy(raw)
    from mounting_edges import validate_rules
    plan['edge_rules']=validate_rules(plan.get('edge_rules'))
    plan['site']=validate_site(plan.get('site'))
    if not isinstance(plan.get('panels'),dict) or not isinstance(plan.get('dimensions'),list):
        raise ValueError('Invalid mounting plan content.')
    # Hidden *display dimensions* survive local JSON export/import. They do not
    # affect physical fixing positions, geometry, or the installation schedule.
    hidden=plan.setdefault('hidden_dimensions',[])
    if (not isinstance(hidden,list) or len(hidden)>10000 or
        any(not isinstance(key,str) or not key or len(key)>512 for key in hidden)):
        raise ValueError('Invalid hidden dimensions list.')
    plan['hidden_dimensions']=list(dict.fromkeys(hidden))
    labels=plan.setdefault('dimension_labels',{})
    if (not isinstance(labels,dict) or len(labels)>10000 or
        any(not isinstance(key,str) or not key or len(key)>512 or
            not isinstance(value,str) or not value.strip() or len(value)>160 or
            any(ch in value for ch in '\r\n\x00')
            for key,value in labels.items())):
        raise ValueError('Invalid custom dimension labels.')
    if plan.get('template') is not None:
        plan['template'] = validate_config(plan['template'],footprint=not plan['edge_rules']['enabled'])
    plan['panels'] = {uid:validate_config(c,footprint=not plan['edge_rules']['enabled']) for uid,c in plan['panels'].items()}
    for d in plan['dimensions']:
        if not isinstance(d,dict):raise ValueError('Invalid mounting dimension.')
        override=d.get('text_override')
        if override is not None and (not isinstance(override,str) or not override.strip() or
                                      len(override)>160 or any(ch in override for ch in '\r\n\x00')):
            raise ValueError('Invalid custom dimension label.')
        if not isinstance(d,dict) or d.get('axis') not in ('horizontal','vertical','aligned'):
            raise ValueError('Invalid mounting dimension.')
        for name in ('p1','p2','label'):
            p=d.get(name)
            if not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p):
                raise ValueError('Invalid dimension point.')
        for name in ('ref1','ref2'):
            ref=d.get(name)
            if ref is not None and (not isinstance(ref,dict) or not isinstance(ref.get('uid'),str)
                or ref.get('kind') not in ('corner','fixing','fixing_corner') or type(ref.get('index')) is not int
                or not 0<=ref['index']<{'corner':4,'fixing':12,'fixing_corner':48}.get(ref.get('kind'),0)):
                raise ValueError('Invalid dimension reference.')
    return plan
