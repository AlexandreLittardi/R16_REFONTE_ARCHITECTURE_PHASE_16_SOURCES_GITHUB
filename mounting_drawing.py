"""Shared mounting scene for the Tk editor and complete vector SVG export."""
import csv
import math
from html import escape
from mounting import validate_config, fixings, transform, dimension_geometry, axes, validate_fixing_sizes
from mounting_edges import validate_rules, topology, is_boundary, fixing_type
from mounting_spacing import nearest_gaps
from mounting_quantities import fixing_inventory


def geometry(app,plan=None):
    plan=app.mounting_plan if plan is None else plan
    rules=validate_rules(plan.get('edge_rules'))
    result={}
    for coord,number in app.panels.items():
        poly=app._panel_rect(coord)
        if not poly:
            continue
        uid=app.panel_uids.get(coord)
        raw=plan['panels'].get(uid)
        config=None;issue=None
        if raw:
            try:
                config=validate_config(raw,footprint=not rules['enabled'])
                if app.px_per_mm<=0 or not getattr(app,'roof_zones',[]):
                    raise ValueError('Missing scale or installation areas.')
                if abs(config['width_mm']-app.panel_width_mm)>1e-6 or abs(config['height_mm']-app.panel_height_mm)>1e-6:
                    raise ValueError('Module dimensions changed: reconfigure mounting.')
            except ValueError as exc:
                config=None;issue=str(exc)
        item=dict(coord=coord,number=number,uid=uid,poly=poly,config=config,issue=issue,fixings=[])
        result[uid]=item
    polygons={uid:item['poly'] for uid,item in result.items()}
    signature=(rules['max_gap_mm'],app.px_per_mm,tuple((uid,tuple(poly)) for uid,poly in polygons.items()))
    cached=getattr(app,'_mounting_topology_cache',None)
    if cached is None or cached[0]!=signature:
        cached=(signature,topology(polygons,rules['max_gap_mm']*app.px_per_mm))
        app._mounting_topology_cache=cached
    for uid,item in result.items():
        config=item['config'];poly=item['poly'];neighbors=cached[1][uid]
        item['is_boundary']=is_boundary(neighbors)
        if config:
            sizes={}
            for f in fixings(config):
                point=transform(poly,config['width_mm'],config['height_mm'],(f['x'],f['y']))
                automatic=fixing_type(poly,point,neighbors,axes(config)[2],f['side'])
                imposed=rules['overrides'].get(uid,{}).get(str(f['index']))
                kind=(imposed or automatic) if rules['enabled'] else 'standard'
                sizes[f['index']]=dict(rules['profiles'][kind] if kind!='standard' else {},
                                      kind=kind,automatic_kind=automatic,forced=bool(imposed and rules['enabled']))
            try:effective=validate_fixing_sizes(config,sizes)
            except ValueError as exc:
                item['issue']=str(exc);continue
            for fixing in effective:
                item['fixings'].append(dict(fixing,
                    point=transform(poly,config['width_mm'],config['height_mm'],(fixing['x'],fixing['y'])),
                    world_polygon=[transform(poly,config['width_mm'],config['height_mm'],p) for p in fixing['polygon']]))
    return result


def resolve_point(d,which,items):
    ref=d.get('ref'+str(which))
    if ref is None:
        return d['p'+str(which)]
    item=items.get(ref['uid'])
    if not item:
        return None
    if ref['kind']=='fixing_corner':
        points=[p for f in item['fixings'] for p in f['world_polygon']]
    else:points=item['poly'] if ref['kind']=='corner' else [f['point'] for f in item['fixings']]
    return points[ref['index']] if ref['index']<len(points) else None


