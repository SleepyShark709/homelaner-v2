"""Recover static/reference-pose attachments from exact cooked component/socket/bone data."""
import collections, importlib.util, math, pathlib, runpy
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
U=runpy.run_path(str(ROOT/'scripts/convert-original-animations.py'))
matrix=U['matrix'];multiply=U['multiply'];world_matrices=U['world_matrices'];read_accessor=U['read_accessor']

def as_matrix(transform):return matrix({'translation':transform['position'],'rotation':transform['rotation'],'scale':transform['scale']})
def error(A,B):return max(abs(A[r][c]-B[r][c]) for r in range(4) for c in range(4))
def decompose(M):
    columns=[[M[r][c] for r in range(3)] for c in range(3)];scales=[g.m.norm(v) for v in columns]
    if min(scales)<1e-10:raise ValueError('Zero scale in attachment matrix')
    if g.m.dot(g.m.cross(columns[0],columns[1]),columns[2])<0:scales[0]*=-1
    axes=[g.m.mul(v,1/s) for v,s in zip(columns,scales)]
    shear=max(abs(g.m.dot(axes[i],axes[j])) for i in range(3) for j in range(i))
    if shear>1e-4:raise ValueError('Attachment contains unsupported TRS shear '+str(shear))
    result={'position':[M[i][3] for i in range(3)],'rotation':g.quat_from_rows(axes),'scale':scales}
    reconstruction=error(M,as_matrix(result))
    if reconstruction>.0002:raise ValueError('TRS reconstruction error '+str(reconstruction))
    return result,reconstruction

