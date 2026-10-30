"""Installation bill of materials: distinguish panel contact points from physical clamps.

Two intermediate fixing points form ONE physical clamp only if both faces match,
the references and footprints coincide, and their axes align along the seam.
Unknown, unmatched or incompatible points are not optimistically merged.
"""
from collections import Counter
from collections import deque
import copy
import math
from mounting_edges import topology


def fixing_inventory(items, px_per_mm, max_gap_mm=50.):
    if not isinstance(px_per_mm,(float,int)) or not math.isfinite(px_per_mm) or px_per_mm<=0:
        raise ValueError('Drawing scale not calibrated.')
    if not isinstance(max_gap_mm,(float,int)) or not math.isfinite(max_gap_mm) or max_gap_mm<0:
        raise ValueError('Invalid adjacency threshold.')
    visible={uid:item for uid,item in items.items() if item.get('poly')}
    faces=topology({uid:item['poly'] for uid,item in visible.items()},max_gap_mm*px_per_mm)
    point_totals=Counter()
    piece_totals=Counter()
    for uid,item in visible.items():
        for f in item.get('fixings',[]):
            key=(f['kind'],f.get('reference') or 'TO BE CONFIRMED',f['length_mm'],f['width_mm'])
            point_totals[key]+=1
            piece_totals[key]+=1
    matched=set()
    pair_records=[]
    # Build adjacency from physical facing edges; no possible pairing across open air.
    neighbors={uid:{o for side in faces[uid] for low,high,o in side} for uid in visible}
    for uid,item in visible.items():
        for f in item.get('fixings',[]):
            key_a=(uid,f['index'])
            if f['kind']!='intermediate' or key_a in matched:continue
            candidates=[]
            for other in neighbors[uid]:
                if other not in visible or uid not in neighbors.get(other,set()):continue
                for g in visible[other].get('fixings',[]):
                    key_b=(other,g['index'])
                    if key_b in matched or g['kind']!='intermediate':continue
                    if (g.get('reference') or '') != (f.get('reference') or ''):continue
                    if abs(g['length_mm']-f['length_mm'])>1e-6 or abs(g['width_mm']-f['width_mm'])>1e-6:continue
                    # Two clamp contact axes lie on the facing frame edges.
                    # Require them to coincide ALONG the common edge (1 mm).
                    # Across-edge separation must remain within the adjacency threshold.
                    px,py=f['point'];qx,qy=g['point']
                    poly=item['poly'];p0,p1,p3=poly[0],poly[1],poly[3]
                    ex=(p1[0]-p0[0],p1[1]-p0[1]); ey=(p3[0]-p0[0],p3[1]-p0[1])
                    axis=ex if abs(ex[0]*(qx-px)+ex[1]*(qy-py))>=abs(ey[0]*(qx-px)+ey[1]*(qy-py)) else ey
                    tangent=ex if axis is ey else ey
                    tangent_norm=math.hypot(*tangent)
                    if tangent_norm<1e-9:continue
                    along=abs(((qx-px)*tangent[0]+(qy-py)*tangent[1])/tangent_norm)/px_per_mm
                    across=abs(((qx-px)*axis[0]+(qy-py)*axis[1])/math.hypot(*axis))/px_per_mm
                    # A single physical clamp must actually bridge the gap.
                    # Zero overlap with either frame is not a viable connection.
                    # The installer must still confirm the *required* frame overlap.
                    if along<=1.0+1e-6 and across<=max_gap_mm+1e-6 and across<min(f['width_mm'],g['width_mm'])-1e-6:
                        candidates.append((along,across,other,g))
            if candidates:
                _,separation,other,g=min(candidates,key=lambda r:(r[0],r[1],r[2],r[3]['index']))
                key_b=(other,g['index']);matched.add(key_a);matched.add(key_b)
                spec=(f['kind'],f.get('reference') or 'TO BE CONFIRMED',f['length_mm'],f['width_mm'])
                piece_totals[spec]-=1
                pair_records.append({'a':key_a,'b':key_b,'gap_mm':separation,'reference':spec[1]})
    # Build a single geometric footprint per *physical* part. Contact axes
    # stay panel-specific for station cotations, but drawing/quantity/export
    # share the very same pairing decision. For shared clamps the footprint is
    # centered on the joint, not drawn twice on opposite module frames.
    pair_by_contact={}
    for record in pair_records:
        for key in (record['a'],record['b']):
            pair_by_contact[key]=record
    physical=[]
    contact_to_piece={}
    for uid,item in visible.items():
        for f in item.get('fixings',[]):
            key=(uid,f['index'])
            if key in contact_to_piece:continue
            pair=pair_by_contact.get(key)
            contacts=(pair['a'],pair['b']) if pair else (key,)
            other_f=(next(g for g in visible[contacts[1][0]]['fixings']
                         if g['index']==contacts[1][1]) if pair else None)
            point=(tuple((f['point'][i]+other_f['point'][i])/2 for i in (0,1))
                   if pair else tuple(f['point']))
            shift=(point[0]-f['point'][0],point[1]-f['point'][1])
            poly=[(p[0]+shift[0],p[1]+shift[1]) for p in f['world_polygon']]
            entry=dict(kind=f['kind'],reference=f.get('reference') or 'TO BE CONFIRMED',
                       length_mm=f['length_mm'],width_mm=f['width_mm'],
                       point=point,world_polygon=poly,contacts=contacts,
                       shared=bool(pair),gap_mm=pair['gap_mm'] if pair else None)
            for c in contacts:contact_to_piece[c]=len(physical)
            physical.append(entry)
    points_by_kind=Counter();pieces_by_kind=Counter()
    for spec,n in point_totals.items():points_by_kind[spec[0]]+=n
    for spec,n in piece_totals.items():pieces_by_kind[spec[0]]+=n
    unmatched_intermediate=points_by_kind['intermediate']-len(pair_records)*2
    return {'points':dict(point_totals),'pieces':dict(piece_totals),
            'points_by_kind':dict(points_by_kind),'pieces_by_kind':dict(pieces_by_kind),
            'points_total':sum(point_totals.values()), 'pieces_total':sum(piece_totals.values()),
            'shared_pairs':pair_records, 'unpaired_intermediate':unmatched_intermediate,
            'physical_fixings':physical, 'contact_to_piece':contact_to_piece}



