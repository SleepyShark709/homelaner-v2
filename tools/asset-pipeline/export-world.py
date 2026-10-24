"""Recover cooked world geometry without clipping, guessed layout, or guessed materials.

Inputs: read-only source pak and static REA audit. All mutations are derived copies.
Geometry stays in glTF RH metres, UE coordinates [X,Z,Y]/100; world origin is zero.
No claim of runtime visibility, inherited Blueprint defaults, or complete migration.
"""
import argparse, base64, collections, concurrent.futures, copy, hashlib, importlib.util, json, math, os, pathlib, re, shutil, struct, subprocess, threading, time

ROOT=pathlib.Path(__file__).resolve().parents[2]
TOOLS=ROOT/'tools/asset-pipeline'; AUDIT=ROOT/'research/rea-audit'; EVID=ROOT/'research/world-recovery'
OUT=ROOT/'public/assets/world'; RAW=ROOT/'research/exports/world-meshes'; UNPACK=ROOT/'research/exports/world-unpacked'
PAK=pathlib.Path(r'E:\SteamLibrary\steamapps\common\UNDEFEATED\UNDEFEATED\Content\Paks\UNDEFEATED-WindowsNoEditor.pak')
spec=importlib.util.spec_from_file_location('worldaudit',AUDIT/'audit-world.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
m=a.mathmod
READ=a.read; WRITE=a.write; HASH=a.digest
INVENTORY=set((ROOT/'research/evidence/pak-files.txt').read_text(encoding='utf-8-sig').splitlines())
extract_lock=threading.Lock()

def assetid(pkg):return re.sub('[^A-Za-z0-9_-]','_',pkg.rsplit('/',1)[1])+'-'+hashlib.sha256(pkg.encode()).hexdigest()[:12]
def diskbase(pkg):return ('UNDEFEATED/Content/'+pkg[6:]) if pkg.startswith('/Game/') else ('Engine/Content/'+pkg[8:]) if pkg.startswith('/Engine/') else None
def package_ref(path):
    if not path:return None
    pkg,obj=path.rsplit('/',1)
    return {'package':pkg,'object':obj,'reference':pkg+'.'+obj}
def glpos(p):return [p[0]*.01,p[2]*.01,p[1]*.01]
def glrot(q):return [-q[0],-q[2],-q[1],q[3]]
def glscale(s):return [s[0],s[2],s[1]]
def transform(t):return {'position':glpos(t['position']),'rotation':glrot(t['rotationQuaternion']),'scale':glscale(t['scale'])}
def emptybounds():return {'min':[float('inf')]*3,'max':[-float('inf')]*3}
def expand(bounds,p):
    for j in range(3):bounds['min'][j]=min(bounds['min'][j],p[j]);bounds['max'][j]=max(bounds['max'][j],p[j])
def objectbounds(bounds,obj,local):
    for x in (local['min'][0],local['max'][0]):
        for y in (local['min'][1],local['max'][1]):
            for z in (local['min'][2],local['max'][2]):expand(bounds,m.add(obj['position'],m.qrotate(obj['rotation'],[v*s for v,s in zip([x,y,z],obj['scale'])])))
def hiddenrun(cmd,timeout=180):
    return subprocess.run([str(x) for x in cmd],capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW,cwd=TOOLS)

def extract(packages):
    with extract_lock:
        wanted=[]
        for pkg in packages:
            base=diskbase(pkg)
            if not base:continue
            for ext in ('.uasset','.uexp','.ubulk'):
                path=base+ext;dest=UNPACK/path
                if path not in INVENTORY or dest.exists():continue
                sources=[AUDIT/'extracted-world-assets'/path,ROOT/'research/exports/unpacked'/path,AUDIT/'extracted'/path]
                src=next((x for x in sources if x.exists()),None)
                if src:
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    try:os.link(src,dest)
                    except OSError:shutil.copy2(src,dest)
                else:wanted.append(path)
        for start in range(0,len(wanted),80):
            cmd=[TOOLS/'bin/repak.exe','unpack',PAK,'-o',UNPACK]
            for p in wanted[start:start+80]:cmd+=['-i',p]
            p=hiddenrun(cmd);p.check_returncode()

def findraw(pkg):
    rel=pkg.removeprefix('/Game/').removeprefix('/Engine/')+'.gltf'
    candidates=[RAW/rel,RAW/('Engine/'+rel)]
    return next((p for p in candidates if p.exists()),None)

def export_one(pkg):
    ident=assetid(pkg);logpath=EVID/'geometry-logs'/(ident+'.log')
    try:
        existing=findraw(pkg)
        if existing:return {'package':pkg,'raw':str(existing),'cached':True}
        # Reuse only raw UEViewer output whose complete original path matches, never city-published materials.
        rel=pkg.removeprefix('/Game/')+'.gltf'
        if pkg.startswith('/Game/'):
            for directory in ('city-meshes','hero','accessories','building','vehicle','citizen'):
                old=ROOT/'research/exports'/directory/rel
                if old.exists():
                    dest=RAW/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,dest)
                    for buf in READ(old).get('buffers',[]):shutil.copy2(old.parent/buf['uri'],dest.parent/buf['uri'])
                    return {'package':pkg,'raw':str(dest),'reusedRaw':str(old)}
        extract([pkg]);source=UNPACK/(diskbase(pkg)+'.uasset')
        if not source.exists():raise ValueError('Source package missing: '+str(source))
        logs=[]
        for attempt in range(8):
            p=hiddenrun([TOOLS/'umodel.exe','-export','-game=ue4.27','-gltf','-png','-noanim','-nolightmap','-nooverwrite','-path='+UNPACK.as_posix(),'-out='+RAW.as_posix(),source.as_posix()],180)
            log=(p.stdout+p.stderr).decode(errors='replace');logs.append(log)
            missing=set(re.findall(r'package (/(?:Game|Engine)/[^\r\n]+?) was not found',log))
            if missing:extract(missing)
            out=findraw(pkg)
            if out and not missing:break
            if not missing and not out:raise ValueError(log[-1800:])
        logpath.parent.mkdir(parents=True,exist_ok=True);logpath.write_text('\n'.join(logs),encoding='utf-8')
        out=findraw(pkg)
        if not out:raise ValueError('No glTF exported after dependency passes')
        return {'package':pkg,'raw':str(out),'log':str(logpath),'unresolvedDependencies':sorted(missing)}
    except Exception as e:return {'package':pkg,'error':str(e),'log':str(logpath)}

