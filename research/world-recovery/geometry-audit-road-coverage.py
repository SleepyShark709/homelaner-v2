"""Independent complete spline UV/section/material dependency coverage, no shader claim."""
import collections,importlib.util,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
world=g.READ(g.OUT/'geometry-manifest.json');materials=g.READ(g.OUT/'material-manifest.json');assets={x['id']:x for x in world['assets']};base={x['sourcePackage']:x for x in g.READ(g.EVID/'geometry-base-assets.json')}
cache={};errors=[];uvpoints=0;sourceuvpoints=0;original=set();materialkeys=set();objects=[]
def geometry(ident):
    if ident not in cache:
        path=g.OUT/'meshes'/ident/'mesh.gltf';d=g.READ(path);bs=[(path.parent/x['uri']).read_bytes() for x in d['buffers']]
        cache[ident]=(d,[{**p,'values':{k:g.m.accessor(d,bs,v) for k,v in p['attributes'].items() if k.startswith('TEXCOORD')}} for m in d['meshes'] for p in m['primitives']])
    return cache[ident]
for level in world['levels']:
    for obj in level['objects']:
        if not obj['geometryMode'].startswith('spline'):continue
        asset=assets[obj['assetId']];d,prims=geometry(obj['assetId']);sourcebase=base[asset['sourcePackage']];_,baseprims=geometry(sourcebase['id']);original.add(asset['sourcePackage'])
        overrides={x['slotIndex']:x['material'] for x in obj['materialOverrides']};effective=[]
        for p in prims:
            assert 'TEXCOORD_0' in p['values']
            for values in p['values'].values():assert all(math.isfinite(x) for uv in values for x in uv)
            mapping=asset['gltfMaterials'][p['material']];slots=mapping['sourceSlotCandidates'];assert len(slots)==1
            slot=slots[0];mat=overrides.get(slot) or asset['sourceMaterialSlots'][slot]['material'];assert mat
            assert mat['package'] in materials['materials'];materialkeys.add(mat['package']);effective.append({'section':p['material'],'originalSlot':slot,'material':mat['package'],'uvChannels':list(p['values'])})
        if obj['geometryMode']=='spline-batch':
            lookup={(p['material'],tuple(sorted(p['attributes']))):p for p in prims}
            sources=obj['sourceComponents']
            for source in sources:
                _,sps=geometry(source['bakedAssetId']);assert len(sps)==len(baseprims)
                for sp,bp,sec in zip(sps,baseprims,source['sections']):
                    k=sec['destinationGroupKey'];dst=lookup[(k[0],tuple(k[1]))]
                    for uv,values in sp['values'].items():
                        assert values==bp['values'][uv],(source['id'],uv,'baking changed original UV')
                        assert values==dst['values'][uv][sec['firstVertex']:sec['firstVertex']+len(values)],(source['id'],uv,'batch changed original UV')
                        uvpoints+=len(values);sourceuvpoints+=len(values)
        else:
            sources=[obj]
            for sp,bp in zip(prims,baseprims):
                for uv,values in sp['values'].items():assert values==bp['values'][uv];sourceuvpoints+=len(values)
        objects.append({'id':obj['id'],'level':level['id'],'sourcePackage':asset['sourcePackage'],'sourceComponentCount':len(sources),'sections':effective})
matrecords=[]
for key in sorted(materialkeys):
    m=materials['materials'][key];textures=[]
    for name,item in m.get('parameters',{}).get('texture',{}).items():
        texture=item.get('value')
        if not texture:continue
        t=materials['textures'].get(texture);path=ROOT/'public'/t['url'].lstrip('/') if t and t.get('url') else None
        textures.append({'parameter':name,'package':texture,'status':t.get('status') if t else None,'url':t.get('url') if t else None,'fileExists':bool(path and path.exists())})
        if not path or not path.exists():errors.append({'material':key,'missingTexture':texture})
    matrecords.append({'package':key,'baseMaterial':m['baseMaterial'],'status':m.get('status'),'baseColorChannel':m.get('channels',{}).get('baseColor'),'shaderRecovery':m.get('shaderRecovery'),'textures':textures})
result={'scope':'All recovered SplineMesh components; no name-based road selection; includes sidewalks/curbs if original component is SplineMesh. No runtime shading or pixel-equivalence claim.','manifestSha256':g.HASH(g.OUT/'geometry-manifest.json'),'materialManifestSha256':g.HASH(g.OUT/'material-manifest.json'),'summary':{'renderObjects':len(objects),'originalSplineComponents':sum(x['sourceComponentCount'] for x in objects),'originalMeshPackages':len(original),'effectiveMaterials':len(materialkeys),'originalToBakedUVPointsExactlyEqual':sourceuvpoints,'bakedToBatchedUVPointsExactlyEqual':uvpoints,'missingTextureFiles':len(errors)},'objects':objects,'materials':matrecords,'errors':errors,'conclusion':'All examined original UV channels and exact native section/material overrides are preserved. Any partial shader projection listed is a material/runtime boundary, not evidence of missing road geometry or UV.'}
g.WRITE(g.EVID/'geometry-road-coverage.json',result);print(result['summary']);print([(x['package'],x['status'],bool(x['shaderRecovery'])) for x in matrecords]);print(errors)