def run():
    manifest=g.READ(g.OUT/'geometry-manifest.json');templates=g.READ(g.EVID/'geometry-template-resolution.json');rows,_=g.inventory(True)
    files={k:pathlib.Path(v) for k,v in templates['decodedPackagePaths'].items()};cache={};lookup={};chaincache={}
    meshassets={x['sourcePackage']:x for x in g.READ(g.EVID/'geometry-base-assets.json')};meshrefs={};transformrefs={};actorrefs={};recordbyname={}
    for row in rows:
        rec=row['record'];recordbyname[rec['name']]=row;files[rec['package']]=pathlib.Path(rec['decoded'])
        for ref in row['detail']['meshReferences']:meshrefs[(rec['package'],ref['componentExportIndex'])]=ref
        for t in row['detail']['componentTransforms']:transformrefs[(rec['package'],t['exportIndex'])]=t
    def package(name):
        if name not in cache:
            if name not in files:
                base=g.diskbase(name);file=g.AUDIT/'decoded-world-assets'/(base+'.json')
                if not file.exists():file=g.EVID/'geometry-decoded-sockets'/(base+'.json')
                if not file.exists():
                    g.extract([name]);file.parent.mkdir(parents=True,exist_ok=True);r=g.hiddenrun([g.TOOLS/'uasset-net472/UAssetGUI.exe','tojson',g.UNPACK/(base+'.uasset'),file,'VER_UE4_27']);r.check_returncode()
                files[name]=file
            cache[name]=g.a.Package(g.READ(files[name]),name.rsplit('/',1)[1]);p=cache[name];lookup[name]={p.path(i):i for i in range(1,len(p.ex)+1)}
        return cache[name]
    def target(owner,index):
        if index>0:return owner,index
        if not index:return None
        p=package(owner);path=p.path(index)
        if path.startswith('/Script/'):return None
        root=index
        while p.ref(root).get('OuterIndex',0):root=p.ref(root)['OuterIndex']
        name=p.objname(root);q=package(name);sub=path[len(name)+1:];idx=lookup[name].get(sub)
        return (name,idx) if idx else None
    def chain(owner,index):
        key=(owner,index)
        if key not in chaincache:
            chaincache[key]=[key];p=package(owner);ti=p.ref(index).get('TemplateIndex',0);nextkey=target(owner,ti) if ti else None
            if nextkey and nextkey!=key:chaincache[key]+=chain(*nextkey)
        return chaincache[key]
    def field(owner,index,name):
        for op,oi in chain(owner,index):
            props=package(op).props(oi)
            if name in props:return props[name],op,oi
        return None
    def local(owner,index):
        def value(name,default):
            f=field(owner,index,name);return f[0] if f else default
        if any(value(k,False) for k in ('bAbsoluteLocation','bAbsoluteRotation','bAbsoluteScale')):raise ValueError('Absolute transform attachment requires separate channel composition')
        return {'position':g.glpos(g.m.vec(value('RelativeLocation',{}))),'rotation':g.glrot(g.m.rotator(value('RelativeRotation',{}))),'scale':g.glscale(g.m.vec(value('RelativeScale3D',{}),(1,1,1)))}
    def parent_for(owner,index):
        f=field(owner,index,'AttachParent')
        if not f or not f[0]:raise ValueError('No AttachParent reference')
        dest=target(f[1],f[0])
        if dest and dest[0]==owner:return dest
        actor=transformrefs[(owner,index)]['sourceActorExportIndex'];candidates=[]
        for (op,oi),t in transformrefs.items():
            if op==owner and t['sourceActorExportIndex']==actor and dest in chain(op,oi):candidates.append((op,oi))
        if len(candidates)!=1:raise ValueError('Parent instance mapping not unique '+str(candidates))
        return candidates[0]
    def sockets(owner,rootindex):
        p=package(owner);refs=g.a.integer_refs(p.props(rootindex).get('Sockets',[]));result=[]
        # Ownership is corroborated with explicit Sockets array when serialized as properties.
        for i,e in enumerate(p.ex,1):
            if p.cls(i)!='SkeletalMeshSocket':continue
            if refs and i not in refs:continue
            if not refs and e.get('OuterIndex')!=rootindex:continue
            props=p.props(i)
            if props.get('SocketName'):result.append({'package':owner,'exportIndex':i,'objectPath':p.path(i),'properties':props,'membershipEvidence':'Sockets property array' if refs else 'Owned SkeletalMeshSocket export','sourceSha256':g.HASH(files[owner])})
        return result
    assetcache={}
    def bone_socket(parentmesh,socketname):
        if parentmesh not in assetcache:
            asset=meshassets[parentmesh];path=g.OUT/asset['url'].removeprefix('/assets/world/');doc=g.READ(path);world=world_matrices(doc['nodes']);p=package(parentmesh);indices=[i for i in range(1,len(p.ex)+1) if p.cls(i)=='SkeletalMesh'];assert len(indices)==1;rootindex=indices[0];definitions=sockets(parentmesh,rootindex);skeletonref=p.props(rootindex).get('Skeleton',0);skeleton=None
            if skeletonref:
                skeleton=p.path(skeletonref).rsplit('/',1)[0];sk=package(skeleton);skroots=[i for i in range(1,len(sk.ex)+1) if sk.cls(i)=='Skeleton'];assert len(skroots)==1
                existing={s['properties']['SocketName'].casefold() for s in definitions};definitions += [s for s in sockets(skeleton,skroots[0]) if s['properties']['SocketName'].casefold() not in existing]
            buffers=[(path.parent/b['uri']).read_bytes() for b in doc['buffers']];skinerror=0
            for meshnode,node in enumerate(doc['nodes']):
                if 'skin' not in node:continue
                skin=doc['skins'][node['skin']];ib=read_accessor(doc,buffers,skin['inverseBindMatrices'])
                for j,bone in enumerate(skin['joints']):
                    inverse=[[ib[j][c*4+r] for c in range(4)] for r in range(4)];skinerror=max(skinerror,error(multiply(world[bone],inverse),world[meshnode]))
            if skinerror>.001:raise ValueError('Parent reference pose/inverse bind mismatch '+str(skinerror))
            assetcache[parentmesh]=(doc,world,definitions,skinerror,skeleton,path)
        doc,world,definitions,skinerror,skeleton,path=assetcache[parentmesh];matches=[s for s in definitions if s['properties']['SocketName'].casefold()==socketname.casefold()]
        if len(matches)>1:raise ValueError('Ambiguous socket definitions')
        socket=matches[0] if matches else None;bonename=socket['properties']['BoneName'] if socket else socketname
        joints={j for s in doc.get('skins',[]) for j in s['joints']};boneids=[i for i in joints if doc['nodes'][i].get('name','').casefold()==bonename.casefold()]
        if len(boneids)!=1:raise ValueError('Socket/bone not found uniquely in original mesh skeleton: '+bonename)
        props=socket['properties'] if socket else {};socketlocal={'position':g.glpos(g.m.vec(props.get('RelativeLocation'))),'rotation':g.glrot(g.m.rotator(props.get('RelativeRotation',{}))),'scale':g.glscale(g.m.vec(props.get('RelativeScale',props.get('RelativeScale3D')),(1,1,1)))}
        boneid=boneids[0];combined=multiply(world[boneid],as_matrix(socketlocal))
        return combined,{'kind':'socket-definition' if socket else 'direct-bone-name','socket':socket,'socketName':socketname,'boneName':bonename,'boneNodeIndex':boneid,'parentSkeletonPackage':skeleton,'boneReferenceMatrix':world[boneid],'socketRelativeMatrix':as_matrix(socketlocal),'socketInMeshReferenceMatrix':combined,'parentGltf':str(path),'parentGltfSha256':g.HASH(path),'parentSkinInverseBindMaximumError':skinerror}
    resolved={};failures=[]
    # On repeat runs, inspect the retained original gap inventory as the now-resolved objects no longer occur in gaps.
    originals=g.EVID/'geometry-socket-original-gaps.json'
    if not originals.exists():g.WRITE(originals,manifest['gaps'])
    gaps=g.READ(originals)
    for gap in gaps:
        try:
            owner=gap['source']['package'];index=gap['source']['exportIndex'];parent=parent_for(owner,index);pm=meshrefs.get(parent)
            if pm is None:raise ValueError('Parent component has no recovered mesh')
            parentmesh=pm['assetReference'].rsplit('/',1)[0];parenttransform=g.transform(transformrefs[parent]['composedComponentTransformUE']);parentmatrix=as_matrix(parenttransform);childlocal=local(owner,index)
            baseline=multiply(parentmatrix,as_matrix(childlocal));recorded=g.transform(transformrefs[(owner,index)]['composedComponentTransformUE']);baselineerror=error(baseline,as_matrix(recorded))
            if baselineerror>.001:raise ValueError('Parent/local composition differs from pre-socket transform '+str(baselineerror))
            socketmatrix,evidence=bone_socket(parentmesh,gap['socket']);full=multiply(multiply(parentmatrix,socketmatrix),as_matrix(childlocal));result,reconstruction=decompose(full)
            record={'id':gap['id'],'source':gap['source'],'status':'recovered-reference-pose','parentComponent':{'package':parent[0],'exportIndex':parent[1],'sourceActor':pm['sourceActor'],'component':pm['component'],'mesh':parentmesh},'socketEvidence':evidence,'parentComponentWorldMatrix':parentmatrix,'childRelativeMatrix':as_matrix(childlocal),'referencePoseWorldMatrix':full,'transform':result,'baselineCompositionMaximumError':baselineerror,'trsReconstructionMaximumError':reconstruction,'animationFollowingImplemented':False,'limitation':'Static original mesh reference pose only. No runtime skeletal animation/socket following is implemented by this placement.'}
            resolved[gap['id']]=record;print('SOCKET OK',gap['id'],gap['socket'],evidence['boneName'],flush=True)
        except Exception as error_:failures.append({**gap,'resolutionError':str(error_)});print('SOCKET GAP',gap['id'],str(error_),flush=True)
    legacy=g.READ(ROOT/'research/evidence/character-assembly.json');head=[r for r in resolved.values() if r['socketEvidence']['socketName']=='head_accessories'];legacychecks=[]
    for row in head:
        socket=row['socketEvidence']['socket'];actual=socket['properties'];expected=legacy['socketSource']['properties'];matches=actual['BoneName'].casefold()==expected['BoneName'].casefold() and error(row['socketEvidence']['socketRelativeMatrix'],matrix(legacy['socketGltfTransform']))<1e-8
        samepackage=socket['package']=='/Game/Action_Male/Meshes/SKEL_Male'
        if samepackage:assert matches
        legacychecks.append({'id':row['id'],'sameSkeletonAsExistingAssembly':samepackage,'socketPropertiesMatchExistingAssemblyEvidence':matches,'referencePoseSocketMatrixDifference':error(row['socketEvidence']['socketInMeshReferenceMatrix'],legacy['socketBindWorldMatrix'])})
    report={'scope':'Original 46 omitted attachment components; exact parents, socket definitions/bone names, exported mesh reference skeleton and inverse binds.','resolved':list(resolved.values()),'gaps':failures,'summary':{'originalGaps':len(gaps),'referencePoseRecovered':len(resolved),'remaining':len(failures),'runtimeAnimatedFollowingImplemented':False},'legacyHeadAccessoryChecks':legacychecks,'decodedSources':{k:{'path':str(files[k]),'sha256':g.HASH(files[k])} for k in cache}}
    g.WRITE(g.EVID/'geometry-socket-resolution.json',report);print(report['summary'])

if __name__=='__main__':run()
