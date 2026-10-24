"""Resumeable typed resource import closure from the 35 audited world maps.

Reads the original Pak, writes only rea-audit. Does not export geometry/pixels,
recover shaders, or create REA retained Evidence.
"""
from pathlib import Path
import argparse, collections, concurrent.futures, hashlib, json, subprocess, time

ROOT=Path('E:/undefeated-web'); OUT=ROOT/'research/rea-audit'
PAK=Path('E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak')
REPAK=ROOT/'tools/asset-pipeline/bin/repak.exe'
DECODER=ROOT/'tools/asset-pipeline/uasset-net472/UAssetGUI.exe'
EXTRACTED=OUT/'extracted-world-assets'; DECODED=OUT/'decoded-world-assets'
RESULT=OUT/'world-asset-dependency-closure.json'
PROGRESS=OUT/'world-asset-dependency-progress.json'
MESH={'StaticMesh','SkeletalMesh','DestructibleMesh'}
MATERIAL={'Material','MaterialInstance','MaterialInstanceConstant','MaterialInstanceDynamic','LandscapeMaterialInstanceConstant'}
FUNCTION={'MaterialFunction','MaterialFunctionInstance','MaterialFunctionMaterialLayer','MaterialFunctionMaterialLayerBlend','MaterialParameterCollection'}
MATERIAL_CONFIG={'SubsurfaceProfile','RuntimeVirtualTexture'}
def eligible(t):return t in MESH|MATERIAL|FUNCTION|MATERIAL_CONFIG or t.startswith('Texture')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def write(p,d):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    for attempt in range(12):
        try:tmp.replace(p);return
        except PermissionError:
            if attempt==11:raise
            time.sleep(0.1)
