"""Independent inventory, source-buffer, transform and spline batching checks."""
import collections, hashlib, importlib.util, json, math, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
manifest=g.READ(g.OUT/'geometry-manifest.json');base=g.READ(g.EVID/'geometry-base-assets.json');rows,_=g.inventory(True)
socketfile=g.EVID/'geometry-socket-resolution.json';socketrecords={x['id']:x for x in g.READ(socketfile)['resolved']} if socketfile.exists() else {}
expected={r['record']['name']+':'+str(m['componentExportIndex']) for r in rows for m in r['detail']['meshReferences']}
transforms={r['record']['name']+':'+str(t['exportIndex']):t['composedComponentTransformUE'] for r in rows for t in r['detail']['componentTransforms'] if t.get('composedComponentTransformUE')}
covered=set();maxtransformerror=0.;instances=0;maxbatcherror=0.;batchsamples=0;uvsamples=0;validated=0;sourceBufferChecks=0
for asset in base:
    raw=pathlib.Path(asset['raw']);published=g.OUT/asset['url'].removeprefix('/assets/world/');d=g.READ(raw)
    for b in d['buffers']:
        assert g.HASH(raw.parent/b['uri'])==g.HASH(published.parent/b['uri']),'Published base geometry differs from original UEViewer buffer'
        sourceBufferChecks+=1
for asset in manifest['assets']:
    path=g.OUT/asset['url'].removeprefix('/assets/world/');stats,bounds=g.validate_gltf(path)
    assert stats==asset['geometryStats'];assert bounds==asset['bounds'];validated+=1
for level in manifest['levels']:
    for obj in level['objects']:
        for field in ('position','rotation','scale'):assert all(math.isfinite(x) for x in obj[field])
        if obj['geometryMode']=='spline-batch':sources=obj['sourceComponents']
        else:sources=[{**obj['source'],'id':obj['id'],'position':obj['position'],'rotation':obj['rotation'],'scale':obj['scale']}]
        for source in sources:
            key=level['id']+':'+str(source['exportIndex']);covered.add(key)
            if obj['geometryMode']=='instanced':instances+=1;continue
            expectedTransform=socketrecords[key]['transform'] if obj['geometryMode']=='socket-reference-pose' else g.transform(transforms[key])
            if obj['geometryMode']=='socket-reference-pose':assert obj['socketAttachment']['animationFollowingImplemented'] is False
            for field in ('position','rotation','scale'):
                error=max(abs(x-y) for x,y in zip(source[field],expectedTransform[field]));maxtransformerror=max(maxtransformerror,error)
        if obj['geometryMode']!='spline-batch':continue
        batchpath=g.OUT/'meshes'/obj['assetId']/'mesh.gltf';bd=g.READ(batchpath);bbs=[(batchpath.parent/b['uri']).read_bytes() for b in bd['buffers']]
        primitiveLookup={(p['material'],tuple(sorted(p['attributes']))):p for p in bd['meshes'][0]['primitives']}
        for source in obj['sourceComponents']:
            spath=g.OUT/'meshes'/source['bakedAssetId']/'mesh.gltf';sd=g.READ(spath);sbs=[(spath.parent/b['uri']).read_bytes() for b in sd['buffers']];sps=[p for mesh in sd['meshes'] for p in mesh['primitives']]
            assert len(sps)==len(source['sections'])
            for sp,section in zip(sps,source['sections']):
                k=section['destinationGroupKey'];bp=primitiveLookup[(k[0],tuple(k[1]))];pv=g.m.accessor(sd,sbs,sp['attributes']['POSITION']);bv=g.m.accessor(bd,bbs,bp['attributes']['POSITION'])
                for index in sorted({0,len(pv)//2,len(pv)-1}):
                    if index<0:continue
                    expectedPoint=g.m.add(source['position'],g.m.qrotate(source['rotation'],[pv[index][i]*source['scale'][i] for i in range(3)]));actual=bv[section['firstVertex']+index];err=max(abs(x-y) for x,y in zip(expectedPoint,actual));maxbatcherror=max(maxbatcherror,err);batchsamples+=1
                    assert err<.001,'Batched vertex deviates by >= 1 mm'
                for name in sp['attributes']:
                    if not name.startswith('TEXCOORD'):continue
                    sourceUV=g.m.accessor(sd,sbs,sp['attributes'][name]);batchUV=g.m.accessor(bd,bbs,bp['attributes'][name])
                    for index in sorted({0,len(sourceUV)//2,len(sourceUV)-1}):
                        if index<0:continue
                        assert sourceUV[index]==batchUV[section['firstVertex']+index],'UV changed during batching';uvsamples+=1
gaps={x['id'] for x in manifest['gaps']}
assert not covered-expected
assert expected-covered==gaps
assert len(expected)==11359 and len(covered)==len(expected)-len(gaps)
assert instances==253
assert maxtransformerror<1e-10
referenced_files={g.OUT/asset['url'].removeprefix('/assets/world/') for asset in manifest['assets']}
for path in list(referenced_files):
    for b in g.READ(path)['buffers']:referenced_files.add(path.parent/b['uri'])
verified_null=sum(x.get('sourceMaterial') is None and bool(x['sourceSlotCandidates']) and all(a['sourceMaterialSlots'][i]['material'] is None for i in x['sourceSlotCandidates']) for a in base for x in a['gltfMaterials'])
report={'status':'passed','sourceComponentsExpected':len(expected),'sourceComponentsRepresented':len(covered),'socketTransformGaps':len(gaps),'validatedPublishedGltfs':validated,'baseSourceBuffersByteIdentical':sourceBufferChecks,'sourceTransformMaximumError':maxtransformerror,'instancesRecovered':instances,'batchPositionSamples':batchsamples,'batchPositionMaximumErrorMeters':maxbatcherror,'batchUVSamplesUnchanged':uvsamples,'referencedGeometryFileBytes':sum(p.stat().st_size for p in referenced_files),'nativeStaticSectionsMapped':sum(x['mappingEvidence'].startswith('native-') for a in base for x in a['gltfMaterials']),'verifiedOriginalNullMaterialSections':verified_null,'unresolvedSectionMaterialAddresses':sum(not x.get('sourceMaterial') for a in base for x in a['gltfMaterials'])-verified_null,'ambiguousOriginalSkeletalSlots':sum(len(x['sourceSlotCandidates'])>1 for a in base for x in a['gltfMaterials']),'manifestSha256':g.HASH(g.OUT/'geometry-manifest.json')}
report['referencePoseSocketAttachments']=len(socketrecords);report['runtimeAnimatedSocketFollowingImplemented']=False
report['nativeSkeletalSectionsMapped']=sum(x['mappingEvidence'].startswith('native-') for a in base if a.get('materialSlotEvidence',{}).get('nativeSkeletalSectionEvidence') for x in a['gltfMaterials'])
report['nativeStaticSectionsMapped']-=report['nativeSkeletalSectionsMapped']
report['componentSectionOverrideAmbiguities']=len(g.READ(g.EVID/'geometry-skeletal-slot-ambiguities.json'))
if socketrecords:report['socketReferencePoseChecks']={'parentInverseBindMaximumError':max(x['socketEvidence']['parentSkinInverseBindMaximumError'] for x in socketrecords.values()),'parentRelativeBaselineMaximumError':max(x['baselineCompositionMaximumError'] for x in socketrecords.values()),'worldTRSReconstructionMaximumError':max(x['trsReconstructionMaximumError'] for x in socketrecords.values())}
g.WRITE(g.EVID/'geometry-validation.json',report)
print(json.dumps(report))
