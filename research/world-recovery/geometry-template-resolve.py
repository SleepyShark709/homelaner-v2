"""Resolve exact cooked component TemplateIndex chains; no component-name guessing."""
import collections, importlib.util, pathlib, json
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def run():
    rows,_=g.inventory();decoded=g.AUDIT/'decoded';files={'/Game/'+p.relative_to(decoded).with_suffix('').as_posix():p for p in decoded.rglob('*.json')};cache={};lookups={};chaincache={};results=[];summary=collections.Counter()
    player=ROOT/'research/exports/decoded/PlayerBP.json'
    if player.exists():files['/Game/-HeroGame/Player/PlayerBP']=player
    for row in rows:files[row['record']['package']]=pathlib.Path(row['record']['decoded'])
    def package(name):
        if name not in cache:
            if name not in files:return None
            cache[name]=g.a.Package(g.READ(files[name]),name.rsplit('/',1)[1]);p=cache[name];lookups[name]={p.path(i):i for i in range(1,len(p.ex)+1)}
        return cache[name]
    def target(owner,index):
        p=package(owner)
        if index>0:return owner,index
        path=p.path(index)
        if not path or path.startswith('/Script/'):return None
        candidates=[name for name in files if path.startswith(name+'/')]
        if not candidates:
            root=index
            while p.ref(root).get('OuterIndex',0):root=p.ref(root)['OuterIndex']
            name=p.objname(root);base=g.diskbase(name)
            if not base or base+'.uasset' not in g.INVENTORY:return None
            file=g.EVID/'geometry-decoded-templates'/(base+'.json')
            if not file.exists():
                g.extract([name]);file.parent.mkdir(parents=True,exist_ok=True);run=g.hiddenrun([g.TOOLS/'uasset-net472/UAssetGUI.exe','tojson',g.UNPACK/(base+'.uasset'),file,'VER_UE4_27'])
                if run.returncode or not file.exists():return None
            files[name]=file;candidates=[name]
        name=max(candidates,key=len);q=package(name);subpath=path[len(name)+1:];idx=lookups[name].get(subpath)
        return (name,idx) if idx else None
    def chain(owner,index,seen=None):
        key=(owner,index)
        if key in chaincache:return chaincache[key]
        seen=set() if seen is None else seen
        if key in seen:return [key]
        seen.add(key);p=package(owner);ti=p.ref(index).get('TemplateIndex',0);nextkey=target(owner,ti) if ti else None;result=[key]
        if nextkey:result+=chain(*nextkey,seen)
        chaincache[key]=result;return result
    def field(owner,index,name):
        for op,oi in chain(owner,index):
            props=package(op).props(oi)
            if name in props:return props[name],op,oi
        return None
    for row in rows:
        rec=row['record'];detail=row['detail'];owner=rec['package'];p=package(owner);trans={x['exportIndex']:x for x in detail['componentTransforms']};meshindices={x['componentExportIndex'] for x in detail['meshReferences']};actorTemplates=collections.defaultdict(dict)
        for idx,t in trans.items():
            for c in chain(owner,idx)[1:]:actorTemplates[t['sourceActorExportIndex']][c]=idx
        composed={}
        def world(idx,seen=None):
            if idx in composed:return composed[idx]
            seen=set() if seen is None else seen
            if idx in seen:raise ValueError('Component attachment cycle')
            seen.add(idx)
            def val(name,default=None):
                item=field(owner,idx,name);return item[0] if item is not None else default
            t=g.m.vec(val('RelativeLocation'));q=g.m.rotator(val('RelativeRotation',{}));s=g.m.vec(val('RelativeScale3D'),(1,1,1));parentfield=field(owner,idx,'AttachParent');parent=0
            if parentfield and isinstance(parentfield[0],int) and parentfield[0]:
                ref,op,oi=parentfield;dest=target(op,ref)
                if dest:
                    if dest[0]==owner:parent=dest[1]
                    else:parent=actorTemplates[trans[idx]['sourceActorExportIndex']].get(dest)
                if not parent:raise ValueError('Inherited AttachParent has no exact instance TemplateIndex match')
            if parent:
                T=world(parent,seen);pt,pq,ps=T['position'],T['rotationQuaternion'],T['scale']
                if not val('bAbsoluteLocation',False):t=g.m.add(pt,g.m.qrotate(pq,[x*y for x,y in zip(t,ps)]))
                if not val('bAbsoluteRotation',False):q=g.m.qmul(pq,q)
                if not val('bAbsoluteScale',False):s=[x*y for x,y in zip(s,ps)]
            composed[idx]={'position':t,'rotationQuaternion':q,'scale':s};return composed[idx]
        for idx,t in trans.items():
            if idx in meshindices or not any(k in t['class'] for k in ('StaticMesh','SkeletalMesh','SplineMesh')):continue
            summary[row['scope']+'MeshComponentsWithoutExplicitMesh']+=1;properties=p.props(idx)
            key='SkeletalMesh' if 'SkeletalMesh' in t['class'] else 'StaticMesh';resolved=field(owner,idx,key);template=chain(owner,idx)
            output={'id':rec['name']+':'+str(idx),'scope':row['scope'],'levelId':rec['name'],'source':{'package':owner,'actor':t['sourceActor'],'component':t['component'],'exportIndex':idx},'componentClass':t['class'],'templateChain':[{'package':op,'exportIndex':oi,'objectPath':package(op).path(oi)} for op,oi in template],'materialOverrides':[],'status':'no-serialized-mesh-through-exact-template-chain','transform':None}
            output['visibilityProperties']={}
            for name in ('bVisible','bHiddenInGame','bOwnerNoSee','bOnlyOwnerSee','CastShadow'):
                item=field(owner,idx,name)
                if item is not None:output['visibilityProperties'][name]=item[0]
            actorhidden=field(owner,t['sourceActorExportIndex'],'bHidden')
            output['visibilityProperties']['actorHidden']=actorhidden[0] if actorhidden else None
            socket=field(owner,idx,'AttachSocketName');output['attachSocket']=socket[0] if socket else None
            materialfield=field(owner,idx,'OverrideMaterials');mo,mi=(materialfield[1],materialfield[2]) if materialfield else (owner,idx);mp=package(mo)
            raw=next((x.get('Value',[]) for x in mp.ref(mi).get('Data',[]) if x['Name']=='OverrideMaterials'),[])
            output['materialOverrideSource']={'package':mo,'exportIndex':mi}
            for slot,element in enumerate(raw):
                ref=element.get('Value',0);material=None
                if ref<0:material=g.package_ref(mp.path(ref))
                elif ref>0:material={'package':mo+'#export:'+str(ref),'reference':mo+'#export:'+str(ref),'ownerPackage':mo,'object':mp.objname(ref),'objectPath':mp.path(ref),'exportIndex':ref,'isEmbedded':True}
                output['materialOverrides'].append({'slotIndex':slot,'material':material})
            try:output['transform']=world(idx)
            except Exception as error:output['transformError']=str(error)
            if resolved:
                ref,op,oi=resolved
                if isinstance(ref,int) and ref:
                    rp=package(op);path=rp.path(ref)
                    if path and path.startswith(('/Game/','/Engine/')):
                        output.update(status='exact-template-mesh-default-recovered',meshReference=path,property=key,meshPropertySource={'package':op,'exportIndex':oi,'referenceIndex':ref});summary[row['scope']+'TemplateMeshesResolved']+=1
                        if output['transform'] is not None:summary[row['scope']+'TemplateMeshesWithTransforms']+=1
                    else:output['meshReferenceUnresolved']=path
                elif ref==0:output['status']='explicit-null-in-template-chain'
            output['constructionCaveat']='Recovered serialized instance/template defaults. Construction-script and runtime reassignment are not executed.'
            results.append(output)
        print('TEMPLATES',rec['name'],sum(x['levelId']==rec['name'] and x['status']=='exact-template-mesh-default-recovered' for x in results),flush=True)
    document={'scope':'Map mesh components without direct StaticMesh/SkeletalMesh property; exact TemplateIndex/import path traversal only.','summary':dict(summary),'components':results,'sourcePackagesLoaded':list(cache),'decodedPackagePaths':{k:str(files[k]) for k in cache},'decodedPackageSha256':{k:g.HASH(files[k]) for k in cache}}
    g.WRITE(g.EVID/'geometry-template-resolution.json',document);print(json.dumps(dict(summary)),flush=True)

if __name__=='__main__':run()