def native_skeletal_sections(blob,offset,names,slotcount):
    """UE4.27 cooked FReferenceSkeleton -> LOD0 FSkelMeshRenderSection; no fuzzy offsets."""
    start=offset
    def read(fmt):
        nonlocal offset
        v=struct.unpack_from('<'+fmt,blob,offset);offset+=struct.calcsize('<'+fmt)
        return v[0] if len(v)==1 else list(v)
    bones=read('i');assert 0<bones<4096
    for _ in range(bones):
        name,number,parent=read('iii');assert 0<=name<len(names) and number>=0 and -1<=parent<bones
    poses=read('i');assert poses==bones;offset+=poses*40
    lookup=read('i');assert lookup==bones
    for _ in range(lookup):
        name,number,index=read('iii');assert 0<=name<len(names) and number>=0 and 0<=index<bones
    skeleton_end=offset;cooked,lods=read('ii');assert cooked==1 and 0<lods<16
    flags=read('BB');cookedout,inlined=read('ii');assert flags[0]&1 and cookedout==0 and inlined in (0,1)
    required=read('i');assert 0<=required<=bones
    for _ in range(required):assert 0<=read('H')<bones
    count=read('i');assert 0<count<1024;sections=[]
    for section in range(count):
        section_start=offset;flags=read('BB');material=read('h');first,tris,recompute=read('iii');mask=read('B');shadow,vertexbase=read('iI')
        assert flags[0]&1 and 0<=material<slotcount and first>=0 and tris>=0 and recompute in (0,1) and shadow in (0,1) and mask<=4
        # These restored meshes have no cloth mappings. Stop rather than guess other layouts.
        cloth_count=read('i');assert cloth_count==0,'Cloth mapping payload is outside the bounded decoder'
        bonemap_count=read('i');assert 0<=bonemap_count<=bones
        for _ in range(bonemap_count):assert 0<=read('H')<bones
        vertices,influences=read('ii');cloth_asset=read('h');offset+=20 # FClothingSectionData: Guid16 + AssetLodIndex4
        assert vertices>=0 and 0<=influences<=12 and cloth_asset>=-1
        if not flags[1]&1:
            duplicate_count=read('i');assert 0<=duplicate_count<10000000;offset+=duplicate_count*4
            duplicate_index_count=read('i');assert 0<=duplicate_index_count<=vertices;offset+=duplicate_index_count*8
        disabled=read('i');assert disabled in (0,1) and offset<=len(blob)
        sections.append({'sectionIndex':section,'materialSlotIndex':material,'firstIndex':first,'numTriangles':tris,'baseVertexIndex':vertexbase,'numVertices':vertices,'castShadow':bool(shadow),'disabled':bool(disabled),'nativeOffset':section_start,'nativeEndOffset':offset})
    return sections,{'referenceSkeletonOffset':start,'referenceSkeletonEndOffset':skeleton_end,'referenceBoneCount':bones,'lodCount':lods,'requiredBoneCount':required,'sectionArrayEndOffset':offset,'schema':'UE4.27 cooked FReferenceSkeleton, FSkeletalMeshLODRenderData, FSkelMeshRenderSection; cloth-free sections only'}

def materialslots(pkg):
    base=diskbase(pkg);file=AUDIT/'decoded-world-assets'/(base+'.json')
    if not file.exists():
        file=EVID/'geometry-decoded-meshes'/(base+'.json');file.parent.mkdir(parents=True,exist_ok=True)
        if not file.exists():
            extract([pkg]);source=UNPACK/(base+'.uasset')
            p=hiddenrun([TOOLS/'uasset-net472/UAssetGUI.exe','tojson',source,file,'VER_UE4_27'])
            if p.returncode or not file.exists():return [],{'error':'No decoded mesh material slots'}
    d=READ(file);p=a.Package(d,pkg.rsplit('/',1)[1]);slots=[];evidence={'decoded':str(file),'sha256':HASH(file)}
    for i,e in enumerate(p.ex,1):
        if p.cls(i) not in ('StaticMesh','SkeletalMesh'):continue
        prop=next((x for x in e.get('Data',[]) if x['Name'] in ('StaticMaterials','Materials')),None)
        raw=prop.get('Value',[]) if prop else []
        for slot,element in enumerate(raw):
            # Array struct elements may all have the same Name; do not collapse them into a dict.
            v=m.simplify(element.get('Value',element)) if isinstance(element,dict) else element
            if isinstance(v,dict) and len(v)==1 and isinstance(next(iter(v.values())),dict):v=next(iter(v.values()))
            ref=v.get('MaterialInterface',0) if isinstance(v,dict) else v
            slots.append({'slotIndex':slot,'slotName':v.get('MaterialSlotName') if isinstance(v,dict) else None,'material':package_ref(p.path(ref)) if isinstance(ref,int) and ref else None})
        blob=base64.b64decode(e.get('Extras',{}).get('$value',''))
        try:
            if p.cls(i)=='SkeletalMesh' and not slots:
                # Cooked UE4.27 native prefix, strip flags, FBoxSphereBounds, FSkeletalMaterial[].
                assert blob[:6]==b'\0\0\0\0\1\0';count=struct.unpack_from('<i',blob,34)[0];assert 0<count<1024;off=38
                for slot in range(count):
                    ref,nameindex,number,hasimport=struct.unpack_from('<4i',blob,off);off+=16
                    assert -len(p.im)<=ref<=len(p.ex) and 0<=nameindex<len(d['NameMap']) and hasimport in (0,1)
                    slotname=d['NameMap'][nameindex]+('_'+str(number-1) if number else '')
                    if hasimport:off+=8
                    initialized,override=struct.unpack_from('<2i',blob,off);assert initialized in (0,1) and override in (0,1);off+=24
                    slots.append({'slotIndex':slot,'slotName':slotname,'material':package_ref(p.path(ref)) if ref else None})
                evidence['nativeSkeletalMaterialArray']={'count':count,'offsetInExtras':34,'endOffsetInExtras':off,'schema':'UE4.27 FSkeletalMaterial with stripped imported names and FMeshUVChannelInfo','extrasSha256':hashlib.sha256(blob).hexdigest()}
                sections,section_evidence=native_skeletal_sections(blob,off,d['NameMap'],len(slots))
                evidence['nativeLod0Sections']=sections;evidence['nativeSkeletalSectionEvidence']=section_evidence
            if p.cls(i)=='StaticMesh':
                assert blob[:6]==b'\0\0\0\0\1\0';cooked=struct.unpack_from('<i',blob,6)[0];assert cooked==1
                sockets=struct.unpack_from('<i',blob,34)[0];assert 0<=sockets<1024;off=38+sockets*4
                lodcount=struct.unpack_from('<i',blob,off)[0];off+=4;assert 1<=lodcount<=16
                strip=list(blob[off:off+2]);off+=2;assert strip[0]&1
                count=struct.unpack_from('<i',blob,off)[0];off+=4;assert 0<count<4096;sections=[]
                for section in range(count):
                    vals=struct.unpack_from('<9i',blob,off);assert 0<=vals[0]<len(slots) and vals[1]>=0 and vals[2]>=0 and all(v in (0,1) for v in vals[5:]);off+=36
                    sections.append({'sectionIndex':section,'materialSlotIndex':vals[0],'firstIndex':vals[1],'numTriangles':vals[2],'minVertexIndex':vals[3],'maxVertexIndex':vals[4],'collision':bool(vals[5]),'castShadow':bool(vals[6]),'forceOpaque':bool(vals[7]),'visibleInRayTracing':bool(vals[8])})
                evidence['nativeLod0Sections']=sections;evidence['nativeLod0SectionArrayEndOffset']=off;evidence['nativeExtrasSha256']=hashlib.sha256(blob).hexdigest()
        except Exception as error:evidence['nativeDecodeError']=str(error) or type(error).__name__
    return slots,evidence

