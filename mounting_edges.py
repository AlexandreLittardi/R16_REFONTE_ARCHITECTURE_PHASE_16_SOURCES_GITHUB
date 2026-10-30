"""Geometric frame adjacency and configurable end/intermediate mounting types."""
import copy
import math
from statistics import median


def default_rules(length=50.,width=40.):
    return dict(enabled=False,max_gap_mm=50.,joint_gap_mm=0.,profiles={
        'intermediate':dict(reference='Intermediate',length_mm=length,width_mm=width),
        'edge':dict(reference='End',length_mm=length,width_mm=width)},overrides={})


def validate_rules(raw):
    if raw is None:return default_rules()
    if not isinstance(raw,dict):raise ValueError('Invalid edge-clamp settings.')
    rules=copy.deepcopy(raw)
    if type(rules.get('enabled')) is not bool:raise ValueError('Invalid edge-clamp activation setting.')
    try:gap=float(rules['max_gap_mm'])
    except (KeyError,TypeError,ValueError):raise ValueError('Invalid maximum module gap.') from None
    if not math.isfinite(gap) or gap<0:raise ValueError('Maximum gap must be finite and non-negative.')
    rules['max_gap_mm']=gap
    try:joint=float(rules.get('joint_gap_mm',0))
    except (TypeError,ValueError):raise ValueError('Invalid intermediate clamp gap.') from None
    if not math.isfinite(joint) or joint<0 or joint>1000:
        raise ValueError('Clamp gap must be between 0 and 1000 mm.')
    rules['joint_gap_mm']=joint
    if joint>rules['max_gap_mm'] and rules['enabled']:
        rules['max_gap_mm']=joint
    if not isinstance(rules.get('profiles'),dict):raise ValueError('Missing clamp types.')
    for kind in ('intermediate','edge'):
        p=rules['profiles'].get(kind)
        if not isinstance(p,dict) or not isinstance(p.get('reference'),str) or not p['reference'].strip():
            raise ValueError('Enter a reference for each clamp type.')
        p['reference']=p['reference'].strip()
        for key in ('length_mm','width_mm'):
            try:value=float(p[key])
            except (KeyError,TypeError,ValueError):raise ValueError('Invalid clamp dimensions.') from None
            if not math.isfinite(value) or value<=0:raise ValueError('Clamp dimensions must be finite and strictly positive.')
            p[key]=value
    overrides=rules.setdefault('overrides',{})
    if not isinstance(overrides,dict):raise ValueError('Invalid clamp assignments.')
    for uid,values in overrides.items():
        if not isinstance(uid,str) or not isinstance(values,dict):raise ValueError('Invalid clamp assignment.')
        for index,kind in values.items():
            if index not in {str(i) for i in range(12)} or kind not in ('edge','intermediate'):
                raise ValueError('Invalid manual clamp type.')
    return rules


def _edge(poly,index):
    a,b=poly[index],poly[(index+1)%4]
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    if length<1e-10:raise ValueError('Degenerate module frame.')
    tangent=(dx/length,dy/length)
    center=tuple(sum(p[i] for p in poly)/4 for i in (0,1))
    normal=(-tangent[1],tangent[0]);mid=tuple((a[i]+b[i])/2 for i in (0,1))
    if sum((mid[i]-center[i])*normal[i] for i in (0,1))<0:normal=tuple(-v for v in normal)
    return a,b,tangent,normal,length


def topology(polygons,max_gap):
    """Return covered intervals of each frame edge; supports rotation and holes.

    Coordinates and max_gap share one unit. A spatial grid bounds candidate
    searches so the adjacency cache can be rebuilt for large layouts.
    """
    if not polygons:return {}
    cell=max(median(min(math.dist(p[0],p[1]),math.dist(p[1],p[2])) for p in polygons.values()),max_gap,1e-6)
    boxes={uid:(min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)) for uid,poly in polygons.items()}
    def cells(box,pad=0):
        x1,y1,x2,y2=box
        for x in range(math.floor((x1-pad)/cell),math.floor((x2+pad)/cell)+1):
            for y in range(math.floor((y1-pad)/cell),math.floor((y2+pad)/cell)+1):yield x,y
    buckets={}
    for uid,box in boxes.items():
        for key in cells(box):buckets.setdefault(key,set()).add(uid)
    edges={uid:[_edge(poly,i) for i in range(4)] for uid,poly in polygons.items()}
    result={uid:[[] for i in range(4)] for uid in polygons}
    eps=max(1e-8,cell*1e-8)
    for uid,poly in polygons.items():
        candidates=set()
        for key in cells(boxes[uid],max_gap+eps):candidates.update(buckets.get(key,()))
        candidates.discard(uid)
        for index,(a,b,t,n,length) in enumerate(edges[uid]):
            for other in candidates:
                for c,d,ot,on,ol in edges[other]:
                    if abs(t[0]*ot[0]+t[1]*ot[1])<1-1e-7 or n[0]*on[0]+n[1]*on[1]>-1+1e-7:continue
                    distances=[sum((p[i]-a[i])*n[i] for i in (0,1)) for p in (c,d)]
                    if min(distances)<-eps or max(distances)>max_gap+eps:continue
                    # The other module must lie outside, not overlap this module.
                    center=tuple(sum(p[i] for p in polygons[other])/4 for i in (0,1))
                    if sum((center[i]-a[i])*n[i] for i in (0,1))<=eps:continue
                    positions=[sum((p[i]-a[i])*t[i] for i in (0,1))/length for p in (c,d)]
                    lo,hi=max(0,min(positions)),min(1,max(positions))
                    if hi-lo>1e-8:result[uid][index].append((lo,hi,other))
    return result


def is_boundary(edges):
    for intervals in edges:
        end=0.
        for lo,hi,uid in sorted(intervals):
            if lo>end+1e-6:break
            end=max(end,hi)
        if end<1-1e-6:return True
    return False


def fixing_type(poly,point,edge_intervals,along_y,side):
    index=(3 if side==0 else 1) if along_y else (0 if side==0 else 2)
    a,b,t,n,length=_edge(poly,index)
    fraction=sum((point[i]-a[i])*t[i] for i in (0,1))/length
    return 'intermediate' if any(lo-1e-6<=fraction<=hi+1e-6 for lo,hi,uid in edge_intervals[index]) else 'edge'