def dimension(items,p1,p2,label,axis,ratio,font=11,color='#222222',tag=None,prefix='',dim_id=None,selected=False,text_override=None):
    a,b,length=dimension_geometry(p1,p2,label,axis)
    if length<1e-8:
        return
    if selected:color='#000000'
    style=dict(color=color,tag=tag,dim_id=dim_id)
    line_width=2.5 if selected else 1
    for start,end in ((p1,a),(p2,b),(a,b)):
        items.append(dict(kind='line',points=[start,end],width=line_width,**style))
    dx,dy=b[0]-a[0],b[1]-a[1];norm=math.hypot(dx,dy)
    if norm:
        ux,uy=dx/norm,dy/norm
        size=min(font*.65,norm/4)
        for p,sign in ((a,1),(b,-1)):
            items.append(dict(kind='polygon',points=[p,(p[0]+sign*ux*size-uy*size*.35,p[1]+sign*uy*size+ux*size*.35),
                (p[0]+sign*ux*size+uy*size*.35,p[1]+sign*uy*size-ux*size*.35)],fill=color,color=color,width=line_width,tag=tag,dim_id=dim_id))
    items.append(dict(kind='text',point=label,text=(text_override if text_override is not None else f'{prefix}{length/ratio:.1f} mm'),font=font,color=color,background=True,tag=tag,dim_id=dim_id))



def site_origin(app, items=None, plan=None):
    """Return (image-pixel datum, explicitly surveyed flag). Y is image-down."""
    plan=plan if plan is not None else app.mounting_plan
    site=plan.get('site') or {}
    if site.get('origin') is not None:
        return tuple(site['origin']), True
    if items is None:items=geometry(app,plan)
    first=next(iter(items.values()),None)
    return (tuple(first['poly'][0]) if first else (0.,0.)),False


