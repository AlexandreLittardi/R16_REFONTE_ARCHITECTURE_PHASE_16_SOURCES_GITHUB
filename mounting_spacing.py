"""Measured, project-independent inter-module clearances in layout coordinates.

U is the first module edge (corner 1 -> 2); V is corner 1 -> 4.
Values are plan-projected clear distances, not roof-slope/geodesic measures.
"""
import math


def nearest_gaps(items, px_per_mm, only_uid=None):
    """For each requested panel find nearest forward aligned panel on U and V.

    Returns {uid: {'u': (neighbor_number, gap_mm) or None, 'v': ...}}.
    Handles arbitrary module sizes, rotation and irregular layouts, and does
    not assume an array grid or spacing prescribed by a particular project.
    """
    if not math.isfinite(px_per_mm) or px_per_mm <= 0:
        raise ValueError('Échelle du plan manquante.')
    candidates = list(items.items())
    result = {}
    for uid, item in candidates:
        if only_uid is not None and uid != only_uid:
            continue
        p = item['poly']
        ex = (p[1][0]-p[0][0], p[1][1]-p[0][1])
        ey = (p[3][0]-p[0][0], p[3][1]-p[0][1])
        lu, lv = math.hypot(*ex), math.hypot(*ey)
        if min(lu,lv) < 1e-9:
            result[uid] = {'u': None, 'v': None}
            continue
        ex,ey=(ex[0]/lu,ex[1]/lu),(ey[0]/lv,ey[1]/lv)
        def project(poly,axis):
            values=[x*axis[0]+y*axis[1] for x,y in poly]
            return min(values),max(values)
        u0,u1=project(p,ex);v0,v1=project(p,ey)
        nearest={'u':None,'v':None}
        for other_uid,other in candidates:
            if other_uid==uid:continue
            q=other['poly']
            qu=(q[1][0]-q[0][0],q[1][1]-q[0][1])
            qv=(q[3][0]-q[0][0],q[3][1]-q[0][1])
            if min(math.hypot(*qu),math.hypot(*qv))<1e-9:continue
            qu=(qu[0]/math.hypot(*qu),qu[1]/math.hypot(*qu))
            qv=(qv[0]/math.hypot(*qv),qv[1]/math.hypot(*qv))
            # Reject oblique panel neighbors: distances must be perpendicular
            # between parallel edges, not diagonal edge-to-edge distances.
            if abs(ex[0]*qu[0]+ex[1]*qu[1]) < .9999 or abs(ey[0]*qv[0]+ey[1]*qv[1]) < .9999:
                continue
            r0,r1=project(q,ex);s0,s1=project(q,ey)
            overlap_v=min(v1,s1)-max(v0,s0)
            overlap_u=min(u1,r1)-max(u0,r0)
            tol=max(1e-5, 0.001*px_per_mm)
            if overlap_v > tol and r0 >= u1-tol:
                d=max(0.,(r0-u1)/px_per_mm)
                if nearest['u'] is None or d < nearest['u'][1]:
                    nearest['u']=(other['number'],d)
            if overlap_u > tol and s0 >= v1-tol:
                d=max(0.,(s0-v1)/px_per_mm)
                if nearest['v'] is None or d < nearest['v'][1]:
                    nearest['v']=(other['number'],d)
        result[uid]=nearest
    return result
