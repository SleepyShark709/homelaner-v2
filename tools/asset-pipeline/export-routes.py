"""Sample six independent original road/sidewalk spline segments, not original AI routes."""
import importlib.util, json, math, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('city_export',pathlib.Path(__file__).with_name('export-city.py'))
city=importlib.util.module_from_spec(spec);spec.loader.exec_module(city)
PUBLIC=ROOT/'public/assets/city'

def load_mesh(name):
    path=PUBLIC/'meshes'/name/(name+'.gltf');d=city.read(path);buffers=[(path.parent/b['uri']).read_bytes() for b in d['buffers']];triangles=[];vertices=[]
    for mesh in d['meshes']:
        for p in mesh['primitives']:
            points=city.accessor(d,buffers,p['attributes']['POSITION']);indices=[x[0] for x in city.accessor(d,buffers,p['indices'])];vertices+=points
            triangles += [[points[indices[i+j]] for j in range(3)] for i in range(0,len(indices),3)]
    return triangles,[min(v[j] for v in vertices) for j in range(3)],[max(v[j] for v in vertices) for j in range(3)]

def height_at(triangles,x,z):
    heights=[]
    for a,b,c in triangles:
        det=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(det)<1e-12:continue
        u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/det
        v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/det
        if min(u,v,1-u-v)>=-1e-6:heights.append(u*a[1]+v*b[1]+(1-u-v)*c[1])
    return max(heights) if heights else None

def unwrap(v):
    while isinstance(v,dict) and len(v)==1:v=next(iter(v.values()))
    return v
def v2(v,default):
    v=unwrap(v)
    return [float(v.get(k,default[i])) for i,k in enumerate('XY')] if isinstance(v,dict) else default

def sample_segment(row,mesh):
    triangles,lo,hi=mesh;params=row['properties']['SplineParams']
    p0,p1,t0,t1=[city.vec(params.get(k)) for k in ['StartPos','EndPos','StartTangent','EndTangent']]
    s0,s1=[v2(params.get(k),[1,1]) for k in ['StartScale','EndScale']]
    o0,o1=[v2(params.get(k),[0,0]) for k in ['StartOffset','EndOffset']]
    r0,r1=[float(params.get(k,0)) for k in ['StartRoll','EndRoll']]
    # Original local glTF Z equals UE Y (the transverse width coordinate).
    transverse=(lo[2]+hi[2])/2;points=[];heights=[]
    for i in range(17):
        t=.025+.95*i/16;x=lo[0]+(hi[0]-lo[0])*t;height=height_at(triangles,x,transverse)
        if height is None:return None
        heights.append(height);t2=t*t;t3=t2*t
        center=[(2*t3-3*t2+1)*p0[j]+(t3-2*t2+t)*t0[j]+(-2*t3+3*t2)*p1[j]+(t3-t2)*t1[j] for j in range(3)]
        tangent=city.unit([(6*t2-6*t)*p0[j]+(3*t2-4*t+1)*t0[j]+(-6*t2+6*t)*p1[j]+(3*t2-2*t)*t1[j] for j in range(3)])
        bx=city.unit(city.cross([0,0,1],tangent));by=city.unit(city.cross(tangent,bx));roll=r0+(r1-r0)*t
        xx=city.add(city.mul(bx,math.cos(roll)),city.mul(by,-math.sin(roll)));yy=city.add(city.mul(by,math.cos(roll)),city.mul(bx,math.sin(roll)))
        scale=[s0[j]+(s1[j]-s0[j])*t for j in range(2)];offset=[o0[j]+(o1[j]-o0[j])*t for j in range(2)]
        local=city.add(center,city.add(city.mul(xx,offset[0]+transverse*100*scale[0]),city.mul(yy,offset[1]+height*100*scale[1])))
        world=city.add(row['positionUE'],city.qrotate(row['rotationUE'],[local[j]*row['scaleUE'][j] for j in range(3)]));points.append(city.glpos(world))
    return points,{'sourceMesh':row['package'],'transverseSourceGLTFMeters':transverse,'sourceSurfaceHeightRangeMeters':[min(heights),max(heights)],'sampleParameterRange':[.025,.975],'method':'Transverse mesh bounds midpoint; exact highest source triangle intersection at each longitudinal sample; apply original SplineParams and full parent transform. No additional foot lift.'}