def publish(result):
    pkg=result['package'];raw=pathlib.Path(result['raw']);ident=assetid(pkg);dest=OUT/'meshes'/ident;dest.mkdir(parents=True,exist_ok=True)
    d=READ(raw);slots,evidence=materialslots(pkg)
    # UEViewer emits a diagnostic palette. Remove it; original materials are resolved separately.
    mappings=[]
    native=evidence.get('nativeLod0Sections',[]);primitives=[pr for mesh in d.get('meshes',[]) for pr in mesh['primitives']]
    nativeValid=len(native)==len(primitives) and all(d['accessors'][pr['indices']]['count']==section['numTriangles']*3 for pr,section in zip(primitives,native))
    for i,mat in enumerate(d.get('materials',[])):
        name=mat.get('name','');matches=[native[i]['materialSlotIndex']] if nativeValid else [s['slotIndex'] for s in slots if s['material'] and s['material']['object'].casefold()==name.casefold()]
        refs=[slots[j]['material'] for j in matches];sourceMaterial=refs[0] if refs and all(r==refs[0] for r in refs) else None
        mappings.append({'materialIndex':i,'name':name,'sourceSlotCandidates':matches,'sourceMaterial':sourceMaterial,'mappingEvidence':'native-LOD0-MaterialIndex-and-triangle-count-match' if nativeValid else 'FName-case-insensitive-original-slot-match'})
        mat.clear();mat.update(name=name,pbrMetallicRoughness={'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':1},extras={'sourceSlotCandidates':matches,'sourceMaterial':sourceMaterial,'materialRecoveryStatus':'pending-original-material-conversion'})
    d.pop('images',None);d.pop('textures',None);d.pop('samplers',None)
    for b in d.get('buffers',[]):
        if '/' in b['uri'] or '\\' in b['uri']:raise ValueError('Unexpected raw buffer path')
        shutil.copy2(raw.parent/b['uri'],dest/b['uri'])
    d.setdefault('extras',{}).update(sourcePackage=pkg,sourceMaterialSlots=slots,sourceRawSha256=HASH(raw))
    WRITE(dest/'mesh.gltf',d)
    stats,bounds=validate_gltf(dest/'mesh.gltf')
    return {'id':ident,'url':'/assets/world/meshes/'+ident+'/mesh.gltf','sourcePackage':pkg,'sourceMaterialSlots':slots,'gltfMaterials':mappings,'bounds':bounds,'geometryStats':stats,'materialSlotEvidence':evidence,'raw':str(raw),'rawSha256':HASH(raw),'sha256':HASH(dest/'mesh.gltf')}

def validate_gltf(path):
    d=READ(path);bs=[(path.parent/b['uri']).read_bytes() for b in d.get('buffers',[])];bounds=emptybounds();tri=0;prims=0;vertices=0
    for i,b in enumerate(d.get('buffers',[])):
        if len(bs[i])<b['byteLength']:raise ValueError('Truncated buffer')
    for mesh in d.get('meshes',[]):
        for p in mesh['primitives']:
            aa=d['accessors'][p['attributes']['POSITION']];positions=m.accessor(d,bs,p['attributes']['POSITION']);indices=m.accessor(d,bs,p['indices'])
            if any(not math.isfinite(v) for row in positions for v in row):raise ValueError('Nonfinite vertex')
            if any(x[0]>=len(positions) for x in indices):raise ValueError('Index outside vertex range')
            if p.get('material',0)>=len(d.get('materials',[])):raise ValueError('Invalid material index')
            for point in (aa['min'],aa['max']):expand(bounds,point)
            tri+=len(indices)//3;vertices+=len(positions);prims+=1
    return {'triangles':tri,'verticesAcrossPrimitives':vertices,'primitives':prims,'meshes':len(d.get('meshes',[])),'skins':len(d.get('skins',[]))},bounds

def unwrap(v):
    while isinstance(v,dict) and len(v)==1:v=next(iter(v.values()))
    return v