def construction_shapes(app, items=None, font=11, selected=(), selected_fixing=None,
                        plan=None, detailed=True, selected_dimension=None, force_detail=False):
    """Live dimension layer, computed from the actual geometry (never persisted)."""
    plan=app.mounting_plan if plan is None else plan
    if not app.px_per_mm or app.px_per_mm<=0:return []
    items=geometry(app,plan) if items is None else items
    if not items:return []
    shapes=[];ratio=app.px_per_mm
    hidden=set(plan.get('hidden_dimensions',[]))
    overrides=plan.get('dimension_labels',{})
    def add_dim(dim_id,p1,p2,label,axis='aligned',color='#333333',prefix=''):
        if dim_id not in hidden:
            dimension(shapes,p1,p2,label,axis,ratio,font,color=color,prefix=prefix,
                      dim_id=dim_id,selected=(dim_id==selected_dimension),
                      text_override=overrides.get(dim_id))
    vertices=[p for i in items.values() for p in i['poly']]
    l=min(p[0] for p in vertices);r=max(p[0] for p in vertices)
    t=min(p[1] for p in vertices);b=max(p[1] for p in vertices)
    # Field dimensions live outside the modules. These include their rotation.
    spacing=max(65*ratio, font*5)
    if r-l>1e-8:
        add_dim('field:x',(l,t),(r,t),((l+r)/2,t-spacing),'horizontal',color='#222222',prefix='X champ = ')
    if b-t>1e-8:
        add_dim('field:y',(r,t),(r,b),(r+spacing,(t+b)/2),'vertical',color='#222222',prefix='Y champ = ')
    origin,confirmed=site_origin(app,items,plan)
    color='#222222' if confirmed else '#555555'
    size=max(font*.85,3*ratio)
    x,y=origin
    for a,q in (((x-size,y),(x+size,y)),((x,y-size),(x,y+size))):
        shapes.append(dict(kind='line',points=[a,q],color=color,width=1.4))
    shapes.append(dict(kind='text',point=(x+font*2,y-font*2),
        text=(plan.get('site') or {}).get('origin_label','O')+('' if confirmed else ' (temporary)'),
        font=font,color=color,background=True))
    if not detailed:return shapes
    # Keep general overviews legible: just the selected module, no repeated
    # dimension chain across hundreds of panels. The PDF has all module details.
    chosen=next((i for i in items.values() if i['coord'] in selected and i['config'] and not i['issue']),None)
    if chosen:
        # Detailed strings of dimensions are only legible after zooming in.
        # The field-wide X/Y dimensions remain visible at any zoom level.
        module_span=math.dist(chosen['poly'][0],chosen['poly'][3])
        if not force_detail and module_span*getattr(app,'zoom_level',1.)<155:
            chosen=None
    if chosen:
        c=chosen['config'];length,cross,along_y=axes(c)
        # Module outline dimensions (including rotation) and both actual station chains.
        sides=[[f['position_mm'] for f in chosen['fixings'] if f['side']==side] for side in (0,1)]
        visible_sides=(0,1) if sides[0]!=sides[1] else (0,)
        if c['count']==6 and c.get('top_offsets_mm') is not None and along_y and sides[0]==sides[1]:
            # Three cumulative top-edge dimensions; A/B/C are all measured
            # from the same upper datum rather than chained together.
            for station,name in enumerate('ABC'):
                stop=sides[0][station]
                from_top=transform(chosen['poly'],c['width_mm'],c['height_mm'],(0,0))
                axis=transform(chosen['poly'],c['width_mm'],c['height_mm'],(0,stop))
                x_offset=-max(font*(14+station*5)/ratio,95+station*75)
                label=transform(chosen['poly'],c['width_mm'],c['height_mm'],(x_offset,stop/2))
                add_dim(f'panel:{chosen["uid"]}:abc:{name}',from_top,axis,label,prefix=name+' = ')
            visible_sides=()
        for side in visible_sides:
            fs=[f for f in chosen['fixings'] if f['side']==side]
            stations=[(0.,0)]+[(f['position_mm'],f['index']+1) for f in fs]+[(length,0)]
            for interval,((start,_),(stop,_)) in enumerate(zip(stations,stations[1:])):
                if stop-start<1e-7:continue
                def at(position):
                    local=(side*cross,position) if along_y else (position,side*cross)
                    return transform(chosen['poly'],c['width_mm'],c['height_mm'],local)
                a,q=at(start),at(stop)
                local_label=((side*cross+(-1 if side==0 else 1)*max(font*(15 if side==0 else 9)/ratio,90),(start+stop)/2)
                             if along_y else ((start+stop)/2,side*cross+(-1 if side==0 else 1)*max(font*(15 if side==0 else 9)/ratio,90)))
                label=transform(chosen['poly'],c['width_mm'],c['height_mm'],local_label)
                add_dim(f'panel:{chosen["uid"]}:chain:{side}:{interval}',a,q,label)
    if chosen:
        # The closest forward neighbors of the selected module provide the
        # actual free U/V clearances (not guessed row/column spacing).
        uid=chosen['uid']
        spacings=nearest_gaps(items,ratio,only_uid=uid).get(uid,{})
        poly=chosen['poly']
        for key,side in (('u',(1,2)),('v',(2,3))):
            gap=spacings.get(key)
            if gap is None:continue
            neighbor,mm=gap
            a,b=poly[side[0]],poly[side[1]]
            a0=((a[0]+b[0])/2,(a[1]+b[1])/2)
            vector=((poly[1][0]-poly[0][0],poly[1][1]-poly[0][1]) if key=='u'
                    else (poly[3][0]-poly[0][0],poly[3][1]-poly[0][1]))
            length=math.hypot(*vector)
            if length<=0:continue
            a1=(a0[0]+vector[0]/length*mm*ratio,a0[1]+vector[1]/length*mm*ratio)
            perpendicular=(-vector[1]/length,vector[0]/length)
            middle=((a0[0]+a1[0])/2,(a0[1]+a1[1])/2)
            if math.dist(a0,a1)>0.01*ratio:
                label=(middle[0]+perpendicular[0]*max(12*font,35*ratio),
                       middle[1]+perpendicular[1]*max(12*font,35*ratio))
                add_dim(f'panel:{uid}:gap:{key}',a0,a1,label,color='#444444',
                        prefix=f'Ecart {key.upper()} -> P{neighbor} = ')
            else:
                gap_id=f'panel:{uid}:gap:{key}'
                if gap_id not in hidden:
                    shapes.append(dict(kind='text',point=middle,
                        text=overrides.get(gap_id,f'Ecart {key.upper()} -> P{neighbor} = 0 mm'),font=font,
                        color='#000000' if gap_id==selected_dimension else '#444444',
                        background=True,dim_id=gap_id))
    if selected_fixing:
        uid,index=selected_fixing;item=items.get(uid)
        if item and index<len(item['fixings']):
            f=item['fixings'][index]
            origin,_=site_origin(app,items,plan)
            x,y=f['point']; ox,oy=origin
            text=f"F{index+1} = {f['position_mm']:.1f} mm"
            fid=f'fixing:{uid}:{index}'
            if fid not in hidden:
                active=fid==selected_dimension
                shapes.append(dict(kind='line',points=[(x,y),(x+font*8,y-font*3)],
                    color='#000000' if active else '#222222',width=2.5 if active else 1,dim_id=fid))
                shapes.append(dict(kind='text',point=(x+font*8,y-font*4),text=overrides.get(fid,text),font=font,
                    color='#000000' if active else '#222222',background=True,dim_id=fid))
    return shapes


