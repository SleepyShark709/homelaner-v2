"""Preserve map-owned MID identities/parameters without re-exporting textures."""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json
spec=importlib.util.spec_from_file_location('restore',Path(__file__).with_name('restore-world-materials.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def key(pkg,i):return f'{pkg}#export:{i}'
def class_name(doc,e):
 c=e.get('ClassIndex',0);return doc['Imports'][-c-1]['ObjectName'] if c<0 else None
def path(doc,i):
 if not i:return ''
 e=doc['Exports'][i-1] if i>0 else doc['Imports'][-i-1];parent=path(doc,e.get('OuterIndex',0))
 return parent+'/'+e['ObjectName'] if parent else e['ObjectName']
def orm_signature(mat):
 channels={k:({f:c[f] for f in ['texturePackage','url','colorSpace','channel']} if (c:=mat['channels'][k]) else None) for k in ['occlusion','roughness','metallic']}
 return json.dumps({'channels':channels,'factors':{k:mat['factors'].get(k) for k in ['roughness','metallic']}},sort_keys=True)
def main():
 manifest=m.read(m.OUT/'material-manifest.json');base={k:v for k,v in manifest['materials'].items() if '#export:' not in k}
 maps=m.read(m.ROOT/'research/rea-audit/world-coverage.json')['levels']
 maps+=m.read(m.ROOT/'research/rea-audit/all-map-inventory.json')['supplementalMaps']
 raw={};embedded={};overrides=[];level_stats=[];original_ref=m.ref;original_sha=m.sha
 for level in maps:
  pkg=level['package'];file=Path(level['decoded']);doc=m.read(file);filehash=original_sha(file)
  def mapped_ref(current,index):
   if current is doc and index>0:return key(pkg,index)
   return original_ref(current,index)
  m.ref=mapped_ref
  m.sha=lambda p: filehash if Path(p)==file else original_sha(p)
  stats={'mapPackage':pkg,'source':str(file),'sourceSha256':filehash,'embeddedMaterialTypes':collections.Counter(),'overrideComponents':0,'nonNullSlots':0,'embeddedSlots':0,'externalSlots':0}
  for i,e in enumerate(doc['Exports'],1):
   cls=class_name(doc,e);data=e.get('Data',[])
   if cls in ['MaterialInstanceDynamic','MaterialInstanceConstant','LandscapeMaterialInstanceConstant','Material']:
    identity=key(pkg,i);raw[identity]=m.parse_material(identity,file,doc,i-1,e)
    raw[identity]['source'].update(ownerPackage=pkg,exportIndex=i,objectPath=path(doc,i),sourceFiles=level['sourceFiles'])
    snapshot=[];unmapped=[]
    for j,p in enumerate(data):
     if p['Name'] in ['ScalarParameterValues','VectorParameterValues','TextureParameterValues']:
      for z,param in enumerate(m.fields(p)):
       info=m.prop(param,'ParameterInfo');association=m.value(m.prop(info,'Association'),doc);index=m.value(m.prop(info,'Index'),doc)
       name=m.value(m.prop(info,'Name'),doc);v=m.value(m.prop(param,'ParameterValue'),doc)
       snapshot.append({'kind':p['Name'],'name':name,'association':association,'index':index,'value':v,
        'pointer':f'/Exports/{i-1}/Data/{j}/Value/{z}','rawParameterInfo':info})
       if association not in [None,'GlobalParameter'] or index not in [None,-1]:
        kind={'ScalarParameterValues':'scalar','VectorParameterValues':'vector','TextureParameterValues':'texture'}[p['Name']]
        raw[identity]['parameters'][kind].pop(name,None);unmapped.append({'reason':'non-global parameter association cannot be collapsed into PBR by name','parameter':snapshot[-1]})
    known={'Parent','ScalarParameterValues','VectorParameterValues','TextureParameterValues','BasePropertyOverrides','CachedExpressionData'}
    properties=[{'name':p['Name'],'value':m.value(p,doc),'pointer':f'/Exports/{i-1}/Data/{j}'} for j,p in enumerate(data) if p['Name'] not in known]
    embedded[identity]={'isEmbedded':True,'ownerPackage':pkg,'exportIndex':i,'objectName':e['ObjectName'],'objectPath':path(doc,i),'className':cls,
      'parentReferenceIndex':(m.prop(data,'Parent') or {}).get('Value'),'resolvedParent':raw[identity]['parent'],'sourceParameters':snapshot,'remainingProperties':properties,'unmappedParameterAssociations':unmapped,
      'parameterSnapshotMeaning':'Serialized cooked map instance values; later runtime mutations not simulated'}
    stats['embeddedMaterialTypes'][cls]+=1
   override=m.prop(data,'OverrideMaterials')
   if override:
    slots=[];stats['overrideComponents']+=1
    for j,v in enumerate(m.fields(override)):
     idx=v.get('Value',0);target=mapped_ref(doc,idx) if idx else None
     slots.append({'slotIndex':j,'materialPackage':target,'referenceIndex':idx,'referenceKind':'embedded' if idx>0 else 'import' if idx<0 else 'null',
       'rawReference':path(doc,idx) if idx else None,'sourcePointer':f'/Exports/{i-1}/Data/{data.index(override)}/Value/{j}'})
     if idx:stats['nonNullSlots']+=1
     if idx>0:stats['embeddedSlots']+=1
     if idx<0:stats['externalSlots']+=1
    overrides.append({'levelPackage':pkg,'componentExportIndex':i,'sourceActor':path(doc,e.get('OuterIndex',0)),'component':e['ObjectName'],'slots':slots})
  level_stats.append(stats);print(pkg,dict(stats['embeddedMaterialTypes']),'embedded slots',stats['embeddedSlots'],flush=True)
 m.ref=original_ref;m.sha=original_sha
 cache=dict(base);orm_cache={orm_signature(v):v['packedPBR'] for v in base.values() if v.get('packedPBR')};unresolved_parents=[]
 for identity,src in raw.items():
  parent=src['parent']
  if parent and parent not in raw and parent not in base:unresolved_parents.append({'material':identity,'parent':parent,'source':src['source']})
 for identity in raw:
  descriptor=m.build_material(identity,raw,manifest['textures'],cache)
  descriptor['embeddedInstance']=embedded[identity]
  descriptor['source']['isEmbedded']=True
  used={}
  for role,c in descriptor['channels'].items():
   if c:used.setdefault(c['evidence']['pointer'],[]).append('texture:'+role) if c['evidence']['package']==identity else None
  for role,names in [('roughness',['Roughness']),('metallic',['Metallic','Metalness']),('opacity',['Opacity']),('baseColor',['Base color','BaseColor','Base Color','Color','Colour','ColorGlass','Glass_Color']),('emissive',['EmissiveColor','Emissive Color','Emissive01'])]:
   kind='vector' if role in ['baseColor','emissive'] else 'scalar'
   selected=next((descriptor['parameters'][kind][n] for n in names if n in descriptor['parameters'][kind]),None)
   if selected and descriptor['factors'][role] is not None and selected['evidence']['package']==identity:used.setdefault(selected['evidence']['pointer'],[]).append('factor:'+role)
  for selected in descriptor.get('emissiveControlEvidence',[]):
   if selected['evidence']['package']==identity:used.setdefault(selected['evidence']['pointer'],[]).append('factor:emissive-control')
  for parameter in embedded[identity]['sourceParameters']:
   parameter['projectionUses']=used.get(parameter['pointer'],[])
   parameter['status']='partial-pbr-projection' if parameter['projectionUses'] else 'retained-not-mapped'
  for p in embedded[identity]['unmappedParameterAssociations']:descriptor['unsupported'].append(p['reason']+': '+str(p['parameter']['name']))
  if raw[identity]['parent'] and raw[identity]['parent'] not in raw and raw[identity]['parent'] not in base:descriptor['unsupported'].append('Original parent missing; explicit unresolved parent, not silent default inheritance')
  signature=orm_signature(descriptor)
  if signature in orm_cache:
   descriptor['packedPBR']=copy.deepcopy(orm_cache[signature]);descriptor['packedPBR']['reusedForIdenticalInputs']=True
  elif any(descriptor['channels'][k] for k in ['roughness','metallic','occlusion']):
   original_key=descriptor['sourcePackage'];descriptor['sourcePackage']='/Embedded/'+hashlib.sha256(original_key.encode()).hexdigest()
   m.pack_orm(descriptor,manifest['textures']);descriptor['sourcePackage']=original_key
   if descriptor['packedPBR']:orm_cache[signature]=descriptor['packedPBR']
 for descriptor in cache.values():m.pack_opacity(descriptor)
 manifest['materials']=cache;manifest['instanceOverrides']=overrides
 summary={'mapCount':len(maps),'baseMaterialDescriptors':len(base),'embeddedMaterialDescriptors':len(raw),'totalMaterialDescriptors':len(cache),
  'embeddedTypes':dict(collections.Counter(e['className'] for e in embedded.values())),
  'originalInstanceParameterEntries':sum(len(e['sourceParameters']) for e in embedded.values()),
  'instanceParameterStatuses':dict(collections.Counter(p['status'] for e in embedded.values() for p in e['sourceParameters'])),
  'overrideComponents':len(overrides),'nonNullOverrideSlots':sum(s['nonNullSlots'] for s in level_stats),
  'embeddedOverrideSlots':sum(s['embeddedSlots'] for s in level_stats),'externalOverrideSlots':sum(s['externalSlots'] for s in level_stats),
  'unresolvedParents':unresolved_parents,'missingEmbeddedOverrideDescriptors':[{'map':r['levelPackage'],'component':r['componentExportIndex'],'slot':s} for r in overrides for s in r['slots'] if s['referenceKind']=='embedded' and s['materialPackage'] not in cache],
  'textureReexported':False,'identityContract':'mapPackage#export:UE_1_based_export_index',
  'geometryRootCause':'Original stored MID references mainly belong to components without explicit meshes. Original geometry exporter omitted these components, not silently nulling an included override.',
  'limitations':['Serialized instance parameters retained; runtime changes not replayed.','Adding MID descriptors does not restore absent Blueprint/template mesh components.','All existing shader limitations remain; non-global parameter associations are retained but not guessed into PBR.']}
 summary['scopes']={name:{'maps':len(rows),'nonNullOverrideSlots':sum(x['nonNullSlots'] for x in rows),'embeddedOverrideSlots':sum(x['embeddedSlots'] for x in rows)} for name,rows in [('original35',level_stats[:35]),('supplemental6',level_stats[35:])]}
 manifest['embeddedMaterialRecovery']=summary
 m.write(m.OUT/'material-manifest.json',manifest)
 m.write(m.WORK/'material-embedded-instances.json',{'summary':summary,'levels':level_stats,'instances':embedded})
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 assert not summary['missingEmbeddedOverrideDescriptors'],summary['missingEmbeddedOverrideDescriptors']
if __name__=='__main__':main()
