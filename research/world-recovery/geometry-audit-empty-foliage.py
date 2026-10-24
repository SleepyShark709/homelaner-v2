"""Bounded TestLevel cooked foliage audit; verifies complete original export byte range."""
import base64,hashlib,importlib.util,pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
decoded=g.AUDIT/'decoded-other-maps/TestLevel.json';d=g.READ(decoded);p=g.a.Package(d,'TestLevel');pkg='/Game/-HeroGame/Maps/TestLevel'
source=ROOT/'research/exports/city-unpacked/UNDEFEATED/Content/-HeroGame/Maps/TestLevel.umap';uexp=source.with_suffix('.uexp');data=uexp.read_bytes()
records=[]
for idx,e in enumerate(p.ex,1):
    if p.cls(idx)!='InstancedFoliageActor':continue
    offset=e['SerialOffset']-source.stat().st_size;raw=data[offset:offset+e['SerialSize']];assert len(raw)==e['SerialSize']==45
    def fname(at):
        i,n=struct.unpack_from('<ii',raw,at);assert 0<=i<len(d['NameMap']) and n==0;return d['NameMap'][i]
    assert fname(0)=='RootComponent' and fname(8)=='ObjectProperty'
    size,array=struct.unpack_from('<ii',raw,16);assert (size,array,raw[24])==(4,0,0)
    root=struct.unpack_from('<i',raw,25)[0];assert root==p.props(idx)['RootComponent'] and fname(29)=='None'
    native=base64.b64decode(e['Extras']['$value']);assert native==raw[37:] and len(native)==8
    guid_present,map_count=struct.unpack('<ii',native);assert guid_present==0 and map_count==0
    children=[{'exportIndex':i,'class':p.cls(i),'object':x['ObjectName'],'properties':p.props(i)} for i,x in enumerate(p.ex,1) if x['OuterIndex']==idx]
    assert len(children)==1 and children[0]['exportIndex']==root and children[0]['class']=='SceneComponent'
    assert not any('InstancedStaticMeshComponent' in p.cls(i) or 'FoliageInstanced' in p.cls(i) for i in range(1,len(p.ex)+1))
    props=p.props(idx);records.append({'sourcePackage':pkg,'exportIndex':idx,'actor':e['ObjectName'],'objectPath':p.path(idx),'class':p.cls(idx),'templateIndex':e['TemplateIndex'],'templatePath':p.path(e['TemplateIndex']),'scope':'supplemental; runtime use not proven','serialOffsetInCombinedPackage':e['SerialOffset'],'offsetInUexp':offset,'serializedBytes':len(raw),'rawHex':raw.hex(),'rawSha256':hashlib.sha256(raw).hexdigest(),'taggedProperties':props,'nativeFields':[{'offsetInExport':37,'field':'UObject.bHasGuid','value':guid_present,'bytes':4},{'offsetInExport':41,'field':'AInstancedFoliageActor.FoliageInfos.Num','value':map_count,'bytes':4}],'nativeBytesConsumed':8,'nativeBytesRemaining':0,'foliageTypesSerialized':0,'foliageInstancesSerialized':0,'children':children,'explicitActorHidden':props.get('bHidden'),'explicitActorHiddenInGame':props.get('bHiddenInGame'),'visibilityConclusion':'No actor visibility mutation is inferred; no render instances are stored irrespective of visibility.','runtimeGeneration':'not observed or executed; an empty cooked map does not prove no later runtime generation'})
assert len(records)==1
report={'status':'verified-original-empty-foliage-map','sourceFiles':[{'path':str(f),'bytes':f.stat().st_size,'sha256':g.HASH(f)} for f in (source,uexp,decoded)],'records':records,'summary':{'serializedFoliageActors':1,'emptyFoliageActors':1,'serializedFoliageTypeEntries':0,'serializedFoliageInstances':0,'addedGeometryObjects':0,'unparsedNativeBytes':0},'formatSources':[{'url':'https://github.com/FabianFG/CUE4Parse/blob/master/CUE4Parse/UE4/Assets/Exports/Actor/AInstancedFoliageActor.cs','snapshot':'research/world-recovery/geometry-CUE4Parse-AInstancedFoliageActor.cs','sha256':g.HASH(g.EVID/'geometry-CUE4Parse-AInstancedFoliageActor.cs')}],'conclusion':'Earlier unresolved-foliage wording is superseded: the sole supplemental TestLevel actor contains an exactly empty cooked FoliageInfos map. No transforms or models can be added from absent entries. Runtime foliage creation remains outside this static audit.'}
g.WRITE(g.EVID/'geometry-foliage-recovery.json',report)
manifest=g.READ(g.OUT/'geometry-manifest.json');manifest['foliageRecovery']={'status':report['status'],**report['summary'],'evidence':'research/world-recovery/geometry-foliage-recovery.json','runtimeGenerationProven':False}
manifest['limitations']=[s for s in manifest['limitations'] if 'Native foliage actor payload in supplemental TestLevel' not in s and not s.startswith('The supplemental TestLevel foliage actor stores an empty')]
manifest['limitations'].append('The supplemental TestLevel foliage actor stores an empty FoliageInfos map (zero types/instances), verified through the full native export. Runtime foliage generation is not observed or executed.')
g.WRITE(g.OUT/'geometry-manifest.json',manifest)
print(report['summary'])