def vec2(v,default):
    v=unwrap(v);return [float(v.get(k,default[i])) for i,k in enumerate('XY')] if isinstance(v,dict) else default

def decode_instances(blob):
    """UE4.27 cooked SMC LODData -> ISM bulk FMatrix -> custom data -> cooked render payload.

    Verified against primary CUE4Parse serializers saved beside geometry evidence.
    Accept only this observed cooked schema; reject unknown flags/counts rather than search bytes.
    """
    off=0
    def integer():
        nonlocal off
        result=struct.unpack_from('<i',blob,off)[0];off+=4;return result
    if integer()!=0:raise ValueError('Unexpected UObject native prefix')
    lods=integer()
    if not 0<=lods<=16:raise ValueError('Invalid component LOD count')
    for lod in range(lods):
        general,cls=blob[off:off+2];off+=2
        if general!=1 or cls!=1:raise ValueError('Unsupported LOD strip/color flags')
        off+=16 # MapBuildDataId, editor and override colors stripped.
    cooked=integer()
    if cooked!=1:raise ValueError('Uncooked ISM variant')
    size=integer();count=integer();matrixoffset=off
    if size!=64 or not 0<count<100000:raise ValueError('Invalid FMatrix bulk header')
    matrices=[]
    for i in range(count):
        matrix=list(struct.unpack_from('<16f',blob,off));off+=64
        if any(not math.isfinite(x) for x in matrix) or any(abs(matrix[j])>1e-5 for j in (3,7,11)) or abs(matrix[15]-1)>1e-5:raise ValueError('Invalid affine instance matrix')
        matrices.append(matrix)
    customsize=integer();customcount=integer()
    if customsize!=4 or customcount<0:raise ValueError('Invalid custom data bulk header')
    off+=customsize*customcount
    renderbytes=struct.unpack_from('<Q',blob,off)[0];off+=8
    if off+renderbytes!=len(blob):raise ValueError('Native ISM tail does not account for complete payload')
    return matrices,{'matrixOffsetInExtras':matrixoffset,'elementSize':64,'instanceCount':count,'componentLods':lods,'customFloatCount':customcount,'renderPayloadBytes':renderbytes,'wholeNativePayloadValidated':True,'extrasSha256':hashlib.sha256(blob).hexdigest()}

def quat_from_rows(rows):
    # UE matrix stores basis vectors as rows; transpose for conventional column-vector rotation.
    R=[[rows[j][i] for j in range(3)] for i in range(3)];trace=sum(R[i][i] for i in range(3))
    if trace>0:
        s=math.sqrt(trace+1)*2;q=[(R[2][1]-R[1][2])/s,(R[0][2]-R[2][0])/s,(R[1][0]-R[0][1])/s,s/4]
    else:
        i=max(range(3),key=lambda k:R[k][k]);j=(i+1)%3;k=(i+2)%3;s=math.sqrt(max(0,1+R[i][i]-R[j][j]-R[k][k]))*2;q=[0,0,0,0]
        if s<1e-12:raise ValueError('Degenerate matrix rotation')
        q[i]=s/4;q[j]=(R[j][i]+R[i][j])/s;q[k]=(R[k][i]+R[i][k])/s;q[3]=(R[k][j]-R[j][k])/s
    length=math.sqrt(sum(x*x for x in q));return [x/length for x in q]

def instance_transform(matrix,parent):
    rows=[matrix[i:i+3] for i in (0,4,8)];scales=[m.norm(x) for x in rows]
    if min(scales)<1e-9:raise ValueError('Zero instance scale')
    if m.dot(m.cross(rows[0],rows[1]),rows[2])<0:scales[0]*=-1
    normalized=[m.mul(x,1/s) for x,s in zip(rows,scales)]
    if max(abs(m.dot(normalized[i],normalized[j])) for i in range(3) for j in range(i))>1e-4:raise ValueError('Instance matrix has shear')
    q=quat_from_rows(normalized);T,Q,S=parent['position'],parent['rotationQuaternion'],parent['scale']
    # Reject parent nonuniform scale combined with rotated local basis, which needs full matrix rendering.
    worldrows=[m.qrotate(Q,[x[j]*S[j] for j in range(3)]) for x in rows]
    ws=[m.norm(x) for x in worldrows]
    if min(ws)<1e-9:raise ValueError('Zero composed instance scale')
    if m.dot(m.cross(worldrows[0],worldrows[1]),worldrows[2])<0:ws[0]*=-1
    rn=[m.mul(x,1/s) for x,s in zip(worldrows,ws)]
    if max(abs(m.dot(rn[i],rn[j])) for i in range(3) for j in range(i))>1e-4:raise ValueError('Composed instance requires shear matrix')
    return {'position':m.add(T,m.qrotate(Q,[matrix[12+j]*S[j] for j in range(3)])),'rotationQuaternion':quat_from_rows(rn),'scale':ws}

