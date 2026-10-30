"""Polygon validity check shared by persistence and editor commands."""
import math

def valid_polygon(points):
    if len(points)<3 or len(set(map(tuple,points)))!=len(points):return False
    if any(len(p)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in p) for p in points):return False
    def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def hits(a,b,c,d):
        eps=1e-9
        o=[orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)]
        if o[0]*o[1]<-eps and o[2]*o[3]<-eps:return True
        def on(a,b,c):return abs(orient(a,b,c))<eps and min(a[0],b[0])-eps<=c[0]<=max(a[0],b[0])+eps and min(a[1],b[1])-eps<=c[1]<=max(a[1],b[1])+eps
        return on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b)
    n=len(points)
    for i in range(n):
        for j in range(i+1,n):
            if j==i+1 or (i==0 and j==n-1):continue
            if hits(points[i],points[(i+1)%n],points[j],points[(j+1)%n]):return False
    area=abs(sum(points[i][0]*points[(i+1)%n][1]-points[(i+1)%n][0]*points[i][1] for i in range(n)))
    return area>1e-8