def scene(app,items=None,font=11,selected=(),selected_dimension=None,selected_fixing=None,plan=None,construction=True,inventory=None):
    plan=app.mounting_plan if plan is None else plan
    items=geometry(app,plan) if items is None else items
    shapes=[]
    for p in app.roof_polygons:
        shapes.append(dict(kind='polygon',points=p['points'],fill='',color='#777777',width=1))
    for item in items.values():
        selected_panel=item['coord'] in selected
        shapes.append(dict(kind='polygon',points=item['poly'],fill='#ffffff',
            color='#000000' if item['issue'] else '#111111' if selected_panel else '#444444',width=2 if selected_panel else 1))
        center=tuple(sum(p[i] for p in item['poly'])/4 for i in (0,1))
        panel_width=math.dist(item['poly'][0],item['poly'][1])
        angle=math.degrees(math.atan2(item['poly'][1][1]-item['poly'][0][1],item['poly'][1][0]-item['poly'][0][0]))
        shapes.append(dict(kind='text',point=center,text=str(item['number']),font=panel_width/4,
            color='#151515',
            bold=True,angle=angle,background=False,role='panel_number',panel_uid=item['uid']))
    rules=validate_rules(plan.get('edge_rules'))
    if rules['enabled'] and app.px_per_mm>0:
        inventory=inventory or fixing_inventory(items,app.px_per_mm,rules['max_gap_mm'])
        physical=inventory['physical_fixings']
    else:
        physical=[dict(f,contacts=((uid,f['index']),),shared=False)
                  for uid,item in items.items() for f in item['fixings']]
    for f in physical:
        active=selected_fixing in f['contacts']
        color='#202020' if f['kind']=='edge' else '#888888'
        shapes.append(dict(kind='polygon',points=f['world_polygon'],color='#111111',
                           fill='#bcbcbc' if active else color,width=1,
                           fixing=f['contacts'][0],fixing_contacts=f['contacts'],
                           role='physical_clamp',shared=f['shared']))
        # One centre mark per physical clamp, not one mark per panel contact.
        radius=min(math.dist(f['world_polygon'][0],f['world_polygon'][1]),
                   math.dist(f['world_polygon'][1],f['world_polygon'][2]))*.18
        shapes.append(dict(kind='cross',point=f['point'],size=radius,color='#111111',
                           role='clamp_center'))

    if rules['enabled'] and items:
        points=[p for item in items.values() for p in item['poly']]
        label=f"End (R) : {rules['profiles']['edge']['reference']} | Intermediate (I) : {rules['profiles']['intermediate']['reference']}"
        shapes.append(dict(kind='text',point=(min(p[0] for p in points)+font*18,min(p[1] for p in points)-font*3),text=label,font=font,color='#222222',background=True,role='legend'))
    shapes.extend(annotations(plan,items,app.px_per_mm,font,selected_dimension))
    if construction:shapes.extend(construction_shapes(app,items,font,plan=plan,detailed=False))
    return shapes