def building_boxes(manifest):
    assets={a['id']:a for a in manifest['assets']};boxes=[]
    for o in manifest['objects']:
        a=assets[o['assetId']]
        if a['kind']!='building':continue
        lo,hi=a['bounds']['min'],a['bounds']['max'];points=[]
        for x in [lo[0],hi[0]]:
            for y in [lo[1],hi[1]]:
                for z in [lo[2],hi[2]]:points.append(city.add(o['position'],city.qrotate(o['rotation'],[v*s for v,s in zip([x,y,z],o['scale'])])))
        boxes.append({'id':o['id'],'min':[min(v[j] for v in points) for j in range(3)],'max':[max(v[j] for v in points) for j in range(3)]})
    return boxes

def main():
    manifest=city.read(PUBLIC/'manifest.json');source=city.read(ROOT/'research/evidence/city-layout-source.json');spawn=manifest['spawn'];bounds=manifest['bounds'];boxes=building_boxes(manifest);cache={};candidates=[];rejected=[]
    if manifest['originUE']!=city.ORIGIN:raise ValueError('Manifest/export origin mismatch; refusing misaligned routes')
    for row in source['nearbySplines']:
        name=row['package'].rsplit('/',1)[1];kind='sidewalk' if name.startswith('Sidewalk_') else 'road'
        if name not in cache:cache[name]=load_mesh(name)
        sampled=sample_segment(row,cache[name])
        if not sampled:rejected.append({'sourceComponent':row['sourceComponent'],'reason':'No source triangle at cross-section midpoint'});continue
        points,evidence=sampled
        if any(not all(bounds['min'][j]<=p[j]<=bounds['max'][j] for j in [0,2]) for p in points):continue
        # Conservative XZ building footprint clearance at 17 points and 8 substeps per segment.
        dense=[[(a[j]+(b[j]-a[j])*t/8) for j in range(3)] for a,b in zip(points,points[1:]) for t in range(9)]
        overlaps=[box['id'] for box in boxes if any(box['min'][0]-.5<=p[0]<=box['max'][0]+.5 and box['min'][2]-.5<=p[2]<=box['max'][2]+.5 for p in dense)]
        if overlaps:rejected.append({'sourceComponent':row['sourceComponent'],'reason':'Expanded building footprint overlaps sampled path','buildings':overlaps});continue
        midpoint=points[len(points)//2];distance=math.hypot(midpoint[0]-spawn[0],midpoint[2]-spawn[2]);length=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
        candidates.append({'route':{'id':kind+'-'+row['sourceComponent'],'kind':kind,'points':points,'sourceComponent':row['sourceComponent'],'closed':False},'evidence':evidence,'distanceToSpawn':distance,'lengthMeters':length})
    chosen=[]
    for kind in ['road','sidewalk']:
        options=sorted((x for x in candidates if x['route']['kind']==kind),key=lambda x:x['distanceToSpawn'])
        chosen+=options[:3]
    city.write(PUBLIC/'routes.json',[x['route'] for x in chosen])
    city.write(ROOT/'research/evidence/city-layout-routes.json',{'coordinateSystem':manifest['coordinateSystem'],'originUE':manifest['originUE'],'scope':'Six independent original geometry spline segments, not recovered original AI routes; no invented connections.','selection':'Closest three road and three sidewalk segments to spawn after conservative bounds and expanded building-footprint screening.','routes':[{k:v for k,v in x.items() if k!='route'}|{'id':x['route']['id'],'sourceComponent':x['route']['sourceComponent']} for x in chosen],'rejected':rejected,'candidateCount':len(candidates),'buildingClearanceMeters':.5})
    print(json.dumps([{'id':x['route']['id'],'distance':x['distanceToSpawn'],'length':x['lengthMeters']} for x in chosen],indent=2))

if __name__=='__main__':main()