def bake_spline(obj,asset,props):
    """UE cubic Hermite slice deformation; normal Jacobian includes curvature/scale/roll.

    Retain section and material indices, all UV channels, vertex colors and topology.
    Only known X-forward default convention is accepted until nondefault evidence is verified.
    """
    unsupported=[k for k in ('ForwardAxis','SplineUpDir','SplineBoundaryMin','SplineBoundaryMax') if k in props]
    if unsupported:raise ValueError('Nondefault spline properties need verified interpretation: '+str(unsupported))
    params=props.get('SplineParams')
    if not params:raise ValueError('No explicit SplineParams')
    source=OUT/asset['url'].removeprefix('/assets/world/');d=READ(source)
    ident=asset['id']+'-spline-'+hashlib.sha256(obj['id'].encode()).hexdigest()[:12];dest=OUT/'meshes'/ident
    if (dest/'mesh.gltf').exists():
        cached=READ(dest/'mesh.gltf')
        if cached.get('extras',{}).get('splineProperties')==props:
            cached['materials']=copy.deepcopy(d['materials']);cached['extras']['sourceMaterialSlots']=asset['sourceMaterialSlots'];WRITE(dest/'mesh.gltf',cached)
            stats,bounds=validate_gltf(dest/'mesh.gltf')
            return {**asset,'id':ident,'url':'/assets/world/meshes/'+ident+'/mesh.gltf','bounds':bounds,'geometryStats':stats,'derivedFrom':asset['id'],'splineSource':obj['source'],'sha256':HASH(dest/'mesh.gltf')}
    bs=[bytearray((source.parent/b['uri']).read_bytes()) for b in d['buffers']]
    p0,p1,t0,t1=[m.vec(params.get(k)) for k in ('StartPos','EndPos','StartTangent','EndTangent')]
    s0,s1=[vec2(params.get(k),[1,1]) for k in ('StartScale','EndScale')];o0,o1=[vec2(params.get(k),[0,0]) for k in ('StartOffset','EndOffset')];r0,r1=[float(params.get(k,0)) for k in ('StartRoll','EndRoll')]
    xmin=asset['bounds']['min'][0]*100;xmax=asset['bounds']['max'][0]*100
    if xmax-xmin<1e-6:raise ValueError('Zero spline forward extent')
    smooth=props.get('bSmoothInterpRollScale',False)
    def deform(v):
        x,y,z=v;t=(x-xmin)/(xmax-xmin);tt=t*t;ttt=tt*t
        c=[(2*ttt-3*tt+1)*p0[j]+(ttt-2*tt+t)*t0[j]+(-2*ttt+3*tt)*p1[j]+(ttt-tt)*t1[j] for j in range(3)]
        tangent=m.unit([(6*tt-6*t)*p0[j]+(3*tt-4*t+1)*t0[j]+(-6*tt+6*t)*p1[j]+(3*tt-2*t)*t1[j] for j in range(3)])
        bx=m.unit(m.cross([0,0,1],tangent));by=m.unit(m.cross(tangent,bx));lerp=(t*t*(3-2*t)) if smooth else t
        roll=r0+(r1-r0)*lerp;xx=m.add(m.mul(bx,math.cos(roll)),m.mul(by,-math.sin(roll)));yy=m.add(m.mul(by,math.cos(roll)),m.mul(bx,math.sin(roll)))
        scale=[s0[j]+(s1[j]-s0[j])*lerp for j in range(2)];off=[o0[j]+(o1[j]-o0[j])*lerp for j in range(2)]
        return m.add(c,m.add(m.mul(xx,y*scale[0]+off[0]),m.mul(yy,z*scale[1]+off[1])))
    def setvalue(ai,row,value):
        acc=d['accessors'][ai];view=d['bufferViews'][acc['bufferView']];n={'VEC3':3,'VEC4':4}[acc['type']]
        if acc['componentType']!=5126:raise ValueError('Nonfloat deformed attribute')
        offset=view.get('byteOffset',0)+acc.get('byteOffset',0)+row*view.get('byteStride',n*4)
        struct.pack_into('<'+'f'*n,bs[view['buffer']],offset,*value)
    done=set()
    for mesh in d['meshes']:
        for prim in mesh['primitives']:
            attrs=prim['attributes'];pi=attrs['POSITION']
            if pi in done:continue
            done.add(pi);pos=m.accessor(d,bs,pi);normals=m.accessor(d,bs,attrs['NORMAL']) if 'NORMAL' in attrs else None;tangents=m.accessor(d,bs,attrs['TANGENT']) if 'TANGENT' in attrs else None;newbounds=emptybounds()
            for index,p in enumerate(pos):
                ue=[p[0]*100,p[2]*100,p[1]*100];v=deform(ue);gp=[v[0]*.01,v[2]*.01,v[1]*.01];setvalue(pi,index,gp);expand(newbounds,gp)
                eps=.01;J=[]
                for axis in range(3):
                    va=list(ue);vb=list(ue);va[axis]+=eps;vb[axis]-=eps;J.append(m.mul(m.sub(deform(va),deform(vb)),1/(2*eps)))
                co=[m.cross(J[1],J[2]),m.cross(J[2],J[0]),m.cross(J[0],J[1])];det=m.dot(J[0],co[0])
                if normals:
                    n=normals[index];un=[n[0],n[2],n[1]];nn=m.unit([sum(co[k][j]*un[k] for k in range(3))*(1 if det>=0 else -1) for j in range(3)]);setvalue(attrs['NORMAL'],index,[nn[0],nn[2],nn[1]])
                if tangents:
                    t=tangents[index];ut=[t[0],t[2],t[1]];nt=m.unit([sum(J[k][j]*ut[k] for k in range(3)) for j in range(3)]);setvalue(attrs['TANGENT'],index,[nt[0],nt[2],nt[1],t[3]*(1 if det>=0 else -1)])
            d['accessors'][pi].update(newbounds)
    ident=asset['id']+'-spline-'+hashlib.sha256(obj['id'].encode()).hexdigest()[:12];dest=OUT/'meshes'/ident;dest.mkdir(parents=True,exist_ok=True)
    for i,b in enumerate(d['buffers']):(dest/b['uri']).write_bytes(bs[i])
    d.setdefault('extras',{}).update(splineSource=obj['source'],splineProperties=props,splineDeformation='Hermite X-forward slices; finite-difference Jacobian normals/tangents')
    WRITE(dest/'mesh.gltf',d);stats,bounds=validate_gltf(dest/'mesh.gltf')
    return {**asset,'id':ident,'url':'/assets/world/meshes/'+ident+'/mesh.gltf','bounds':bounds,'geometryStats':stats,'derivedFrom':asset['id'],'splineSource':obj['source'],'sha256':HASH(dest/'mesh.gltf')}