def move_linked_stations(items, plan, inventory, uid, index, position_mm):
    """Move a clamp station and all contacts sharing that physical station.

    A/B/C stations link both sides of a six-fixing module, so the propagation
    crosses successive intermediate clamps in a row. This is a transactional
    geometric edit: the caller validates the complete resulting scene before
    replacing its saved mounting plan.
    """
    from mounting import axes, set_fixing_position, validate_config
    if uid not in items or index >= len(items[uid]['fixings']):
        raise ValueError('Clamp contact point unavailable.')
    origin=items[uid]
    f0=origin['fixings'][index]
    along_y=axes(origin['config'])[2]
    vec=((origin['poly'][3][0]-origin['poly'][0][0], origin['poly'][3][1]-origin['poly'][0][1])
         if along_y else (origin['poly'][1][0]-origin['poly'][0][0], origin['poly'][1][1]-origin['poly'][0][1]))
    length=origin['config']['height_mm' if along_y else 'width_mm']
    delta=position_mm-f0['position_mm']
    world_delta=(vec[0]*delta/length,vec[1]*delta/length)
    # Physical pair associations come from exactly the same inventory used by
    # the monochrome drawing and the bill of materials.
    adjacent={}
    for pair in inventory['shared_pairs']:
        a,b=pair['a'],pair['b']
        adjacent[a]=b;adjacent[b]=a
    pending=deque([(uid,index)]);visited=set();changes={}
    while pending:
        contact=pending.popleft()
        if contact in visited:continue
        visited.add(contact)
        module_id,i=contact
        item=items[module_id]
        f=item['fixings'][i];c=item['config']
        if c is None:raise ValueError('A connected module has no mounting configuration.')
        a_y=axes(c)[2]
        local=(item['poly'][3][0]-item['poly'][0][0],item['poly'][3][1]-item['poly'][0][1]) if a_y else (
            item['poly'][1][0]-item['poly'][0][0],item['poly'][1][1]-item['poly'][0][1])
        dim=c['height_mm' if a_y else 'width_mm']
        local=(local[0]/dim,local[1]/dim)
        denom=local[0]**2+local[1]**2
        if denom<1e-16:raise ValueError('Degenerate module geometry.')
        shift=(world_delta[0]*local[0]+world_delta[1]*local[1])/denom
        new_value=round(f['position_mm']+shift,3)
        if module_id not in changes:changes[module_id]=copy.deepcopy(c)
        changes[module_id]=set_fixing_position(changes[module_id],i,new_value)
        if contact in adjacent:pending.append(adjacent[contact])
        if c['count']==6 and c.get('top_offsets_mm') is not None:
            pending.append((module_id,2*(i//2)+(1-i%2)))
    result=copy.deepcopy(plan)
    enabled=(plan.get('edge_rules') or {}).get('enabled',False)
    for module_id,c in changes.items():
        result['panels'][module_id]=validate_config(c,footprint=not enabled)
    return result


def write_inventory_csv(app,path):
    """One project-wide physical BOM; no duplicate shared intermediate clamp."""
    import csv
    from mounting_drawing import geometry
    items=geometry(app)
    rules=(app.mounting_plan.get('edge_rules') or {})
    inventory=fixing_inventory(items,app.px_per_mm,rules.get('max_gap_mm',50))
    names={'edge':'End','intermediate':'Intermediate','standard':'Uniform'}
    with open(path,'w',encoding='utf-8-sig',newline='') as file:
        writer=csv.writer(file,delimiter=';')
        writer.writerow(['Type','Reference','Length Lf (mm)','Width lf (mm)',
                         'Points de contact','Physical clamps (pieces)'])
        for spec,n in sorted(inventory['points'].items()):
            kind,ref,length,width=spec
            writer.writerow([names[kind],ref,length,width,n,inventory['pieces'][spec]])
        writer.writerow(['TOTAL','','','',inventory['points_total'],inventory['pieces_total']])
        writer.writerow(['Unpaired intermediate clamps','','','',inventory['unpaired_intermediate'],''])
    return inventory


def write_physical_schedule_csv(app, path):
    """One installation coordinate per physical clamp, shared or individual."""
    import csv
    from mounting_drawing import geometry, site_origin
    items=geometry(app)
    rules=(app.mounting_plan.get('edge_rules') or {})
    inv=fixing_inventory(items,app.px_per_mm,rules.get('max_gap_mm',50))
    datum,confirmed=site_origin(app,items)
    with open(path,'w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream,delimiter=';')
        writer.writerow(['Physical clamp','Type','Reference','Length Lf (mm)','Width lf (mm)',
                         'Site datum clamp X (mm)','Site datum clamp Y (mm)',
                         'Associated contacts','Shared clamp','Jeu entre axes (mm)',
                         'Site datum confirmed'])
        for number,piece in enumerate(inv['physical_fixings'],1):
            x,y=piece['point']
            members=' + '.join(f"P{items[uid]['number']}/F{index+1}" for uid,index in piece['contacts'])
            writer.writerow([f'M{number}',piece['kind'],piece['reference'],piece['length_mm'],piece['width_mm'],
                round((x-datum[0])/app.px_per_mm,2),round((y-datum[1])/app.px_per_mm,2),
                members,'Yes' if piece['shared'] else 'No',
                round(piece['gap_mm'],2) if piece['shared'] else '',
                'Yes' if confirmed else 'NO - TEMPORARY'])
    return inv
