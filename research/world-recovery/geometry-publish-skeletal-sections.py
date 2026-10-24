"""Replace ambiguous skeletal material slot mappings using native LOD0 section proof."""
import importlib.util,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
base=g.READ(g.EVID/'geometry-base-assets.json');results={x['package']:x for x in g.READ(g.EVID/'geometry-export-results.json')};changed=[]
reportfile=g.EVID/'geometry-skeletal-section-recovery.json';previous={x['sourcePackage']:x for x in g.READ(reportfile)['assets']} if reportfile.exists() else {}
for i,asset in enumerate(base):
    if asset['sourcePackage'] not in previous and not any(len(x['sourceSlotCandidates'])>1 for x in asset['gltfMaterials']):continue
    published=g.publish(results[asset['sourcePackage']]);ev=published['materialSlotEvidence'];sections=ev.get('nativeLod0Sections',[])
    assert 'nativeSkeletalSectionEvidence' in ev and all(len(x['sourceSlotCandidates'])==1 and x['mappingEvidence'].startswith('native-') for x in published['gltfMaterials']),(asset['sourcePackage'],ev)
    gltf=g.READ(pathlib.Path(published['raw']));primitives=[p for m in gltf['meshes'] for p in m['primitives']]
    assert len(sections)==len(primitives)
    for sec,pr in zip(sections,primitives):
        assert sec['numTriangles']*3==gltf['accessors'][pr['indices']]['count']
        assert sec['numVertices']==gltf['accessors'][pr['attributes']['POSITION']]['count']
        mat=published['sourceMaterialSlots'][sec['materialSlotIndex']]['material']
        assert mat and mat['object'].casefold()==gltf['materials'][pr['material']]['name'].casefold()
    changed.append({'sourcePackage':asset['sourcePackage'],'previousAmbiguousSections':previous.get(asset['sourcePackage'],{}).get('previousAmbiguousSections',sum(len(x['sourceSlotCandidates'])>1 for x in asset['gltfMaterials'])),'sectionMaterialIndices':[x['materialSlotIndex'] for x in sections],'sectionTrianglesAndVertexCountsMatched':len(sections),'sourceEvidence':ev})
    base[i]=published
g.WRITE(g.EVID/'geometry-base-assets.json',base);g.WRITE(g.EVID/'geometry-skeletal-section-recovery.json',{'status':'passed','assets':changed,'ambiguousSectionsResolved':sum(x['previousAmbiguousSections'] for x in changed),'geometryBuffersChanged':False});print([(x['sourcePackage'],x['sectionMaterialIndices']) for x in changed])