def annotations(plan,items,ratio,font=11,selected_dimension=None):
    shapes=[]
    if ratio>0:
        for i,d in enumerate(plan['dimensions']):
            p1,p2=resolve_point(d,1,items),resolve_point(d,2,items)
            if p1 is None or p2 is None:
                shapes.append(dict(kind='text',point=d['label'],text='Missing reference',font=font,color='#000000',background=True,tag=i))
                continue
            dimension(shapes,p1,p2,d['label'],d['axis'],ratio,font,
                      '#111111' if selected_dimension==i else '#222222',i,
                      text_override=d.get('text_override'))
    return shapes


def draw_tk(canvas,shapes,zoom=1.,offset=(0,0),live=False):
    def xy(p):return (p[0]*zoom+offset[0],p[1]*zoom+offset[1])
    for s in shapes:
        color=s.get('color','#222222')
        tags=('mounting',)+(('dimension:'+str(s['tag']),) if s.get('tag') is not None else ())
        tags+=('mounting_live_dims',) if live else (('mounting_annotation',) if s.get('tag') is not None else ('mounting_geometry',))
        if live and s.get('dim_id') is not None:
            tags+=(f"live-dimension:{s['dim_id']}",)
        if s.get('role')=='panel_number':tags+=('mounting-number',f"panel-number:{s['panel_uid']}")
        if s.get('fixing') is not None:
            contacts=s.get('fixing_contacts',(s['fixing'],))
            tags+=('fixing-footprint',)+(tuple(f"fixing:{uid}:{index}" for uid,index in contacts))
        if s['kind'] in ('polygon','line'):
            flat=[v for p in s['points'] for v in xy(p)]
            if s['kind']=='polygon':canvas.create_polygon(*flat,fill=s.get('fill',''),outline=color,width=s['width'],tags=tags)
            else:canvas.create_line(*flat,fill=color,width=s['width'],tags=tags)
        elif s['kind']=='cross':
            x,y=xy(s['point']);r=s['size']*zoom
            canvas.create_line(x-r,y,x+r,y,fill=color,tags=tags)
            canvas.create_line(x,y-r,x,y+r,fill=color,tags=tags)
        elif s['kind']=='text':
            x,y=xy(s['point'])
            size=max(7,int(s['font']*zoom)) if s.get('role')=='panel_number' else max(8,round(s['font']*zoom))
            font=('Arial',size,'bold') if s.get('bold') else ('Arial',size)
            text=canvas.create_text(x,y,text=s['text'],fill=color,font=font,angle=s.get('angle',0),tags=tags)
            if s.get('background'):
                box=canvas.bbox(text)
                bg=canvas.create_rectangle(box[0]-3,box[1]-2,box[2]+3,box[3]+2,fill='white',outline='',tags=tags)
                canvas.tag_lower(bg,text)


def bounds(shapes,source=None,font=11):
    points=[]
    for s in shapes:
        points.extend(s.get('points',[]))
        if 'point' in s:
            x,y=s['point'];pad=len(s.get('text',''))*s.get('font',font)*.3
            points.extend([(x-pad,y-font),(x+pad,y+font)])
    if source is not None:points.extend([(0,0),(source.width,source.height)])
    if not points:points=[(0,0),(800,600)]
    margin=font*4
    return (min(x for x,y in points)-margin,min(y for x,y in points)-margin,
            max(x for x,y in points)+margin,max(y for x,y in points)+margin)


