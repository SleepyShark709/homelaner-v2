"""Recover ResidentialArea1 from cooked map component transforms and original meshes.
Uses only the installed read-only pak plus local portable tools; stdlib Python.
"""
import argparse, collections, hashlib, json, math, pathlib, re, shutil, struct, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=ROOT/'research/exports'
UNPACK=WORK/'unpacked'
DECODE=WORK/'city-decoded'
OUTPUT=ROOT/'public/assets/city'
RAW=WORK/'city-meshes'
TOOLS=ROOT/'tools/asset-pipeline'
PAK=pathlib.Path(r'E:\SteamLibrary\steamapps\common\UNDEFEATED\UNDEFEATED\Content\Paks\UNDEFEATED-WindowsNoEditor.pak')
ORIGIN=[-10000.,-55000.,0.]
RECT=(-32000,15000,-70000,-42000)

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def simplify(x):
    if isinstance(x,list):
        if len(x)==1 and isinstance(x[0],dict) and 'Value' in x[0]:return simplify(x[0]['Value'])
        if all(isinstance(a,dict) and 'Name' in a for a in x):return {a['Name']:simplify(a.get('Value',a)) for a in x}
        return [simplify(a) for a in x]
    if isinstance(x,dict):return {k:simplify(v) for k,v in x.items() if k not in ['$type','Name','DuplicationIndex']}
    return x