def batch_splines(level,assets,cellsize=128):
    """Merge by level/cell/source mesh/override configuration, retaining all section indices."""
    lookup={x['id']:x for x in assets};groups={};unchanged=[]
    for obj in level['objects']:
        if obj['geometryMode']!='spline-baked':unchanged.append(obj);continue
        asset=lookup[obj['assetId']];center=[(asset['bounds']['min'][i]+asset['bounds']['max'][i])/2 for i in range(3)];center=m.add(obj['position'],m.qrotate(obj['rotation'],[x*s for x,s in zip(center,obj['scale'])]));cell=[math.floor(center[i]/cellsize) for i in (0,2)]
        key=json.dumps([cell,asset['sourcePackage'],obj['materialOverrides']],sort_keys=True);groups.setdefault(key,[]).append(obj)
    newassets=[];batchstats=[]
    for key,objects in groups.items():
        if len(objects)==1:unchanged+=objects;continue
        first=lookup[objects[0]['assetId']];primgroups={};sources=[];sourceTriangles=0
        for obj in objects:
            asset=lookup[obj['assetId']];path=OUT/asset['url'].removeprefix('/assets/world/');d=READ(path);bs=[(path.parent/b['uri']).read_bytes() for b in d['buffers']];sourceTriangles+=asset['geometryStats']['triangles'];pieces=[];negative=math.prod(obj['scale'])<0
            for mesh in d['meshes']:
                for prim in mesh['primitives']:
                    groupkey=(prim['material'],tuple(sorted(prim['attributes'])));g=primgroups.setdefault(groupkey,{'attributes':{k:[] for k in prim['attributes']},'indices':[],'types':{}});base=len(g['attributes']['POSITION']);firstindex=len(g['indices'])
                    for semantic,ai in prim['attributes'].items():
                        ac=d['accessors'][ai];values=m.accessor(d,bs,ai)
                        if ac.get('normalized') and ac['componentType']!=5126:
                            div={5121:255,5123:65535}[ac['componentType']];values=[tuple(x/div for x in value) for value in values]
                        if semantic=='POSITION':values=[m.add(obj['position'],m.qrotate(obj['rotation'],[v[i]*obj['scale'][i] for i in range(3)])) for v in values]
                        elif semantic=='NORMAL':values=[m.unit(m.qrotate(obj['rotation'],[v[i]/obj['scale'][i] for i in range(3)])) for v in values]
                        elif semantic=='TANGENT':values=[m.unit(m.qrotate(obj['rotation'],[v[i]*obj['scale'][i] for i in range(3)]))+[v[3]*(-1 if negative else 1)] for v in values]
                        g['attributes'][semantic]+=values;g['types'][semantic]=ac['type']
                    indices=[v[0]+base for v in m.accessor(d,bs,prim['indices'])]
                    if negative:
                        for i in range(0,len(indices),3):indices[i+1],indices[i+2]=indices[i+2],indices[i+1]
                    g['indices']+=indices;pieces.append({'sourceSectionIndex':prim['material'],'destinationGroupKey':list(groupkey),'firstIndex':firstindex,'indexCount':len(indices),'firstVertex':base,'vertexCount':d['accessors'][prim['attributes']['POSITION']]['count']})
            sources.append({'id':obj['id'],**obj['source'],'position':obj['position'],'rotation':obj['rotation'],'scale':obj['scale'],'bakedAssetId':obj['assetId'],'sections':pieces})
        data=bytearray();views=[];accessors=[];primitives=[]
        def put(values,typ,isindex=False):
            n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[typ];start=len(data);fmt='<'+('I' if isindex else 'f')*n
            for v in values:data.extend(struct.pack(fmt,*(v if isinstance(v,(list,tuple)) else [v])))
            views.append({'buffer':0,'byteOffset':start,'byteLength':len(data)-start});acc={'bufferView':len(views)-1,'componentType':5125 if isindex else 5126,'count':len(values),'type':typ}
            if typ=='VEC3':acc.update(min=[min(v[i] for v in values) for i in range(3)],max=[max(v[i] for v in values) for i in range(3)])
            accessors.append(acc);return len(accessors)-1
        for (mat,semantics),g in primgroups.items():primitives.append({'material':mat,'attributes':{k:put(values,g['types'][k]) for k,values in g['attributes'].items()},'indices':put(g['indices'],'SCALAR',True)})
        ident='spline-batch-'+level['id']+'-'+hashlib.sha256(key.encode()).hexdigest()[:12];dest=OUT/'meshes'/ident;dest.mkdir(parents=True,exist_ok=True)
        firstdoc=READ(OUT/first['url'].removeprefix('/assets/world/'))
        document={'asset':{'version':'2.0','generator':'UNDEFEATED original spline spatial batching'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],'meshes':[{'primitives':primitives}],'materials':firstdoc['materials'],'buffers':[{'uri':'mesh.bin','byteLength':len(data)}],'bufferViews':views,'accessors':accessors,'extras':{'sourcePackage':first['sourcePackage'],'sourceMaterialSlots':first['sourceMaterialSlots'],'sourceComponents':sources,'spatialCellSizeMeters':cellsize}}
        (dest/'mesh.bin').write_bytes(data);WRITE(dest/'mesh.gltf',document);stats,bounds=validate_gltf(dest/'mesh.gltf')
        assert stats['triangles']==sourceTriangles,'Spline batching changed triangle count'
        newasset={**first,'id':ident,'url':'/assets/world/meshes/'+ident+'/mesh.gltf','bounds':bounds,'geometryStats':stats,'sourceComponentCount':len(objects),'sha256':HASH(dest/'mesh.gltf')};newasset.pop('splineSource',None);newasset.pop('derivedFrom',None);newassets.append(newasset)
        unchanged.append({**objects[0],'id':ident,'assetId':ident,'position':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1],'geometryMode':'spline-batch','sourceComponents':sources,'sourceLocalTransformUE':None,'transformCaveat':'Original component transforms baked into world-space vertices; exact sources retained in sourceComponents.'})
        batchstats.append({'id':ident,'sources':len(objects),'sourceTriangles':sourceTriangles,'batchedTriangles':stats['triangles'],'primitives':stats['primitives']})
    level['objects']=unchanged
    return newassets,batchstats

