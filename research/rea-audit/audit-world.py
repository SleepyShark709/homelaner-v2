"""Read-only whole MainLevel streaming-world audit. No demo/public mutations."""
import base64, collections, concurrent.futures, hashlib, importlib.util, json, math, pathlib, struct, subprocess, time

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
MAPROOT=ROOT/'research/exports/city-unpacked/UNDEFEATED/Content'
EXISTING=ROOT/'research/exports/city-decoded'
DECODED=OUT/'decoded-world'
TOOL=ROOT/'tools/asset-pipeline/uasset-net472/UAssetGUI.exe'
spec=importlib.util.spec_from_file_location('city_math',ROOT/'tools/asset-pipeline/export-city.py');mathmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mathmod)

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def compact(x):return mathmod.simplify(x)

class Package:
    def __init__(self,data,name):self.data=data;self.name=name;self.ex=data['Exports'];self.im=data['Imports'];self.cache={};self.propsCache={}
    def ref(self,index):return (self.ex[index-1] if index>0 else self.im[-index-1]) if index else {}
    def objname(self,index):return self.ref(index).get('ObjectName','')
    def path(self,index,seen=None):
        if not index:return None
        seen=set() if seen is None else seen
        if index in seen:return '[cycle]'
        seen.add(index);obj=self.ref(index);outer=obj.get('OuterIndex',0)
        return (self.path(outer,seen)+'/' if outer else '')+obj['ObjectName']
    def cls(self,index):return self.objname(self.ref(index).get('ClassIndex',0))
    def props(self,index):
        if index not in self.propsCache:self.propsCache[index]={p['Name']:compact(p.get('Value',p)) for p in self.ref(index).get('Data',[]) if 'Name' in p}
        return self.propsCache[index]
    def world(self,index,seen=None):
        if index in self.cache:return self.cache[index]
        seen=set() if seen is None else seen
        if index in seen:raise ValueError('Attachment cycle '+str(index))
        seen.add(index);p=self.props(index);t=mathmod.vec(p.get('RelativeLocation'));q=mathmod.rotator(p.get('RelativeRotation',{}));s=mathmod.vec(p.get('RelativeScale3D'),(1,1,1));parent=p.get('AttachParent',0)
        if isinstance(parent,int) and parent>0:
            T,Q,S=self.world(parent,seen)
            if not p.get('bAbsoluteLocation',False):t=mathmod.add(T,mathmod.qrotate(Q,[x*y for x,y in zip(t,S)]))
            if not p.get('bAbsoluteRotation',False):q=mathmod.qmul(Q,q)
            if not p.get('bAbsoluteScale',False):s=[x*y for x,y in zip(s,S)]
        self.cache[index]=(t,q,s);return t,q,s
    def streamings(self):
        records=[];tables=[]
        for i,e in enumerate(self.ex,1):
            if self.cls(i)!='World':continue
            raw=base64.b64decode(e.get('Extras',{}).get('$value',''));words=list(struct.unpack('<'+'i'*(len(raw)//4),raw[:len(raw)//4*4]))
            # Known UE4 cooked UWorld tail: prefix/PersistentLevel/extra refs followed by counted streaming refs.
            candidates=[]
            for start,count in enumerate(words):
                if count<=0 or start+1+count!=len(words):continue
                refs=words[start+1:]
                if len(set(refs))==len(refs) and all(0<x<=len(self.ex) and self.cls(x).startswith('LevelStreaming') for x in refs):candidates.append((start,count,refs))
            if len(candidates)!=1:
                tables.append({'worldExport':i,'tailBytes':len(raw),'tailWords':words,'verifiedCountedTable':False});continue
            start,count,refs=candidates[0];tables.append({'worldExport':i,'tailBytes':len(raw),'tailSha256':hashlib.sha256(raw).hexdigest(),'tailWords':words,'countOffsetInExtras':start*4,'count':count,'streamingExportIndices':refs,'verifiedCountedTable':True,'evidence':'Exact terminal int32 counted array; every reference resolves to a LevelStreaming object owned by this World. This decodes the counted-reference region, not all undocumented UWorld tail fields.'})
            for idx in refs:
                p=self.props(idx);world=p.get('WorldAsset',{});asset=world.get('AssetPath',{});value=asset.get('AssetName') if isinstance(asset,dict) else asset;package=value.split('.')[0] if value else None
                flags={k:p[k] for k in p if any(s in k.lower() for s in ['shouldbeloaded','shouldbevisible','initiallyloaded','initiallyvisible','blockonload','disable','streamingvolume'])}
                records.append({'exportIndex':idx,'objectName':self.objname(idx),'class':self.cls(idx),'outer':self.path(self.ref(idx).get('OuterIndex',0)),'worldAsset':value,'package':package,'explicitLoadingProperties':flags,'bShouldBeLoaded':p.get('bShouldBeLoaded'),'bShouldBeVisible':p.get('bShouldBeVisible'),'configurationClassification':'always-loaded class policy' if self.cls(idx)=='LevelStreamingAlwaysLoaded' else 'dynamic runtime-requested; current loaded/visible state not established','levelTransform':p.get('LevelTransform'),'properties':p})
        return records,tables

def decode(package):
    name=package.rsplit('/',1)[1];source=MAPROOT/(package.removeprefix('/Game/')+'.umap');cached=EXISTING/(name+'.json');target=cached if cached.exists() else DECODED/(name+'.json')
    record={'package':package,'name':name,'source':str(source),'decoded':str(target),'usedExistingDecode':cached.exists()}
    if not source.exists():record['error']='Map package is not locally extracted';return record
    for ext in ['.umap','.uexp','.ubulk']:
        path=source.with_suffix(ext)
        if path.exists():record.setdefault('sourceFiles',[]).append({'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path)})
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True);startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        try:
            p=subprocess.run([str(TOOL),'tojson',str(source),str(target),'VER_UE4_27'],capture_output=True,startupinfo=startup,timeout=120)
            record['exitCode']=p.returncode
            if p.returncode or not target.exists():record['error']=(p.stdout+p.stderr).decode(errors='replace')[-3000:]
        except Exception as error:record['error']=str(error)
    if target.exists():record['decodedBytes']=target.stat().st_size;record['decodedSha256']=digest(target)
    print('DECODE '+name+' '+('ERROR' if 'error' in record else 'OK'),flush=True);return record

def integer_refs(value):
    if isinstance(value,int) and not isinstance(value,bool):return [value]
    if isinstance(value,list):return [i for x in value for i in integer_refs(x)]
    if isinstance(value,dict):return [i for x in value.values() for i in integer_refs(x)]
    return []

def summarize(record,web):
    data=read(pathlib.Path(record['decoded']));pkg=Package(data,record['name']);actors=set();levelactorrefs=[]
    for i,e in enumerate(pkg.ex,1):
        if 'LevelExport' in e['$type']:
            refs=e.get('Actors',[]);valid=[x for x in refs if isinstance(x,int) and 0<x<=len(pkg.ex)];actors.update(valid);levelactorrefs.append({'levelExportIndex':i,'slots':len(refs),'nullSlots':refs.count(0),'actorExports':valid})
    components={i for i,e in enumerate(pkg.ex,1) if 'Component' in pkg.cls(i)}
    for i in actors:
        for key,value in pkg.props(i).items():
            if key in ['RootComponent','BlueprintCreatedComponents','InstanceComponents','OwnedComponents']:
                components.update(x for x in integer_refs(value) if x>0 and x<=len(pkg.ex))
    def owner(i):
        seen=set();cur=i
        while cur>0 and cur not in seen:
            if cur in actors:return cur
            seen.add(cur);cur=pkg.ref(cur).get('OuterIndex',0)
        return None
    activecomponents={i for i in components if owner(i)}
    sceneComponents={i for i in activecomponents if any(k in pkg.props(i) for k in ['RelativeLocation','RelativeRotation','RelativeScale3D','AttachParent']) or any(k in pkg.cls(i) for k in ['Scene','Mesh','Light','Camera','Collision','Landscape','Spline','Arrow','Billboard','Particle','Audio','Box','Sphere','Capsule'])}
    transforms=[];meshrefs=[];materialoverrides=[];terrain=[];foliage=[];lighting=[];classcounts=collections.Counter(pkg.cls(i) for i in actors);componentcounts=collections.Counter(pkg.cls(i) for i in activecomponents)
    for i in sorted(sceneComponents):
        p=pkg.props(i);e=pkg.ref(i);own=owner(i);transform={'exportIndex':i,'component':e['ObjectName'],'class':pkg.cls(i),'sourceActor':pkg.path(own),'sourceActorExportIndex':own,'outer':pkg.path(e.get('OuterIndex',0)),'attachParentIndex':p.get('AttachParent',0),'attachParent':pkg.path(p['AttachParent']) if isinstance(p.get('AttachParent'),int) and p['AttachParent'] else None,'attachSocket':p.get('AttachSocketName'),'relativeLocationUE':p.get('RelativeLocation'),'relativeRotationUE':p.get('RelativeRotation'),'relativeScaleUE':p.get('RelativeScale3D'),'absoluteFlags':{k:p[k] for k in ['bAbsoluteLocation','bAbsoluteRotation','bAbsoluteScale'] if k in p},'serializedPropertiesAbsentUseDefaults':True}
        try:
            t,q,s=pkg.world(i);transform['composedComponentTransformUE']={'position':t,'rotationQuaternion':q,'scale':s};transform['worldTransformCaveat']='In level coordinates; absent values use zero/identity. Native/Blueprint template overrides and socket transforms are not applied; LevelStreaming transform is recorded separately.'
        except Exception as error:transform['compositionError']=str(error)
        transform['visibilityProperties']={k:p[k] for k in ['bVisible','bHiddenInGame','bOwnerNoSee','bOnlyOwnerSee','bCastHiddenShadow','Mobility'] if k in p}
        transform['visibilityCaveat']='Absent flags do not establish actual rendered visibility; owner/template/runtime state can override.'
        transforms.append(transform)
    for i in sorted(activecomponents):
        p=pkg.props(i);cls=pkg.cls(i);own=owner(i)
        for key in ['StaticMesh','SkeletalMesh']:
            ref=p.get(key)
            if isinstance(ref,int) and ref:
                path=pkg.path(ref);meshrefs.append({'componentExportIndex':i,'sourceActor':pkg.path(own),'component':pkg.objname(i),'class':cls,'property':key,'assetReference':path,'referenceIndex':ref,'referencedClass':pkg.ref(ref).get('ClassName') if ref<0 else pkg.cls(ref),'hasInstanceDataProperties':[k for k in p if 'Instance' in k or 'Spline' in k]})
        refs=integer_refs(p.get('OverrideMaterials',[]))
        if refs:materialoverrides.append({'componentExportIndex':i,'sourceActor':pkg.path(own),'slots':[pkg.path(x) if x else None for x in refs]})
        if 'Light' in cls or 'ReflectionCapture' in cls or 'PostProcess' in cls:
            lighting.append({'componentExportIndex':i,'class':cls,'sourceActor':pkg.path(own),'properties':{k:v for k,v in p.items() if any(s.lower() in k.lower() for s in ['Intensity','LightColor','Temperature','Radius','Shadow','Mobility','Lightmass','Cubemap','Source','Indirect','Affect','Visibility','Bloom','Exposure','Atmosphere','Sky','Settings'])}})
        if 'Landscape' in cls:
            terrain.append({'componentExportIndex':i,'class':cls,'sourceActor':pkg.path(own),'properties':{k:v for k,v in p.items() if any(s.lower() in k.lower() for s in ['SectionBase','ComponentSize','Subsection','Heightmap','Weightmap','Material','Collision','Scale','RelativeLocation','LOD'])},'extrasBytes':len(base64.b64decode(pkg.ref(i).get('Extras',{}).get('$value','')))})
        if any(s in cls for s in ['Foliage','InstancedStaticMesh','HierarchicalInstanced']):
            instanceprops={k:v for k,v in p.items() if any(s in k for s in ['Instance','Cluster','StaticMesh','Density','Cull'])};foliage.append({'componentExportIndex':i,'class':cls,'sourceActor':pkg.path(own),'properties':instanceprops,'extrasBytes':len(base64.b64decode(pkg.ref(i).get('Extras',{}).get('$value',''))),'instanceCountStatus':'Only serialized property counts are reliable; binary extras may contain unparsed instances.'})
    for i in actors:
        if 'Foliage' in pkg.cls(i):foliage.append({'actorExportIndex':i,'class':pkg.cls(i),'sourceActor':pkg.path(i),'properties':pkg.props(i),'extrasBytes':len(base64.b64decode(pkg.ref(i).get('Extras',{}).get('$value','')))})
    materials=[pkg.path(-i) for i,e in enumerate(pkg.im,1) if e.get('ClassName') in ['Material','MaterialInstanceConstant','MaterialInstanceDynamic']]
    meshimports=[pkg.path(-i) for i,e in enumerate(pkg.im,1) if e.get('ClassName') in ['StaticMesh','SkeletalMesh']]
    embeddedmaterials=[pkg.path(i) for i,e in enumerate(pkg.ex,1) if any(s in pkg.cls(i) for s in ['MaterialInstance','LandscapeMaterial'])]
    streams,tables=pkg.streamings()
    for s in streams:s['sourcePackage']=record['package']
    name=record['name'];webobjects=[o for o in web['objects'] if o.get('sourceActor','').startswith(name+'/')];webpairs={(o['sourceActor'],o.get('sourceComponent')) for o in webobjects if o.get('sourceComponent')};websplinecomponents={c for o in webobjects for c in o.get('sourceComponents',[])}
    meshcovered=[m for m in meshrefs if (m['sourceActor'],m['component']) in webpairs or m['component'] in websplinecomponents]
    raw=[{'exportIndex':i,'name':e['ObjectName'],'class':pkg.cls(i),'type':e['$type']} for i,e in enumerate(pkg.ex,1) if 'RawExport' in e['$type']]
    environmentActors=[{'exportIndex':i,'class':pkg.cls(i),'name':pkg.objname(i),'properties':pkg.props(i)} for i in actors if any(s in pkg.cls(i) for s in ['PostProcess','Fog','SkyLight','DirectionalLight','ReflectionCapture','WorldSettings'])]
    detail={'package':record['package'],'actors':[{'exportIndex':i,'name':pkg.objname(i),'class':pkg.cls(i),'rootComponentIndex':pkg.props(i).get('RootComponent'),'rootComponent':pkg.path(pkg.props(i)['RootComponent']) if isinstance(pkg.props(i).get('RootComponent'),int) and pkg.props(i)['RootComponent'] else None,'visibilityProperties':{k:v for k,v in pkg.props(i).items() if k in ['bHidden','bHiddenInGame','bActorEnableCollision','bIsEditorOnlyActor']}} for i in sorted(actors)],'componentTransforms':transforms,'meshReferences':meshrefs,'materialOverrides':materialoverrides,'lightsAndReflection':lighting,'environmentActors':environmentActors,'terrain':terrain,'foliageAndInstancing':foliage,'streamingRecords':streams,'streamingTables':tables,'levelActorReferenceTables':levelactorrefs,'materialImports':materials,'meshImports':meshimports,'embeddedMaterialExports':embeddedmaterials,'rawExports':raw}
    detailpath=OUT/'levels'/(name+'.json');write(detailpath,detail)
    counts={'actorInstances':len(actors),'allExports':len(pkg.ex),'actorOwnedComponents':len(activecomponents),'allComponentNamedExportsIncludingTemplates':len(components),'sceneComponentTransforms':len(transforms),'staticMeshComponents':sum('StaticMeshComponent' in pkg.cls(i) or pkg.cls(i)=='SplineMeshComponent' for i in activecomponents),'skeletalMeshComponents':sum('SkeletalMeshComponent' in pkg.cls(i) for i in activecomponents),'splineMeshComponents':sum(pkg.cls(i)=='SplineMeshComponent' for i in activecomponents),'resolvedMeshComponentReferences':len(meshrefs),'uniqueReferencedMeshAssets':len(set(m['assetReference'] for m in meshrefs)),'meshImports':len(meshimports),'uniqueMaterialImports':len(set(materials)),'embeddedMaterialInstances':len(embeddedmaterials),'componentsWithMaterialOverrides':len(materialoverrides),'nonNullMaterialOverrideSlots':sum(sum(x is not None for x in m['slots']) for m in materialoverrides),'lightComponents':sum('LightComponent' in pkg.cls(i) for i in activecomponents),'reflectionCaptureComponents':sum('ReflectionCapture' in pkg.cls(i) for i in activecomponents),'postProcessComponents':sum('PostProcess' in pkg.cls(i) for i in activecomponents),'landscapeActors':sum('Landscape' in pkg.cls(i) for i in actors),'landscapeComponents':sum(pkg.cls(i)=='LandscapeComponent' for i in activecomponents),'landscapeCollisionComponents':sum('Landscape' in pkg.cls(i) and 'Collision' in pkg.cls(i) for i in activecomponents),'foliageActors':sum('Foliage' in pkg.cls(i) for i in actors),'foliageOrInstancedMeshComponents':sum(any(s in pkg.cls(i) for s in ['Foliage','InstancedStaticMesh','HierarchicalInstanced']) for i in activecomponents),'rawExports':len(raw)}
    result={**record,'counts':counts,'actorClassCounts':dict(classcounts.most_common()),'componentClassCounts':dict(componentcounts.most_common()),'details':str(detailpath.relative_to(OUT)),'webCoverage':{'manifestObjectsAttributed':len(webobjects),'resolvedOriginalMeshComponentsRepresented':len(meshcovered),'originalResolvedMeshComponents':len(meshrefs),'meshComponentCoveragePercent':100*len(meshcovered)/len(meshrefs) if meshrefs else None,'materialOverrideReconstruction':'Not implemented in current city exporter','originalLightingTerrainFoliageReconstruction':'No original light, landscape heightfield or foliage instance data imported into current Web manifest'}}
    counts.update(postProcessVolumeActors=sum(pkg.cls(i)=='PostProcessVolume' for i in actors),fogActors=sum('Fog' in pkg.cls(i) for i in actors),skyBlueprintActors=sum(pkg.cls(i)=='BP_Sky_C' for i in actors),explicitHiddenComponents=sum(pkg.props(i).get('bHiddenInGame') is True or pkg.props(i).get('bVisible') is False for i in activecomponents),explicitHiddenActors=sum(pkg.props(i).get('bHidden') is True for i in actors),componentsWithSocketAttachment=sum(bool(pkg.props(i).get('AttachSocketName')) for i in activecomponents))
    print('AUDIT '+name+' actors='+str(len(actors))+' meshes='+str(len(meshrefs))+' web='+str(len(meshcovered)),flush=True)
    return result,streams,set(meshimports),set(materials)

def main():
    OUT.mkdir(exist_ok=True);mainpkg='/Game/-HeroGame/Maps/MainLevel';mainrecord=decode(mainpkg);main=Package(read(pathlib.Path(mainrecord['decoded'])),'MainLevel');streams,tables=main.streamings();write(OUT/'mainlevel-streaming-table.json',{'records':streams,'tables':tables})
    packages=sorted(set(s['package'] for s in streams if s['package']));records=[mainrecord]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records+=list(pool.map(decode,packages))
    write(OUT/'world-decode-manifest.json',{'tool':str(TOOL),'sha256':digest(TOOL),'engineVersion':'VER_UE4_27','records':records})
    web=read(ROOT/'public/assets/city/manifest.json');results=[];allmeshes=set();allmaterials=set();nested=[]
    knownPackages={r['package'] for r in records};cursor=0
    while cursor<len(records):
        record=records[cursor];cursor+=1
        if 'error' in record:results.append(record);continue
        result,sub,meshes,materials=summarize(record,web);results.append(result);allmeshes|=meshes;allmaterials|=materials;nested+=sub
        for child in sub:
            if child.get('package') and child['package'] not in knownPackages:
                knownPackages.add(child['package']);new=decode(child['package']);new['referenceDepth']='transitive';records.append(new)
    totals={key:sum(r.get('counts',{}).get(key,0) for r in results) for key in results[0]['counts']};webcovered=sum(r.get('webCoverage',{}).get('resolvedOriginalMeshComponentsRepresented',0) for r in results)
    report={'scope':'MainLevel persistent package plus all 33 packages actually referenced by its serialized UWorld StreamingLevels array; stored content inventory, not claim of simultaneous runtime visibility.','method':'repak extraction + UAssetGUI/UAssetAPI static cooked UE4.27 decoding; not REA native decompiler output or runtime capture.','mainLevel':mainpkg,'streaming':{'tableEvidence':'mainlevel-streaming-table.json','referencedPackages':len(packages),'alwaysLoaded':[s for s in streams if s['class']=='LevelStreamingAlwaysLoaded'],'dynamic':[s for s in streams if s['class']!='LevelStreamingAlwaysLoaded'],'explicitLoadedVisibleFlagCount':sum(bool(s['explicitLoadingProperties']) for s in streams),'runtimeState':'Unknown; all omitted flags are reported null, not invented false/true. AlwaysLoaded classification derives from actual class.'},'levels':results,'totals':totals,'uniqueAssetsAcrossReferencedWorld':{'meshImports':len(allmeshes),'materialImports':len(allmaterials),'meshes':sorted(allmeshes),'materials':sorted(allmaterials)},'webComparison':{'cityManifestSha256':digest(ROOT/'public/assets/city/manifest.json'),'webAssetEntries':len(web['assets']),'webSceneObjects':len(web['objects']),'representedSourceMeshComponents':webcovered,'totalResolvedSourceMeshComponents':totals['resolvedMeshComponentReferences'],'componentCoveragePercent':100*webcovered/max(1,totals['resolvedMeshComponentReferences']),'representedLevels':[r['name'] for r in results if r.get('webCoverage',{}).get('resolvedOriginalMeshComponentsRepresented')],'missingLevels':[r['name'] for r in results if r.get('counts',{}).get('resolvedMeshComponentReferences') and not r.get('webCoverage',{}).get('resolvedOriginalMeshComponentsRepresented')]},'nestedStreamingReferences':nested,'limitations':['Static scene packages are not the set visible at one runtime moment; dynamic load/unload logic needs Blueprint/native runtime tracing.','Mesh/material counts include resolved references/imports, not total triangles or pixels; inherited Blueprint/template meshes and runtime-spawned meshes can be absent.','Foliage/HISM binary instance payloads may remain in Extras; instance counts are not guessed.','Material imports are direct map references; full per-mesh material/texture/shader dependency closure is outside this count.','Component transforms retain exact serialized local values and composed parent-chain values, but socket/template transforms and level-streaming transforms require separate application.']}
    report['scope']='MainLevel persistent package + its 33 directly referenced streaming packages + recursively discovered stored streaming-package references. This closure is an inventory, not proof nested streams auto-load or all levels are simultaneously visible.'
    report['streaming']['transitiveAdditionalPackages']=sorted(knownPackages-set(packages)-{mainpkg})
    report['officialStreamingSemanticsSource']='https://dev.epicgames.com/documentation/unreal-engine/level-streaming-overview?application_version=4.27'
    report['limitations'].append('The 11 InstancedStaticMeshComponents found in Park reference paths/walls/stairs. They are not automatically classified as foliage; absence of InstancedFoliageActor does not imply absence of trees, which may be merged/static meshes.')
    write(OUT/'world-decode-manifest.json',{'tool':str(TOOL),'sha256':digest(TOOL),'engineVersion':'VER_UE4_27','records':records})
    write(OUT/'world-coverage.json',report)
    print('TOTAL '+json.dumps({'levels':len(results),'totals':totals,'web':report['webComparison']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
