"""Original population models plus explicitly NEW browser population placement/routes."""
import hashlib, importlib.util, json, math, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('city',pathlib.Path(__file__).with_name('export-city.py'));city=importlib.util.module_from_spec(spec);spec.loader.exec_module(city)
PUBLIC=ROOT/'public';CITY=PUBLIC/'assets/city';OUT=PUBLIC/'assets/population'

def mesh_data(path):
    d=city.read(path);buffers=[(path.parent/b['uri']).read_bytes() for b in d['buffers']];triangles=[];lo=[math.inf]*3;hi=[-math.inf]*3
    for mesh in d['meshes']:
        for p in mesh['primitives']:
            vertices=city.accessor(d,buffers,p['attributes']['POSITION']);idx=[v[0] for v in city.accessor(d,buffers,p['indices'])]
            triangles += [[vertices[idx[i+j]] for j in range(3)] for i in range(0,len(idx),3)]
            for v in vertices:
                for j in range(3):lo[j]=min(lo[j],v[j]);hi[j]=max(hi[j],v[j])
    return triangles,{'min':lo,'max':hi}

def transform(p,obj):return city.add(obj['position'],city.qrotate(obj['rotation'],[v*s for v,s in zip(p,obj['scale'])]))

def world_data(manifest):
    assets={a['id']:a for a in manifest['assets']};cache={};cells={};boxes=[]
    for obj in manifest['objects']:
        a=assets[obj['assetId']]
        if a['id'] not in cache:cache[a['id']]=mesh_data(PUBLIC/a['url'].lstrip('/'))
        triangles,bounds=cache[a['id']]
        if a['kind']=='building':
            corners=[transform([x,y,z],obj) for x in [bounds['min'][0],bounds['max'][0]] for y in [bounds['min'][1],bounds['max'][1]] for z in [bounds['min'][2],bounds['max'][2]]]
            boxes.append({'id':obj['id'],'min':[min(p[j] for p in corners) for j in range(3)],'max':[max(p[j] for p in corners) for j in range(3)]})
        if a['kind']!='road':continue
        for tri in triangles:
            t=[transform(p,obj) for p in tri]
            for x in range(math.floor(min(p[0] for p in t)/10),math.floor(max(p[0] for p in t)/10)+1):
                for z in range(math.floor(min(p[2] for p in t)/10),math.floor(max(p[2] for p in t)/10)+1):cells.setdefault((x,z),[]).append(t)
    return cells,boxes

def ground(cells,x,z):
    heights=[]
    for a,b,c in cells.get((math.floor(x/10),math.floor(z/10)),[]):
        det=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(det)<1e-12:continue
        u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/det;v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/det
        if min(u,v,1-u-v)>=-1e-6:heights.append(u*a[1]+v*b[1]+(1-u-v)*c[1])
    if not heights:raise ValueError(f'No original ground surface at {x,z}')
    return max(heights)

def proof_breakable():
    pkg='/Game/-HeroGame/BP/Props/BP_BaseBreakProps';city.extract([pkg]);source=city.UNPACK/'UNDEFEATED/Content/-HeroGame/BP/Props/BP_BaseBreakProps.uasset';dest=city.WORK/'population/BP_BaseBreakProps.json';dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():
        s=subprocess.STARTUPINFO();s.dwFlags|=subprocess.STARTF_USESHOWWINDOW;s.wShowWindow=0
        subprocess.run([str(city.TOOLS/'uasset-net472/UAssetGUI.exe'),'tojson',str(source),str(dest),'VER_UE4_27'],check=True,capture_output=True,startupinfo=s,timeout=90)
    d=city.read(dest)
    def ref(i):return (d['Exports'][i-1] if i>0 else d['Imports'][-i-1]) if i else {}
    def path(i):
        e=ref(i);return (path(e['OuterIndex'])+'/' if e.get('OuterIndex') else '')+e.get('ObjectName','')
    default=next(e for e in d['Exports'] if e['ObjectName']=='Default__BP_BaseBreakProps_C');props={p['Name']:p.get('Value') for p in default['Data']};mesh=path(props['PropsStaticMesh']).rsplit('/',1)[0]
    return mesh,{'sourceBlueprint':pkg,'defaultObject':'Default__BP_BaseBreakProps_C','property':'PropsStaticMesh','mesh':mesh,'ForceScale':props.get('ForceScale'),'FadeOutDelayTime':props.get('FadeOutDelayTime'),'sourceAssetSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'decodedSha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'meaning':'Original breakable-prop default visual mesh. Export does not implement original fracture, physics, hit effect or fade behavior.'}