def write_svg(app,path):
    if app.px_per_mm<=0:
        raise ValueError('Calibrate the drawing before exporting.')
    items=geometry(app)
    shapes=scene(app,items,construction=False)
    # Exporting a drawing must not depend on the current GUI zoom. Include
    # selected-panel A/B/C and clearance dimensions regardless of zoom level.
    shapes.extend(construction_shapes(app,items,selected=getattr(app,'selected_panel_coords',()),
                                      detailed=True,force_detail=True))
    left,top,right,bottom=bounds(shapes)
    width,height=right-left,bottom-top
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width/app.px_per_mm:.6f}mm" height="{height/app.px_per_mm:.6f}mm" viewBox="{left} {top} {width} {height}">',
         '<title>'+escape(app.project_name)+' — Mounting drawing, dimensions in mm</title>',
         f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="white"/>']
    for s in shapes:
        color=s.get('color','#222222')
        if s['kind'] in ('line','polygon'):
            points=' '.join(f'{x:.6f},{y:.6f}' for x,y in s['points'])
            kind='polygon' if s['kind']=='polygon' else 'polyline'
            attributes=(' data-role="physical-clamp" data-contacts="'+
                escape(';'.join(f'{uid}:F{index+1}' for uid,index in s.get('fixing_contacts',())))+'"'
                if s.get('role')=='physical_clamp' else '')
            out.append(f'<{kind} points="{points}" stroke="{color}" fill="{s.get("fill") or "none"}" stroke-width="{s["width"]}"{attributes}/>')
        elif s['kind']=='cross':
            x,y=s['point'];r=s['size']
            out.append(f'<path d="M {x-r},{y} H {x+r} M {x},{y-r} V {y+r}" stroke="{color}"/>')
        elif s['kind']=='text':
            x,y=s['point'];font=s['font']
            bg=' paint-order="stroke" stroke="white" stroke-width="4" stroke-linejoin="round"' if s.get('background') else ''
            style=' font-weight="bold"' if s.get('bold') else ''
            if s.get('angle'):style+=f' transform="rotate({-s["angle"]} {x} {y})"'
            if s.get('role')=='panel_number':style+=' data-role="panel-number"'
            out.append(f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central" font-family="Arial,sans-serif" font-size="{font}" fill="{color}"{style}{bg}>{escape(s["text"])}</text>')
    out.append('</svg>')
    with open(path,'w',encoding='utf-8') as f:f.write('\n'.join(out))


def write_schedule(app,path):
    """Coordinates in a clearly identified image-origin mm datum, Y down."""
    if app.px_per_mm<=0:raise ValueError('Calibrate the drawing before exporting.')
    with open(path,'w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream,delimiter=';')
        writer.writerow(['Module','Clamp','Side','Position on frame (mm)','Drawing X (mm, image origin)','Drawing Y (mm, downward)','Clamp length (mm)','Clamp width (mm)','Statut','Type','Reference','Affectation','Boundary module',
                         'Site datum X (mm)','Site datum Y (mm)','Site corner 1 X (mm)','Site corner 1 Y (mm)','Module orientation (deg)','Origin datum','Datum confirmed'])
        items=geometry(app);origin,confirmed=site_origin(app,items)
        datum=(app.mounting_plan.get('site') or {}).get('origin_label','O')
        def coords(p):return (round((p[0]-origin[0])/app.px_per_mm,2),round((p[1]-origin[1])/app.px_per_mm,2))
        for item in items.values():
            if not item['fixings']:
                corner=coords(item['poly'][0]);angle=math.degrees(math.atan2(item['poly'][1][1]-item['poly'][0][1],item['poly'][1][0]-item['poly'][0][0]))
                writer.writerow([item['number'],'','','','','','','',item['issue'] or 'Mounting not defined','','','','Yes' if item['is_boundary'] else 'No',
                                 '','',*corner,round(angle,2),datum,'Yes' if confirmed else 'NO - TEMPORARY'])
            for f in item['fixings']:
                writer.writerow([item['number'],f['index']+1,f['side']+1,f['position_mm'],
                    round(f['point'][0]/app.px_per_mm,3),round(f['point'][1]/app.px_per_mm,3),
                    f['length_mm'],f['width_mm'],'Mounting geometry',
                    {'edge':'End','intermediate':'Intermediate','standard':'Uniform'}[f['kind']],f['reference'],
                    'Manual' if f.get('forced') else 'Automatic' if f['kind']!='standard' else 'Uniform',
                    'Yes' if item['is_boundary'] else 'No',*coords(f['point']),*coords(item['poly'][0]),
                    round(math.degrees(math.atan2(item['poly'][1][1]-item['poly'][0][1],item['poly'][1][0]-item['poly'][0][0])),2),
                    datum,'Yes' if confirmed else 'NO - TEMPORARY'])