def inventory(include_templates=False):
    world=READ(AUDIT/'world-coverage.json');other=READ(AUDIT/'all-map-inventory.json');rows=[];packages=set()
    for scope,records in [('main-world',world['levels']),('supplemental',other['supplementalMaps'])]:
        for r in records:
            detail=READ(AUDIT/r['details']);rows.append({'record':r,'scope':scope,'detail':detail})
            for mesh in detail['meshReferences']:packages.add(mesh['assetReference'].rsplit('/',1)[0])
    if include_templates:
        path=EVID/'geometry-template-resolution.json'
        if path.exists():
            templates=READ(path);byname={r['record']['name']:r for r in rows}
            for item in templates['components']:
                if item['status']!='exact-template-mesh-default-recovered' or not item.get('transform'):continue
                row=byname[item['levelId']];idx=item['source']['exportIndex'];ref=item['meshReference'];packages.add(ref.rsplit('/',1)[0])
                row['detail']['meshReferences'].append({'componentExportIndex':idx,'sourceActor':item['source']['actor'],'component':item['source']['component'],'class':item['componentClass'],'property':item['property'],'assetReference':ref,'templateRecovery':item})
                t=next(x for x in row['detail']['componentTransforms'] if x['exportIndex']==idx);t['composedComponentTransformUE']=item['transform'];t['visibilityProperties']=item['visibilityProperties'];t['attachSocket']=item['attachSocket']
    return rows,sorted(packages)