def run(args,timeout=120):return subprocess.run([str(x) for x in args],capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
def rel(pkg):
    if pkg.startswith('/Game/'):return 'UNDEFEATED/Content/'+pkg[6:]
    if pkg.startswith('/Engine/'):return 'Engine/Content/'+pkg[8:]
    return None
listing=set((ROOT/'research/evidence/pak-files.txt').read_text(encoding='utf-8-sig').splitlines())
inventory={p.casefold():p for p in listing}
def pakfile(pkg,ext='.uasset'):
    q=rel(pkg);return inventory.get((q+ext).casefold()) if q else None
def canonical(pkg):
    p=pakfile(pkg)
    if p:
        if p.startswith('UNDEFEATED/Content/'):return '/Game/'+p[len('UNDEFEATED/Content/'):-7]
        if p.startswith('Engine/Content/'):return '/Engine/'+p[len('Engine/Content/'):-7]
    return pkg
def outer_package(doc,index):
    seen=set()
    while index:
        if index in seen:return None
        seen.add(index);x=doc['Imports'][-index-1] if index<0 else doc['Exports'][index-1]
        if x.get('ClassName')=='Package' or x.get('ObjectName','').startswith(('/Game/','/Engine/','/Script/')):return canonical(x['ObjectName'])
        index=x.get('OuterIndex',0)
    return None
def class_name(doc,e):
    index=e.get('ClassIndex',0)
    return (doc['Imports'][-index-1] if index<0 else doc['Exports'][index-1]).get('ObjectName') if index else None
def export_identity(doc,i,e):
    extra=e.get('Extras'); extra=extra.get('$value','') if isinstance(extra,dict) else extra
    return {'index':i,'objectName':e.get('ObjectName'),'className':class_name(doc,e),'serializedExportType':e.get('$type'),
        'propertyCount':len(e.get('Data') or []),'opaqueExtrasEncodedCharacters':len(extra) if isinstance(extra,str) else None,
        'isRawExport':'RawExport' in e.get('$type',''),'pointer':f'/Exports/{i}'}
def imports(doc,pkg,decoded):
    rows=[]
    for i,x in enumerate(doc.get('Imports',[])):
        target=outer_package(doc,-i-1);kind=x.get('ClassName','')
        if not target or kind=='Package':continue
        follow=target!=pkg and eligible(kind) and target.startswith(('/Game/','/Engine/'))
        rows.append({'from':pkg,'to':target,'className':kind,'objectName':x.get('ObjectName'),'pointer':f'/Imports/{i}',
            'decodedFile':str(decoded),'followed':follow,'presentInPak':pakfile(target) is not None,
            'scopeReason':'typed resource dependency' if follow else 'self/native/non-resource import; recorded only'})
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--max-new-packages',type=int,default=0);parser.add_argument('--retry-failed',action='store_true');args=parser.parse_args()
    started=time.time();world=read(OUT/'world-coverage.json');worldhash=sha(OUT/'world-coverage.json')
    seedsfile=OUT/'world-asset-dependency-seeds.json'
    if seedsfile.exists() and read(seedsfile).get('worldCoverageSha256')==worldhash:seeddata=read(seedsfile)
    else:
        rootedges=[];embedded=[]
        for level in world['levels']:
            decoded=Path(level['decoded']);doc=read(decoded)
            rootedges.extend(e for e in imports(doc,level['package'],decoded) if e['followed'])
            embedded.append({'package':level['package'],'decodedFile':str(decoded),'decodedSha256':level['decodedSha256'],
                'sourceFiles':level['sourceFiles'],'resourceExports':[export_identity(doc,i,e) for i,e in enumerate(doc['Exports']) if eligible(class_name(doc,e) or '')]})
            print('Read world seed imports',level['name'],flush=True)
        target_packages=sorted({e['to'] for e in rootedges})
        listed=world['uniqueAssetsAcrossReferencedWorld'];normalized=[]
        for kind,key in [('mesh','meshes'),('material','materials')]:
            for i,name in enumerate(listed[key]):
                candidate=name.rsplit('/',1)[0]
                candidate=canonical(candidate)
                normalized.append({'kind':kind,'reference':name,'package':candidate,'presentInTypedSeeds':candidate in target_packages,
                    'worldCoveragePointer':f'/uniqueAssetsAcrossReferencedWorld/{key}/{i}'})
        seeddata={'worldCoverageSha256':worldhash,'worldCoverageSource':str(OUT/'world-coverage.json'),'rootEdges':rootedges,
            'seedPackages':target_packages,'mapOwnedResourceExports':embedded,'meshMaterialSeedCrosscheck':normalized}
        write(seedsfile,seeddata)
    cache={}
    prior=read(OUT/'material-coverage.json')
    for item in prior['sourceMaterialDependencyClosure']+prior.get('sampledTextureMetadata',[]):
        if item.get('status')=='static-decoded':cache[canonical(item['package'])]=item
    sources={}
    for base in [ROOT/'research/exports/unpacked',OUT/'unpacked',OUT/'extracted',OUT/'extracted-blueprints',EXTRACTED]:
        if not base.exists():continue
        scan=run(['rg','--files','--no-ignore','-g','*.uasset',base])
        for name in scan.stdout.decode('utf-8',errors='replace').splitlines():
            p=Path(name);s=p.as_posix()
            if '/UNDEFEATED/Content/' in s:pkg='/Game/'+s.split('/UNDEFEATED/Content/',1)[1][:-7]
            elif '/Engine/Content/' in s:pkg='/Engine/'+s.split('/Engine/Content/',1)[1][:-7]
            else:continue
            if pakfile(pkg,'.uexp') and not p.with_suffix('.uexp').exists():continue
            sources.setdefault(canonical(pkg),p)
    nodes={};edges=[];pending=set(seeddata['seedPackages'])
    if RESULT.exists():
        previous=read(RESULT)
        if previous['provenance']['worldCoverageSha256']!=worldhash:raise RuntimeError('World coverage changed; archive old closure before resuming.')
        nodes={n['package']:n for n in previous['nodes']};edges=previous['edges'];pending.update(previous['pendingPackages'])
        if args.retry_failed:
            bad={p for p,n in nodes.items() if n['status']!='imports-and-properties-decoded'}
            nodes={p:n for p,n in nodes.items() if p not in bad};edges=[e for e in edges if e['from'] not in bad];pending.update(bad)
    for edge in edges:
        follow=edge['to']!=edge['from'] and eligible(edge['className']) and edge['to'].startswith(('/Game/','/Engine/'))
        edge['followed']=follow
        edge['scopeReason']='typed resource dependency' if follow else 'self/native/non-resource import; recorded only'
        if follow:pending.add(edge['to'])
    pending.difference_update(nodes)
    types=collections.defaultdict(set)
    for e in seeddata['rootEdges']+edges:
        if e['followed']:types[e['to']].add(e['className'])
    processed_new=0

    def save():
        raw=sum(len(n.get('rawExports',[])) for n in nodes.values())
        stats={'seedPackages':len(seeddata['seedPackages']),'processedPackages':len(nodes),'pendingPackages':len(pending),
          'decodedPackages':sum(n['status']=='imports-and-properties-decoded' for n in nodes.values()),
          'failedPackages':sum(n['status']!='imports-and-properties-decoded' for n in nodes.values()),
          'rawExports':raw,'packagesWithRawExports':sum(bool(n.get('rawExports')) for n in nodes.values()),
          'reusedMaterialAuditPackages':sum(n.get('reusedMaterialAudit',False) for n in nodes.values()),
          'importsEdges':len(edges),'followedEdges':sum(e['followed'] for e in edges),'newThisRun':processed_new,
          'elapsedSecondsThisRun':round(time.time()-started,2),'queueExhausted':not pending}
        for p,n in nodes.items():n['incomingTypes']=sorted(types[p])
        result={'schemaVersion':1,'evidenceKind':'Independent UAssetAPI cooked static typed-import resource closure. NOT REA retained Evidence.',
          'scope':'35 maps in world-coverage.json -> exact typed mesh/material/texture/function/MPC imports -> recursively reachable resources of these types plus SubsurfaceProfile/RuntimeVirtualTexture material configuration; no unrelated Pak seeds.',
          'coverageMeaning':'Imports/properties only. Decoding metadata, even with zero RawExport objects, does not recover mesh geometry, texture pixels, full material shader math or runtime usage.',
          'provenance':{'worldCoverageSha256':worldhash,'seedsFile':str(seedsfile),'sourcePak':str(PAK),'pakIdentity':read(ROOT/'research/evidence/pak-identity.json'),
              'decoder':str(DECODER),'decoderSha256':sha(DECODER),'scriptSha256':sha(Path(__file__))},
          'statistics':stats,'nodes':[nodes[p] for p in sorted(nodes)],'rootEdges':seeddata['rootEdges'],'edges':edges,'pendingPackages':sorted(pending),
          'limitations':['Hard typed imports are potential dependencies, not proof an object is visible or active.',
            'Blueprint/script-created, soft-only or string-built resources are outside this resource-only traversal.',
            'Map-owned landscape textures/materials are recorded in seedsFile as embedded exports; their geometry/pixel payloads are not exported.',
            'All non-resource import edges are recorded but not recursively decoded, including Skeleton/PhysicsAsset/Blueprint dependencies.',
            'Bulk pixel/geometry data is not exported. Existing local ubulk is hashed where available; absent ubulk is explicitly recorded.',
            'RawExport and opaque Extras are distinguished; a NormalExport with opaque Extras is not a recovered mesh/shader.']}
        write(RESULT,result);write(PROGRESS,stats);print(json.dumps(stats),flush=True)

    def decode_one(pkg):
        node={'package':pkg,'pakPath':pakfile(pkg),'status':'failed','reusedMaterialAudit':pkg in cache};outedges=[]
        try:
            source=sources.get(pkg)
            if source is None:node['failure']='No .uasset/.uexp source available in original Pak/local extraction';return node,outedges
            node['sourceFiles']=[]
            for ext in ['.uasset','.uexp','.ubulk']:
                p=source.with_suffix(ext);record={'extension':ext,'presentInPak':pakfile(pkg,ext) is not None,'localPath':str(p),'existsLocally':p.exists()}
                if p.exists():record.update(bytes=p.stat().st_size,sha256=sha(p))
                else:record['notReadReason']='Bulk payload intentionally not extracted' if ext=='.ubulk' else 'Not present locally'
                node['sourceFiles'].append(record)
            old=cache.get(pkg);target=ROOT/old['decodedFile'] if old else DECODED/(rel(pkg)+'.json')
            if old and sha(target)!=old['decodedSha256']:raise RuntimeError('Cached JSON identity mismatch')
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                decoded=run([DECODER,'tojson',source,target,'VER_UE4_27'],timeout=120)
                node['decoderExitCode']=decoded.returncode
                if decoded.returncode or not target.exists():
                    node['failure']=(decoded.stdout+decoded.stderr).decode(errors='replace')[-3000:] or 'No JSON output';return node,outedges
            doc=read(target);node.update(decodedFile=str(target),decodedSha256=sha(target),decodedBytes=target.stat().st_size)
            node['exports']=[export_identity(doc,i,e) for i,e in enumerate(doc.get('Exports',[]))]
            node['rawExports']=[e for e in node['exports'] if e['isRawExport']]
            node['classCounts']=dict(collections.Counter(e['className'] for e in node['exports']))
            node['softPackageReferences']=doc.get('SoftPackageReferenceList')
            node['recoveryLevel']='serialized imports and decoded properties only; opaque Extras and bulk payload not interpreted'
            node['status']='imports-and-properties-decoded';outedges=imports(doc,pkg,target)
        except Exception as exc:node['failure']=type(exc).__name__+': '+str(exc)
        return node,outedges

    while pending and (not args.max_new_packages or processed_new<args.max_new_packages):
        take=min(32,args.max_new_packages-processed_new) if args.max_new_packages else 32
        batch=sorted(pending)[:take]
        missing=[p for p in batch if p not in sources and pakfile(p)]
        if missing:
            cmd=[REPAK,'unpack',PAK,'-o',EXTRACTED,'-q']
            for p in missing:
                for ext in ['.uasset','.uexp']:
                    if file:=pakfile(p,ext):cmd+=['-i',file]
            extracted=run(cmd,180)
            if extracted.returncode:
                write(OUT/'world-asset-extraction-error.json',{'packages':missing,'exitCode':extracted.returncode,'error':(extracted.stdout+extracted.stderr).decode(errors='replace')[-4000:]})
            for p in missing:
                source=EXTRACTED/pakfile(p)
                if source.exists():sources[p]=source
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for node,newedges in pool.map(decode_one,batch):
                pkg=node['package'];nodes[pkg]=node;pending.discard(pkg);processed_new+=1;edges.extend(newedges)
                for edge in newedges:
                    if edge['followed']:
                        types[edge['to']].add(edge['className'])
                        if edge['to'] not in nodes:pending.add(edge['to'])
        save()
    save()

if __name__=='__main__':main()
