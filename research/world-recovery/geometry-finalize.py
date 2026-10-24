"""Retain omitted socket component metadata and report final geometry recovery boundaries."""
import importlib.util, pathlib, collections, json
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
path=g.OUT/'geometry-manifest.json';d=g.READ(path);rows,_=g.inventory(True)
allrefs={r['record']['name']+':'+str(m['componentExportIndex']):(r,m) for r in rows for m in r['detail']['meshReferences']}
for gap in d['gaps']:
    row,mesh=allrefs[gap['id']];idx=mesh['componentExportIndex'];t=next(x for x in row['detail']['componentTransforms'] if x['exportIndex']==idx)
    gap['transformBeforeSocketUE']=t['composedComponentTransformUE']
    if 'templateRecovery' in mesh:gap['materialOverrides']=mesh['templateRecovery']['materialOverrides']
    else:
        ov=next((x['slots'] for x in row['detail']['materialOverrides'] if x['componentExportIndex']==idx),[])
        gap['materialOverrides']=[{'slotIndex':i,'material':g.package_ref(v)} for i,v in enumerate(ov)]
g.WRITE(path,d)
summary=g.READ(g.EVID/'geometry-summary.json');summary['manifestSha256']=g.HASH(path);summary['remainingSocketNames']=dict(collections.Counter(x['socket'] for x in d['gaps']));summary['templateResolutionSummary']=d['templateResolutionSummary'];g.WRITE(g.EVID/'geometry-summary.json',summary);g.WRITE(g.EVID/'geometry-gaps.json',d['gaps'])
# Check every originally serialized override is still represented (including omitted socket objects).
represented={}
for level in d['levels']:
    for obj in level['objects']:
        sources=obj.get('sourceComponents') or [obj['source']]
        for source in sources:represented[level['id']+':'+str(source['exportIndex'])]=obj['materialOverrides']
for gap in d['gaps']:represented[gap['id']]=gap['materialOverrides']
checks=0;original_nonnull=0;embedded=0
for row in rows:
    for override in row['detail']['materialOverrides']:
        key=row['record']['name']+':'+str(override['componentExportIndex']);got=represented.get(key)
        assert got is not None,(key,'Component overrides dropped')
        assert len(got)==len(override['slots']),(key,'Override slot count changed')
        for slot,raw in enumerate(override['slots']):
            material=got[slot]['material'];assert (raw is None)==(material is None),(key,slot,'Null override changed')
            if raw is not None:
                original_nonnull+=1
                if raw.startswith('/'):
                    assert material==g.package_ref(raw),(key,slot,'External reference changed')
                else:
                    assert material.get('isEmbedded') and material['objectPath']==raw,(key,slot,'Embedded reference dropped')
                    embedded+=1
            checks+=1
g.WRITE(g.EVID/'geometry-override-validation.json',{'status':'passed','originalSerializedOverrideSlotsChecked':checks,'originalNonNullOverridesPreserved':original_nonnull,'embeddedOriginalOverridesPreserved':embedded,'scope':'All 41 map packages; per original component, before instancing expansion and batching.'})
print(json.dumps({'overrideSlotsChecked':checks,'nonNull':original_nonnull,'embedded':embedded,'gaps':len(d['gaps']),'totals':d['totals']}))
assets={x['id']:x for x in d['assets']};ambiguities=[]
for level in d['levels']:
    for obj in level['objects']:
        asset=assets[obj['assetId']];overrides={x['slotIndex']:x['material'] for x in obj['materialOverrides']}
        for section in asset['gltfMaterials']:
            candidates=section['sourceSlotCandidates']
            if len(candidates)<2:continue
            materials=[overrides.get(i) or asset['sourceMaterialSlots'][i]['material'] for i in candidates]
            if any(x!=materials[0] for x in materials):ambiguities.append({'id':obj['id'],'section':section['materialIndex'],'candidates':candidates,'materials':materials})
ambiguityfile=g.EVID/'geometry-skeletal-slot-ambiguities.json';originalfile=g.EVID/'geometry-skeletal-slot-original-ambiguities.json'
if ambiguityfile.exists() and not originalfile.exists():g.WRITE(originalfile,g.READ(ambiguityfile))
g.WRITE(ambiguityfile,ambiguities)