def main():
    manifest=city.read(CITY/'manifest.json');cells,boxes=world_data(manifest)
    propPackage,breakProof=proof_breakable();city.OUTPUT=OUT;propSource=city.export_mesh(propPackage);city.publish_mesh(propSource,'prop')
    definitions=[('citizen','citizen','/assets/citizen/citizen.gltf','+Z','Original citizen mesh + idle/walk/run clips; forward +Z follows toe-joint direction. Ground offset is bind-pose bottom; animation foot contact may vary.'),('sedan','vehicle','/assets/original/vehicle/vehicle.gltf','+X','Original Sedan_SkelMesh open-top sample; headlights establish +X front. Not a fully restored closed-roof sedan.'),('newspaper-box','prop','/assets/population/meshes/NewspaperBox/NewspaperBox.gltf','+X','Original BP_BaseBreakProps default NewspaperBox. +X facing is a browser placement convention inferred from protruding face, not verified original actor facing. Destruction behavior must be implemented separately.')]
    models=[]
    for id,kind,url,axis,note in definitions:
        _,bounds=mesh_data(PUBLIC/url.lstrip('/'));models.append({'id':id,'kind':kind,'url':url,'bounds':bounds,'forwardAxis':axis,'groundOffset':-bounds['min'][1],'notes':note})
    modelsById={m['id']:m for m in models};spawn=manifest['spawn'];cx=spawn[0];cz=spawn[2];routes=[];spawns=[];checks=[];radii={'citizen':.75,'sedan':2.6,'newspaper-box':.55}
    def valid(p,radius):
        if not(manifest['bounds']['min'][0]+radius<p[0]<manifest['bounds']['max'][0]-radius and manifest['bounds']['min'][2]+radius<p[2]<manifest['bounds']['max'][2]-radius):raise ValueError('Out of restored bounds')
        for b in boxes:
            if b['min'][0]-radius<=p[0]<=b['max'][0]+radius and b['min'][2]-radius<=p[2]<=b['max'][2]+radius:raise ValueError('Building footprint overlap '+b['id'])
    def place(id,modelId,x,z,length=0,direction=1):
        radius=radii[modelId];kind=modelsById[modelId]['kind'];routeId=None
        if length:
            points=[]
            for i in range(17):
                zz=z-length/2+length*i/16;p=[x,ground(cells,x,zz),zz];valid(p,radius);points.append(p)
            if direction<0:points.reverse()
            routeId=id+'-patrol';routes.append({'id':routeId,'kind':'vehicle' if kind=='vehicle' else 'citizen','points':points,'closed':False,'provenance':'Browser new design: short independent street-parallel patrol on original restored road triangles. Not an original AI route and not a connection between original spline components.'});position=points[0]
        else:position=[x,ground(cells,x,z),z];valid(position,radius)
        for previous in spawns:
            clearance=math.hypot(position[0]-previous['position'][0],position[2]-previous['position'][2])-radius-radii[previous['modelId']]
            if clearance<.4:raise ValueError('Spawn overlap '+id+' / '+previous['id'])
        # Logical heading uses +Z; runtime applies model.forwardAxis exactly once.
        yaw=0 if direction>0 else math.pi
        obj={'id':id,'modelId':modelId,'position':position,'yaw':yaw}
        if routeId:obj['routeId']=routeId
        spawns.append(obj);checks.append({'id':id,'groundY':position[1],'radiusMeters':radius,'distanceToPlayerSpawn':math.hypot(position[0]-spawn[0],position[2]-spawn[2]),'buildingFootprintClear':True})
    for side in [-1,1]:
        for i,zoffset in enumerate([-28,-20,-12,-4]):place(f'citizen-{side}-{i}','citizen',cx+side*9,cz+zoffset,3,1 if side<0 else -1)
    for i,zoffset in enumerate([-28,-16,-4]):place('vehicle-'+str(i),'sedan',cx+(-3 if i%2==0 else 3),cz+zoffset,6,1 if i%2==0 else -1)
    for i,(side,zoffset) in enumerate([(-1,-.5),(1,-10),(-1,-22)]):place('prop-'+str(i),'newspaper-box',cx+side*11,cz+zoffset)
    routeMap={r['id']:r for r in routes};corridors=[];minimumSeparation=math.inf
    for s in spawns:
        points=routeMap[s['routeId']]['points'] if 'routeId' in s else [s['position']];c={'id':s['id'],'x':points[0][0],'zmin':min(p[2] for p in points),'zmax':max(p[2] for p in points),'radius':radii[s['modelId']]}
        assert all(abs(p[0]-c['x'])<1e-9 for p in points)
        for b in boxes:
            if b['min'][0]-c['radius']<=c['x']<=b['max'][0]+c['radius'] and not(c['zmax']<b['min'][2]-c['radius'] or c['zmin']>b['max'][2]+c['radius']):raise ValueError('Continuous route intersects building '+s['id'])
        for prev in corridors:
            dz=max(0,c['zmin']-prev['zmax'],prev['zmin']-c['zmax']);clearance=math.hypot(c['x']-prev['x'],dz)-c['radius']-prev['radius'];minimumSeparation=min(minimumSeparation,clearance)
            if clearance<.4:raise ValueError('Patrol corridors overlap '+c['id']+'/'+prev['id'])
        corridors.append(c)
    output={'coordinateSystem':manifest['coordinateSystem'],'originUE':manifest['originUE'],'models':models,'routes':routes,'spawns':spawns,'notes':['All models are original local exports; current population spawns and patrols are newly designed for this browser prototype, not original AI data.','Spawn position Y is foot/tire/prop bottom surface. Add model.groundOffset to the imported model root Y. Yaw is logical heading in radians around Y with +Z forward; runtime must compensate model.forwardAxis once.','Citizens patrol street-edge strips on actual original roadway surfaces near spawn. These are not claimed to be original sidewalks.','Open routes should reverse at endpoints; no implied closed loop or connection.']}
    city.write(PUBLIC/'assets/population-manifest.json',output)
    resourceChecks=[]
    for model in models:
        p=PUBLIC/model['url'].lstrip('/');d=city.read(p);missing=[x['uri'] for x in d.get('buffers',[])+d.get('images',[]) if not(p.parent/x['uri']).exists()]
        if missing:raise ValueError('Missing resource '+str(missing))
        resourceChecks.append({'id':model['id'],'missing':missing})
    city.write(ROOT/'research/evidence/population-placement.json',{'breakableProp':breakProof,'checks':checks,'spawnCount':len(spawns),'routeCount':len(routes),'groundMethod':'Highest triangle intersection from original restored road/floor geometry; no invented flat ground.','collisionMethod':'Continuous XZ patrol intervals reject building AABBs expanded by model radius. All spawn/patrol corridors have at least 0.4m additional pairwise separation.','minimumCorridorSeparationMeters':minimumSeparation,'resourceChecks':resourceChecks,'placementScope':'New browser design near player spawn on existing original geometry; not original NPC/vehicle spawn logic.','modelSha256':{m['id']:hashlib.sha256((PUBLIC/m['url'].lstrip('/')).read_bytes()).hexdigest() for m in models}})
    print(json.dumps({'models':models,'spawnCount':len(spawns),'routeCount':len(routes),'maximumSpawnDistance':max(c['distanceToPlayerSpawn'] for c in checks)},indent=2))

if __name__=='__main__':main()