def assemble(rows,assets,export_results,bake):
    bypkg={x['sourcePackage']:x for x in assets};levels=[];gaps=[];spawns=[];total=collections.Counter();allassets=list(assets)
    socketfile=EVID/'geometry-socket-resolution.json';socketdata=READ(socketfile) if socketfile.exists() else {'resolved':[]};socketresolved={x['id']:x for x in socketdata['resolved']}
    for row in rows:
        record=row['record'];detail=row['detail'];lid=record['name'];trans={x['exportIndex']:x for x in detail['componentTransforms']};overrides={x['componentExportIndex']:x['slots'] for x in detail['materialOverrides']};actors={x['exportIndex']:x for x in detail['actors']};level={'id':lid,'package':record['package'],'scope':row['scope'],'streaming':detail['streamingRecords'],'bounds':emptybounds(),'objects':[]};decoded=None;pkg=None
        def source_props(i):
            nonlocal decoded,pkg
            if pkg is None:decoded=READ(pathlib.Path(record['decoded']));pkg=a.Package(decoded,lid)
            return pkg.props(i)
        for actor in detail['actors']:
            if actor['class'] not in ('PlayerStart','BP_RespawnAndSpawnPoint_C'):continue
            t=trans.get(actor.get('rootComponentIndex'))
            if t and t.get('composedComponentTransformUE'):spawns.append({'levelId':lid,'scope':row['scope'],'actorClass':actor['class'],'sourceActor':lid+'/PersistentLevel/'+actor['name'],'sourceExportIndex':actor['exportIndex'],**transform(t['composedComponentTransformUE'])})
        for mesh in detail['meshReferences']:
            idx=mesh['componentExportIndex'];ident=lid+':'+str(idx);src={'package':record['package'],'actor':mesh['sourceActor'],'component':mesh['component'],'exportIndex':idx};t=trans.get(idx);pkgname=mesh['assetReference'].rsplit('/',1)[0];asset=bypkg.get(pkgname);total[row['scope']+'SourceComponents']+=1
            if 'templateRecovery' in mesh:total[row['scope']+'TemplateDefaultComponents']+=1
            else:total[row['scope']+'ExplicitMeshComponents']+=1
            def gap(reason,extra=None):gaps.append({'id':ident,'source':src,'sourceMesh':pkgname,'reason':reason,'materialOverrides':mesh.get('templateRecovery',{}).get('materialOverrides',[{'slotIndex':i,'material':package_ref(ref)} for i,ref in enumerate(overrides.get(idx,[]))]),'transformBeforeSocketUE':t.get('composedComponentTransformUE') if t else None,**(extra or {})})
            if not asset:gap('mesh-export-failed');continue
            if not t or not t.get('composedComponentTransformUE'):gap('component-transform-unresolved');continue
            if t.get('attachSocket') and t['attachSocket']!='None' and ident not in socketresolved:gap('attachment-socket-transform-not-applied',{'socket':t['attachSocket']});continue
            actorvisibility=actors.get(t.get('sourceActorExportIndex'),{}).get('visibilityProperties',{})
            obj={'id':ident,'assetId':asset['id'],**transform(t['composedComponentTransformUE']),'source':src,'componentClass':mesh['class'],'geometryMode':'static','materialOverrides':[{'slotIndex':i,'material':package_ref(ref)} for i,ref in enumerate(overrides.get(idx,[]))],'visibilityProperties':{**t.get('visibilityProperties',{}),'actorHidden':actorvisibility.get('bHidden',actorvisibility.get('bHiddenInGame'))},'sourceActorVisibilityProperties':actorvisibility,'sourceLocalTransformUE':{k:t[k] for k in ('relativeLocationUE','relativeRotationUE','relativeScaleUE','absoluteFlags')},'transformCaveat':'Parent attachment composition from serialized values; omitted template defaults remain unresolved.'}
            if 'templateRecovery' in mesh:
                tr=mesh['templateRecovery'];obj.update(geometryMode='template-default',materialOverrides=tr['materialOverrides'],visibilityProperties=tr['visibilityProperties'],templateRecovery={'chain':tr['templateChain'],'meshPropertySource':tr['meshPropertySource'],'materialOverrideSource':tr.get('materialOverrideSource'),'caveat':tr['constructionCaveat']},transformCaveat='Serialized template/instance default composition; construction/runtime mutations are not executed.')
            if ident in socketresolved:
                sr=socketresolved[ident];obj.update(**sr['transform'],geometryMode='socket-reference-pose',socketAttachment={'parentComponent':sr['parentComponent'],'socketName':sr['socketEvidence']['socketName'],'boneName':sr['socketEvidence']['boneName'],'sourceSocket':sr['socketEvidence']['socket'],'boneNodeIndex':sr['socketEvidence']['boneNodeIndex'],'animationFollowingImplemented':False,'evidence':'research/world-recovery/geometry-socket-resolution.json#'+ident},transformCaveat=sr['limitation']);total['referencePoseSocketAttachments']+=1
            if any(s in mesh['class'] for s in ('InstancedStaticMesh','HierarchicalInstanced')):
                props=source_props(idx);extras=base64.b64decode(pkg.ref(idx).get('Extras',{}).get('$value',''))
                try:
                    matrices,evidence=decode_instances(extras)
                    recovered=[]
                    for ii,matrix in enumerate(matrices):
                        it=instance_transform(matrix,t['composedComponentTransformUE']);instance={**obj,**transform(it),'id':ident+':instance:'+str(ii),'source':{**src,'instanceIndex':ii},'geometryMode':'instanced','sourceInstanceMatrixUE':matrix,'instanceArrayEvidence':evidence};recovered.append(instance)
                    for instance in recovered:level['objects'].append(instance);objectbounds(level['bounds'],instance,asset['bounds']);total[row['scope']+'Objects']+=1
                    total['instancedComponentsRecovered']+=1;total['instancesRecovered']+=len(recovered)
                except Exception as error:gap('native-instance-array-not-decoded',{'error':str(error),'extrasBytes':len(extras),'extrasSha256':hashlib.sha256(extras).hexdigest()})
                continue
            if mesh['class']=='SplineMeshComponent':
                if not bake:gap('spline-bake-not-requested');continue
                try:
                    derived=bake_spline(obj,asset,source_props(idx));allassets.append(derived);asset=derived;obj.update(assetId=derived['id'],geometryMode='spline-baked');total['splinesBaked']+=1
                except Exception as error:gap('spline-bake-failed',{'error':str(error)});continue
            level['objects'].append(obj);objectbounds(level['bounds'],obj,asset['bounds']);total[row['scope']+'Objects']+=1
        if not level['objects']:level['bounds']=None
        levels.append(level);print('LAYOUT',lid,len(level['objects']),flush=True)
    batchstats=[]
    for level in levels:
        new,stats=batch_splines(level,allassets);allassets+=new;batchstats+=stats
    used={o['assetId'] for level in levels for o in level['objects']};allassets=[x for x in allassets if x['id'] in used or not x.get('derivedFrom')]
    total.update(assets=len(allassets),baseAssets=len(assets),levels=len(levels),gaps=len(gaps),spawnCandidates=len(spawns),renderObjects=sum(len(x['objects']) for x in levels),splineBatches=len(batchstats),splineComponentsBatched=sum(x['sources'] for x in batchstats))
    WRITE(EVID/'geometry-spline-batches.json',batchstats)
    templates=READ(EVID/'geometry-template-resolution.json') if (EVID/'geometry-template-resolution.json').exists() else {'components':[],'summary':{}}
    unresolved=[x for x in templates['components'] if x['status']!='exact-template-mesh-default-recovered' or not x.get('transform')]
    manifest={'schemaVersion':1,'coordinateSystem':'gltf-rh-y-up-meters','originUE':[0,0,0],'assets':allassets,'levels':levels,'spawnCandidates':spawns,'gaps':gaps,'unresolvedComponents':unresolved,'templateResolutionSummary':templates['summary'],'socketResolutionSummary':socketdata.get('summary'),'totals':dict(total),'limitations':['Stored map objects are not proof of simultaneous visibility; runtime streaming logic is not applied.','Template-default objects follow exact cooked TemplateIndex/import paths and retain original MID overrides; construction scripts and runtime reassignments are not executed.','socket-reference-pose objects use original socket/bone reference matrices; runtime animated socket following is not implemented.','Native foliage actor payload in supplemental TestLevel is not yet recovered; terrain is delivered by a separate manifest.','No original material rendering claim: material slots retained, diagnostic palette removed pending material conversion.','LOD0 render geometry does not restore original collision, navigation or other LODs.']}
    foliage_evidence=EVID/'geometry-foliage-recovery.json'
    if foliage_evidence.exists():
        fr=READ(foliage_evidence);manifest['foliageRecovery']={'status':fr['status'],**fr['summary'],'evidence':'research/world-recovery/geometry-foliage-recovery.json','runtimeGenerationProven':False}
        manifest['limitations']=[s for s in manifest['limitations'] if 'Native foliage actor payload in supplemental TestLevel' not in s]
        manifest['limitations'].append('The supplemental TestLevel foliage actor stores an empty FoliageInfos map (zero types/instances), verified through the full native export. Runtime foliage generation is not observed or executed.')
    WRITE(OUT/'geometry-manifest.json',manifest);WRITE(EVID/'geometry-export-results.json',export_results);WRITE(EVID/'geometry-gaps.json',gaps)
    WRITE(EVID/'geometry-summary.json',{'totals':dict(total),'gapReasons':dict(collections.Counter(x['reason'] for x in gaps)),'manifestSha256':HASH(OUT/'geometry-manifest.json'),'sourceWorldSummarySha256':HASH(AUDIT/'world-coverage.json'),'exportFailures':[r for r in export_results if 'error' in r]})
    print(json.dumps(dict(total)),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3);parser.add_argument('--skip-export',action='store_true');parser.add_argument('--skip-splines',action='store_true');parser.add_argument('--layout-only',action='store_true',help='Reuse validated base glTF files and regenerate placement metadata.');args=parser.parse_args()
    EVID.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    rows,packages=inventory(True);WRITE(EVID/'geometry-source-packages.json',packages);print('SOURCE PACKAGES',len(packages),flush=True)
    if args.layout_only:
        assemble(rows,READ(EVID/'geometry-base-assets.json'),READ(EVID/'geometry-export-results.json'),not args.skip_splines);return
    if args.skip_export:results=READ(EVID/'geometry-export-results.json')
    else:
        extract(packages);results=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for result in pool.map(export_one,packages):
                results.append(result);print('EXPORT',len(results),'/',len(packages),result['package'],'FAIL' if 'error' in result else 'OK',flush=True)
                WRITE(EVID/'geometry-export-results.json',results)
    assets=[]
    for i,result in enumerate(results):
        if 'error' in result:continue
        try:assets.append(publish(result))
        except Exception as error:result['error']='publish: '+str(error)
        if (i+1)%20==0:print('PUBLISH',i+1,flush=True)
    WRITE(EVID/'geometry-base-assets.json',assets)
    assemble(rows,assets,results,not args.skip_splines)

if __name__=='__main__':main()