def vec(v,default=(0,0,0)):return [float(v.get(k,default[i])) for i,k in enumerate('XYZ')] if isinstance(v,dict) else list(default)
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,k):return [x*k for x in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(v):return math.sqrt(dot(v,v))
def unit(v):return mul(v,1/max(norm(v),1e-15))
def qmul(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return [w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z]
def qrotate(q,v):return qmul(qmul(q,v+[0]),[-q[0],-q[1],-q[2],q[3]])[:3]
def rotator(v):
    # UE FRotator::Quaternion: yaw about +Z, pitch about -Y, roll about -X.
    p,y,r=[math.radians(float(v.get(k,0)))/2 for k in ['Pitch','Yaw','Roll']]
    return qmul(qmul([0,0,math.sin(y),math.cos(y)],[0,-math.sin(p),0,math.cos(p)]),[-math.sin(r),0,0,math.cos(r)])
def glpos(p):return [(p[0]-ORIGIN[0])*.01,(p[2]-ORIGIN[2])*.01,(p[1]-ORIGIN[1])*.01]
def glrot(q):return [-q[0],-q[2],-q[1],q[3]]
def glscale(s):return [s[0],s[2],s[1]]

def prepare_levels():
    """Decode only the required two maps; cached decoded JSON is deterministic input."""
    folder=WORK/'city-unpacked'
    names=['-HeroGame/Maps/MainLevel','-HeroGame/Maps/SubLevel/ResidentialArea1']
    inventory=set((ROOT/'research/evidence/pak-files.txt').read_text().splitlines())
    wanted=[]
    for name in names:
        for ext in ['.umap','.uexp','.ubulk']:
            path='UNDEFEATED/Content/'+name+ext
            if path in inventory and not (folder/path).exists():wanted.append(path)
    if wanted:
        cmd=[str(TOOLS/'bin/repak.exe'),'unpack',str(PAK),'-o',str(folder)]
        for path in wanted:cmd+=['-i',path]
        subprocess.run(cmd,check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    DECODE.mkdir(parents=True,exist_ok=True)
    for name in names:
        src=folder/('UNDEFEATED/Content/'+name+'.umap');dest=DECODE/(src.stem+'.json')
        if not dest.exists():
            startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
            subprocess.run([str(TOOLS/'uasset-net472/UAssetGUI.exe'),'tojson',str(src),str(dest),'VER_UE4_27'],check=True,capture_output=True,startupinfo=startup,timeout=120)

class Level:
    def __init__(self,name):
        self.levelName=name;self.data=read(DECODE/(name+'.json'));self.ex=self.data['Exports'];self.im=self.data['Imports'];self.cache={}
    def ref(self,i):return (self.ex[i-1] if i>0 else self.im[-i-1]) if i else {}
    def name(self,i):return self.ref(i).get('ObjectName','')
    def path(self,i):
        e=self.ref(i);return (self.path(e['OuterIndex'])+'/' if e.get('OuterIndex') else '')+e.get('ObjectName','')
    def props(self,i):return {x['Name']:simplify(x.get('Value',x)) for x in self.ref(i).get('Data',[])}
    def world(self,i):
        if i in self.cache:return self.cache[i]
        p=self.props(i);t=vec(p.get('RelativeLocation'));q=rotator(p.get('RelativeRotation',{}));s=vec(p.get('RelativeScale3D'),(1,1,1))
        parent=p.get('AttachParent',0)
        if parent>0:
            T,Q,S=self.world(parent);t=add(T,qrotate(Q,[x*y for x,y in zip(t,S)]));q=qmul(Q,q);s=[x*y for x,y in zip(s,S)]
        self.cache[i]=(t,q,s);return t,q,s
    def meshes(self):
        out=[]
        for i,e in enumerate(self.ex,1):
            cls=self.name(e['ClassIndex'])
            if cls not in ['StaticMeshComponent','SplineMeshComponent']:continue
            p=self.props(i);mi=p.get('StaticMesh',0)
            if mi>=0:continue
            path=self.path(mi).rsplit('/',1)[0]
            t,q,s=self.world(i)
            out.append({'index':i,'sourceActor':self.path(e['OuterIndex']),'sourceComponent':e['ObjectName'],'class':cls,'package':path,'positionUE':t,'rotationUE':q,'scaleUE':s,'properties':p})
        return out

def extract(packages):
    inventory=(ROOT/'research/evidence/pak-files.txt').read_text().splitlines();wanted=set()
    for pkg in packages:
        base='UNDEFEATED/Content/'+pkg.removeprefix('/Game/')
        for ext in ['.uasset','.uexp','.ubulk']:
            if base+ext in inventory and not (UNPACK/(base+ext)).exists():wanted.add(base+ext)
    if wanted:
        cmd=[str(TOOLS/'bin/repak.exe'),'unpack',str(PAK),'-o',str(UNPACK)]
        for p in sorted(wanted):cmd+=['-i',p]
        subprocess.run(cmd,check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)

def export_mesh(pkg):
    target=RAW/pkg.removeprefix('/Game/')
    if target.with_suffix('.gltf').exists():return target.with_suffix('.gltf')
    extract([pkg]);exe=TOOLS/'umodel.exe'
    for attempt in range(6):
        p=subprocess.run([str(exe),'-export','-game=ue4.27','-gltf','-png','-path='+(UNPACK/'UNDEFEATED/Content').as_posix(),'-out='+RAW.as_posix(),pkg.rsplit('/',1)[1]],cwd=TOOLS,capture_output=True,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(p.stdout+p.stderr).decode(errors='replace')
        (ROOT/('research/evidence/city-layout-export-'+target.name+'.log')).write_text(log)
        missing=set(re.findall(r'package (/Game/[^\r\n]+?) was not found',log))
        if not missing:
            if not target.with_suffix('.gltf').exists():raise RuntimeError(log[-1500:])
            return target.with_suffix('.gltf')
        extract(missing)
    raise RuntimeError('Unresolved dependencies '+pkg)

def publish_mesh(source,kind):
    d=read(source);id=source.stem;dest=OUTPUT/'meshes'/id;dest.mkdir(parents=True,exist_ok=True)
    for b in d['buffers']:shutil.copy2(source.parent/b['uri'],dest/b['uri'])
    pngs={p.stem.lower():p for p in RAW.rglob('*.png')};mats={p.stem:p for p in RAW.rglob('*.mat')};props={p.name.removesuffix('.props.txt'):p for p in RAW.rglob('*.props.txt')}
    d.pop('images',None);d.pop('textures',None);cache={}
    for mat in d['materials']:
        n=mat['name'];pbr=mat['pbrMetallicRoughness']={'baseColorFactor':[.6,.6,.6,1],'metallicFactor':0,'roughnessFactor':.8};diff=None
        if n in mats:
            m=re.search(r'^Diffuse=(.+)$',mats[n].read_text(),re.M)
            if m and not any(s in m[1].lower() for s in ['height','mask','alpha','metalic','gradient','windowgrime']):diff=m[1].strip()
        if 'Red_Brick' in n:diff='T_Red_Brick'
        if 'PolishedConcrete' in n:diff='T_Polished_Concrete'
        if 'Generic_Color' in n:diff=None
        if n in props:
            m=re.search(r'Name=Color\s*\}.*?ParameterValue = \{ R=([\d.e-]+), G=([\d.e-]+), B=([\d.e-]+), A=([\d.e-]+)',props[n].read_text(),re.S)
            if m:pbr['baseColorFactor']=list(map(float,m.groups()))
        if 'Glass' in n:pbr.update(baseColorFactor=[.06,.10,.14,1],metallicFactor=.15,roughnessFactor=.25)
        if 'Road' in n and not diff:pbr['baseColorFactor']=[.12,.13,.14,1]
        if diff and diff.lower() in pngs:
            if diff not in cache:
                tex=pngs[diff.lower()];(OUTPUT/'textures').mkdir(exist_ok=True);shutil.copy2(tex,OUTPUT/'textures'/tex.name)
                (dest/'textures').mkdir(exist_ok=True);shutil.copy2(tex,dest/'textures'/tex.name)
                j=len(d.setdefault('images',[]));d['images'].append({'uri':'textures/'+tex.name});d.setdefault('textures',[]).append({'source':j});cache[diff]=j
            pbr['baseColorTexture']={'index':cache[diff]}
        mat['alphaMode']='MASK' if n=='RoadDecals_Inst' else 'OPAQUE'
        if n=='RoadDecals_Inst':mat['alphaCutoff']=0.3333
    compact_mesh(d,dest)
    write(dest/(id+'.gltf'),d)
    mins=[float('inf')]*3;maxs=[-float('inf')]*3
    for mesh in d['meshes']:
        for pr in mesh['primitives']:
            a=d['accessors'][pr['attributes']['POSITION']]
            for j in range(3):mins[j]=min(mins[j],a['min'][j]);maxs[j]=max(maxs[j],a['max'][j])
    return {'id':id,'url':'/assets/city/meshes/'+id+'/'+id+'.gltf','kind':kind,'bounds':{'min':mins,'max':maxs}}

def accessor(d,bs,i):
    a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];f={5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']];stride=v.get('byteStride',struct.calcsize(f)*n);off=v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from('<'+f*n,bs[v['buffer']],off+j*stride) for j in range(a['count'])]

def compact_mesh(d,folder):
    """Merge equal-material primitives inside a mesh; retain triangle/attribute values."""
    bs=[(folder/b['uri']).read_bytes() for b in d['buffers']];unique=[];remap={};keys={}
    for i,m in enumerate(d['materials']):
        key=json.dumps(m,sort_keys=True)
        if key not in keys:keys[key]=len(unique);unique.append(m)
        remap[i]=keys[key]
    data=bytearray();views=[];accessors=[];meshes=[]
    def store(values,n,typ,isindex=False):
        start=len(data);f='I' if isindex else 'f'
        for v in values:data.extend(struct.pack('<'+f*n,*(v if isinstance(v,(list,tuple)) else [v])))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(data)-start});a={'bufferView':len(views)-1,'componentType':5125 if isindex else 5126,'count':len(values),'type':typ}
        if typ=='VEC3':a.update(min=[min(v[j] for v in values) for j in range(n)],max=[max(v[j] for v in values) for j in range(n)])
        accessors.append(a);return len(accessors)-1
    for mesh in d['meshes']:
        groups={}
        for p in mesh['primitives']:
            key=(remap[p['material']],tuple(sorted(p['attributes'])))
            if key not in groups:groups[key]={'attrs':{k:[] for k in p['attributes']},'indices':[],'types':{}}
            group=groups[key];base=len(group['attrs']['POSITION'])
            for k,ai in p['attributes'].items():
                a=d['accessors'][ai];values=accessor(d,bs,ai)
                if a.get('normalized') and a['componentType']!=5126:
                    divisor={5121:255,5123:65535}[a['componentType']];values=[tuple(v/divisor for v in row) for row in values]
                group['attrs'][k]+=values;group['types'][k]=a['type']
            group['indices'] += [row[0]+base for row in accessor(d,bs,p['indices'])]
        primitives=[]
        for (mi,_),g in groups.items():
            attrs={k:store(v,len(v[0]),g['types'][k]) for k,v in g['attrs'].items()};primitives.append({'attributes':attrs,'indices':store(g['indices'],1,'SCALAR',True),'material':mi})
        meshes.append({'primitives':primitives})
    d.update(materials=unique,meshes=meshes,accessors=accessors,bufferViews=views,buffers=[{'uri':'mesh.bin','byteLength':len(data)}]);(folder/'mesh.bin').write_bytes(data)

def bake_splines(rows):
    """Bake original source vertices using recorded cubic Hermite spline slices.
    Current map uses ForwardAxis X and default Z up. Reject explicit alternatives.
    """
    groups={};materials=[];images=[];textures=[];matindex={};sources=[];cache={};midpoints=[]
    def unwrap(v):
        while isinstance(v,dict) and len(v)==1:v=next(iter(v.values()))
        return v
    def v2(v,default):v=unwrap(v);return [float(v.get(k,default[i])) for i,k in enumerate('XY')] if isinstance(v,dict) else list(default)
    for row in rows:
        props=row['properties'];params=props['SplineParams'];name=row['package'].rsplit('/',1)[1]
        if any(k in props for k in ['ForwardAxis','SplineUpDir','SplineBoundaryMin','SplineBoundaryMax']):raise ValueError('Nondefault spline convention '+row['sourceComponent'])
        if name not in cache:
            path=OUTPUT/'meshes'/name/(name+'.gltf');d=read(path);bs=[(path.parent/b['uri']).read_bytes() for b in d['buffers']]
            bounds=[d['accessors'][p['attributes']['POSITION']] for m in d['meshes'] for p in m['primitives']]
            xs=[a['min'][0] for a in bounds];xe=[a['max'][0] for a in bounds]
            cache[name]=(d,bs,min(xs)*100,max(xe)*100)
        d,bs,xmin,xmax=cache[name]
        p0,p1,t0,t1=[vec(params.get(k)) for k in ['StartPos','EndPos','StartTangent','EndTangent']]
        s0,s1=[v2(params.get(k),[1,1]) for k in ['StartScale','EndScale']];o0,o1=[v2(params.get(k),[0,0]) for k in ['StartOffset','EndOffset']]
        r0,r1=[float(params.get(k,0)) for k in ['StartRoll','EndRoll']]
        def sample(a):
            a2=a*a;a3=a2*a
            c=[(2*a3-3*a2+1)*p0[j]+(a3-2*a2+a)*t0[j]+(-2*a3+3*a2)*p1[j]+(a3-a2)*t1[j] for j in range(3)]
            tangent=unit([(6*a2-6*a)*p0[j]+(3*a2-4*a+1)*t0[j]+(-6*a2+6*a)*p1[j]+(3*a2-2*a)*t1[j] for j in range(3)])
            bx=unit(cross([0,0,1],tangent));by=unit(cross(tangent,bx));roll=r0+(r1-r0)*a
            xx=add(mul(bx,math.cos(roll)),mul(by,-math.sin(roll)));yy=add(mul(by,math.cos(roll)),mul(bx,math.sin(roll)))
            scale=[s0[j]+(s1[j]-s0[j])*a for j in range(2)];offset=[o0[j]+(o1[j]-o0[j])*a for j in range(2)]
            return add(c,add(mul(xx,offset[0]),mul(yy,offset[1]))),tangent,xx,yy,scale
        worldt,worldq,worlds=row['positionUE'],row['rotationUE'],row['scaleUE']
        def world(v):return add(worldt,qrotate(worldq,[v[j]*worlds[j] for j in range(3)]))
        if name.startswith('Road_'):midpoints.append({'point':glpos(world(sample(.5)[0])),'sourceComponent':row['sourceComponent']})
        for prim in d['meshes'][0]['primitives']:
            mi=prim['material'];mat=d['materials'][mi];key=json.dumps(mat,sort_keys=True)
            if key not in matindex:
                mat=json.loads(key);pbr=mat['pbrMetallicRoughness']
                if 'baseColorTexture' in pbr:
                    tex=d['textures'][pbr['baseColorTexture']['index']];im=dict(d['images'][tex['source']]);images.append(im);textures.append({'source':len(images)-1});pbr['baseColorTexture']['index']=len(textures)-1
                matindex[key]=len(materials);materials.append(mat);groups[key]={'positions':[],'normals':[],'uvs':[],'indices':[]}
            g=groups[key];base=len(g['positions']);positions=accessor(d,bs,prim['attributes']['POSITION']);normals=accessor(d,bs,prim['attributes']['NORMAL']);uvs=accessor(d,bs,prim['attributes']['TEXCOORD_0'])
            for pos,n in zip(positions,normals):
                x,z,y=[v*100 for v in pos];a=(x-xmin)/(xmax-xmin);c,t,xx,yy,scale=sample(a)
                local=add(c,add(mul(xx,y*scale[0]),mul(yy,z*scale[1])));g['positions'].append(glpos(world(local)))
                normal=unit(qrotate(worldq,add(mul(t,n[0]),add(mul(xx,n[2]/max(abs(scale[0]),1e-9)),mul(yy,n[1]/max(abs(scale[1]),1e-9))))));g['normals'].append([normal[0],normal[2],normal[1]])
            g['uvs']+=uvs;g['indices'] += [v[0]+base for v in accessor(d,bs,prim['indices'])]
        sources.append({'sourceActor':row['sourceActor'],'sourceComponent':row['sourceComponent'],'sourceExportIndex':row['index'],'package':row['package']})
    binary=bytearray();views=[];accessors=[];primitives=[]
    def put(values,f,n,typ,bounds=False):
        while len(binary)%4:binary.append(0)
        start=len(binary)
        for v in values:binary.extend(struct.pack('<'+f*n,*(v if isinstance(v,(list,tuple)) else [v])))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start});a={'bufferView':len(views)-1,'componentType':5126 if f=='f' else 5125,'count':len(values),'type':typ}
        if bounds:a.update(min=[min(v[j] for v in values) for j in range(n)],max=[max(v[j] for v in values) for j in range(n)])
        accessors.append(a);return len(accessors)-1
    for key,g in groups.items():
        attrs={'POSITION':put(g['positions'],'f',3,'VEC3',True),'NORMAL':put(g['normals'],'f',3,'VEC3'),'TEXCOORD_0':put(g['uvs'],'f',2,'VEC2')};primitives.append({'attributes':attrs,'indices':put(g['indices'],'I',1,'SCALAR'),'material':matindex[key]})
    doc={'asset':{'version':'2.0','generator':'Original map spline reconstruction; original UModel mesh vertices deformed by decoded SplineParams'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0,'name':'OriginalResidentialRoads'}],'meshes':[{'primitives':primitives}],'materials':materials,'images':images,'textures':textures,'buffers':[{'uri':'roads.bin','byteLength':len(binary)}],'bufferViews':views,'accessors':accessors}
    write(OUTPUT/'roads.gltf',doc);(OUTPUT/'roads.bin').write_bytes(binary)
    write(ROOT/'research/evidence/city-layout-spline-bake.json',{'count':len(sources),'sources':sources,'triangles':sum(len(g['indices'])//3 for g in groups.values()),'materialGroups':len(groups),'midpoints':midpoints,'method':'Original source vertex x normalized to mesh bounds -> cubic Hermite StartPos/EndPos/tangents; interpolated slice scale/roll/offset; transform full component parent chain; UE to glTF Y/Z exchange.'})
    return {'id':'original-roads','url':'/assets/city/roads.gltf','kind':'road'}, {'id':'original-roads','assetId':'original-roads','position':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1],'sourceActor':'MainLevel/PersistentLevel/Landscape_2','sourceComponents':[s['sourceComponent'] for s in sources]},midpoints

def main():
    prepare_levels()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    res=Level('ResidentialArea1');main=Level('MainLevel');rrows=res.meshes();mrows=main.meshes()
    selected=[r for r in rrows if ('/SM_MERGED_Apartment_' in r['package'] or '/SM_MERGED_Ornate_Floor_' in r['package'] or '/SM_Floor12000x15000' in r['package'])]
    nearby=[r for r in mrows if RECT[0]<r['positionUE'][0]<RECT[1] and RECT[2]<r['positionUE'][1]<RECT[3]]
    selected += [r for r in nearby if r['class']=='StaticMeshComponent' and '/RoadProps/' in r['package']]
    splines=[r for r in nearby if r['class']=='SplineMeshComponent']
    evidence={'sourceLevels':['MainLevel','ResidentialArea1'],'originUE':ORIGIN,'selectedStatic':selected,'nearbySplines':splines,'coordinateTransform':'UE position [x,z,y]/100; quaternion [-qx,-qz,-qy,qw]; source UModel ExportGLTF TransformPosition swaps Y/Z. Map quaternion uses reflection basis C R C^-1.'}
    write(ROOT/'research/evidence/city-layout-source.json',evidence)
    assets=[];objects=[]
    packages=sorted(set(r['package'] for r in selected+splines))
    for pkg in packages:
        kind='building' if '/SM_MERGED_Apartment_' in pkg else 'road'
        print('Export',pkg,flush=True);assets.append(publish_mesh(export_mesh(pkg),kind))
    for k,r in enumerate(selected):
        objects.append({'id':'static-'+str(k),'assetId':r['package'].rsplit('/',1)[1],'position':glpos(r['positionUE']),'rotation':glrot(r['rotationUE']),'scale':glscale(r['scaleUE']),'sourceActor':r['sourceActor'],'sourceComponent':r['sourceComponent'],'sourceExportIndex':r['index']})
    roadasset,roadobject,midpoints=bake_splines(splines);assets.append(roadasset);objects.append(roadobject)
    used={o['assetId'] for o in objects};assets=[a for a in assets if a['id'] in used]
    chosen=min(midpoints,key=lambda p:p['point'][0]**2+p['point'][2]**2);spawn=list(chosen['point']);ground=spawn[1]+.0812;spawn[1]=ground+1.2
    manifest={'coordinateSystem':'gltf-rh-y-up-meters','originUE':ORIGIN,'spawn':spawn,'groundY':ground,'spawnEvidence':{'method':'Nearest original Road spline midpoint to origin, placed 1.2m above original road surface; not PlayerStart.','sourceComponent':chosen['sourceComponent']},'bounds':{'min':[-220,0,-150],'max':[250,140,130]},'assets':assets,'objects':objects,'notes':['恢复ResidentialArea1公寓和铺装真实坐标；211段道路/人行道按原SplineParams与原网格烘焙。','材质为原颜色贴图与简化PBR，不含原光照/反射/UE自定义材质。','spawn为最近原道路样条中心上方的计算安全点，不是原PlayerStart；未恢复外围地形、植被、所有街具。']}
    boxes=[];allpoints=[];assetmap={a['id']:a for a in assets}
    for o in objects:
        asset=assetmap[o['assetId']]
        if 'bounds' not in asset:continue
        lo,hi=asset['bounds']['min'],asset['bounds']['max'];points=[]
        for x in [lo[0],hi[0]]:
            for y in [lo[1],hi[1]]:
                for z in [lo[2],hi[2]]:points.append(add(o['position'],qrotate(o['rotation'],[v*s for v,s in zip([x,y,z],o['scale'])])))
        allpoints+=points
        if 'Floor' in asset['id']:boxes.append({'id':o['id'],'min':[min(p[j] for p in points) for j in range(3)],'max':[max(p[j] for p in points) for j in range(3)],'sourceActor':o['sourceActor'],'kind':'original-floor-surface'})
    manifest['collisionBoxes']=boxes
    manifest['restoredStaticBounds']={'min':[min(p[j] for p in allpoints) for j in range(3)],'max':[max(p[j] for p in allpoints) for j in range(3)]}
    roadsdoc=read(OUTPUT/'roads.gltf')
    for primitive in roadsdoc['meshes'][0]['primitives']:
        a=roadsdoc['accessors'][primitive['attributes']['POSITION']];allpoints.extend([a['min'],a['max']])
    manifest['bounds']={'min':[min(p[0] for p in allpoints),min(p[1] for p in allpoints),min(p[2] for p in allpoints)],'max':[max(p[0] for p in allpoints),140,max(p[2] for p in allpoints)]}
    write(OUTPUT/'manifest.json',manifest)
    checks=[]
    for p in OUTPUT.rglob('*.gltf'):
        d=read(p);missing=[]
        for entry in d.get('images',[])+d.get('buffers',[]):
            uri=entry.get('uri','');local=ROOT/'public'/uri.lstrip('/') if uri.startswith('/') else p.parent/uri
            if not local.is_file():missing.append(uri)
        checks.append({'file':p.relative_to(OUTPUT).as_posix(),'missingResources':missing})
    sourcefiles=[TOOLS/'umodel.exe',TOOLS/'bin/repak.exe',TOOLS/'bin/oo2core_9_win64.dll',TOOLS/'uasset-net472/UAssetGUI.exe']
    for name in ['MainLevel','SubLevel/ResidentialArea1']:
        for ext in ['.umap','.uexp']:
            p=WORK/('city-unpacked/UNDEFEATED/Content/-HeroGame/Maps/'+name+ext)
            if p.exists():sourcefiles.append(p)
    write(ROOT/'research/evidence/city-layout-validation.json',{'staticObjects':len(selected),'splineComponents':len(splines),'assets':len(assets),'resourceChecks':checks,'inputs':[{'file':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sourcefiles],'groundY':ground,'spawn':spawn,'staticBounds':manifest['restoredStaticBounds'],'coordinateChecks':{'UE_yaw_90_local_X_in_glTF':qrotate(glrot(rotator({'Yaw':90})),[1,0,0]),'expected':[0,0,1]},'scope':'Original actors/components, original source meshes, selected rectangular street block; not complete map or original UE rendering.'})
    print('Statics',len(objects),'spline candidates',len(splines),'assets',len(assets),flush=True)

if __name__=='__main__':main()
