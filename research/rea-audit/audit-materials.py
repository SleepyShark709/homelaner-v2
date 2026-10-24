"""Read-only source/public audit. Writes audit outputs only; not REA Evidence."""
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CONTENT = ROOT / 'research/exports/unpacked/UNDEFEATED/Content'
PAK = Path('E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak')
TOOLS = ROOT / 'tools/asset-pipeline'
INVENTORY = set((ROOT/'research/evidence/pak-files.txt').read_text().splitlines())


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, x): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf-8')


def ref(doc, i):
    if not i: return None
    obj = doc['Exports'][i-1] if i > 0 else doc['Imports'][-i-1]
    parent = ref(doc, obj.get('OuterIndex', 0))
    return (parent+'.' if parent else '')+obj['ObjectName']


def package(doc, i):
    while i:
        item = doc['Exports'][i-1] if i > 0 else doc['Imports'][-i-1]
        if item['ObjectName'].startswith('/Game/') or item['ObjectName'].startswith('/Engine/'):
            return item['ObjectName']
        i = item.get('OuterIndex', 0)
    return None


def simplify(prop, doc):
    value = prop.get('Value', prop.get('EnumValue'))
    typ = prop.get('$type', '')
    if 'ObjectPropertyData' in typ: return ref(doc, value)
    if isinstance(value, list):
        if any(not isinstance(v,dict) for v in value): return value
        if 'ArrayPropertyData' in typ: return [simplify(v, doc) for v in value]
        names=[v.get('Name', str(i)) for i,v in enumerate(value)]
        if len(names)!=len(set(names)):
            return [{'name':n,'value':simplify(v,doc)} for n,v in zip(names,value)]
        return {v.get('Name', str(i)): simplify(v, doc) for i, v in enumerate(value)}
    if isinstance(value, dict): return {k: v for k,v in value.items() if k != '$type'}
    return value


def public_inventory():
    results=[]; names=set()
    for path in sorted((ROOT/'public/assets').rglob('*.gltf')):
        doc=read(path); mats=[]
        for i,m in enumerate(doc.get('materials', [])):
            names.add(m.get('name','')); pbr=m.get('pbrMetallicRoughness',{})
            channels={}
            for key,value in [('baseColorTexture',pbr.get('baseColorTexture')),('metallicRoughnessTexture',pbr.get('metallicRoughnessTexture')),
                              ('normalTexture',m.get('normalTexture')),('occlusionTexture',m.get('occlusionTexture')),('emissiveTexture',m.get('emissiveTexture'))]:
                if value:
                    tex=doc['textures'][value['index']]; channels[key]=doc['images'][tex['source']].get('uri')
                else: channels[key]=None
            mats.append(dict(index=i,name=m.get('name'),pointer=f'/materials/{i}',channels=channels,serialized=m))
        results.append(dict(file=str(path.relative_to(ROOT)),sha256=sha(path),materials=mats,
                            meshCount=len(doc.get('meshes',[])),extensions=doc.get('extensionsUsed',[])))
    return results,names


def maps_audit():
    result=[]; overrides=[]; deps={}
    selected={r['sourceActor'] for r in read(ROOT/'research/evidence/city-layout-source.json')['selectedStatic']}
    for name in ['MainLevel','ResidentialArea1','ResidentialArea2','DownTown']:
        path=ROOT/'research/exports/city-decoded'/(name+'.json')
        if not path.exists():continue
        doc=read(path); classes=collections.Counter(); mats=[]
        for i,imp in enumerate(doc['Imports']):
            pkg=package(doc,-i-1)
            if pkg and imp['ClassName'] in ['Material','MaterialInstanceConstant','LandscapeMaterialInstanceConstant','MaterialFunction','MaterialParameterCollection','Texture2D','TextureCube','StaticMesh','SkeletalMesh']:
                deps.setdefault(pkg,dict(classes=set(),sources=[]))['classes'].add(imp['ClassName'])
                deps[pkg]['sources'].append(dict(map=name,pointer=f'/Imports/{i}',object=imp['ObjectName']))
                if 'Material' in imp['ClassName']:mats.append(pkg)
        for i,e in enumerate(doc['Exports']):
            c=e.get('ClassIndex',0); cls=doc['Imports'][-c-1]['ObjectName'] if c<0 else ref(doc,c)
            classes[cls]+=1
            for j,p in enumerate(e.get('Data',[])):
                if p.get('Name')!='OverrideMaterials':continue
                slots=[]
                for k,v in enumerate(p.get('Value',[])):
                    slots.append(dict(slot=k,material=ref(doc,v.get('Value',0)),package=package(doc,v.get('Value',0)),
                                      pointer=f'/Exports/{i}/Data/{j}/Value/{k}/Value'))
                actor=(ref(doc,e.get('OuterIndex',0)) or '').replace('.','/')
                overrides.append(dict(map=name,component=e['ObjectName'],sourceActor=actor,exportIndex=i+1,
                                      selectedForCurrentWeb=actor in selected,slots=slots))
        result.append(dict(level=name,file=str(path.relative_to(ROOT)),sha256=sha(path),exports=len(doc['Exports']),
            componentClassCounts=dict(classes),materialImportPackages=sorted(set(mats))))
        print('Audited map',name,flush=True)
    return result,overrides,{k:dict(classes=sorted(v['classes']),sources=v['sources']) for k,v in sorted(deps.items())}


def local_source(pkg):
    if pkg.startswith('/Game/'):
        relative='UNDEFEATED/Content/'+pkg[6:]
        existing=CONTENT/(pkg[6:]+'.uasset')
    elif pkg.startswith('/Engine/'):
        relative='Engine/Content/'+pkg[8:];existing=ROOT/'research/exports/unpacked'/(relative+'.uasset')
    else:return None,None
    target=OUT/'unpacked'/(relative+'.uasset')
    if existing.exists():return existing,relative
    if target.exists():return target,relative
    return None,relative


def ensure_packages(packages):
    missing=[]
    for pkg in packages:
        source,relative=local_source(pkg)
        if source is None and relative:
            for ext in ['.uasset','.uexp','.ubulk']:
                if relative+ext in INVENTORY:missing.append(relative+ext)
    if missing:
        cmd=[str(TOOLS/'bin/repak.exe'),'unpack',str(PAK),'-o',str(OUT/'unpacked')]
        for p in sorted(set(missing)):cmd+=['-i',p]
        subprocess.run(cmd,check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)


def decode_material(pkg):
    source,relative=local_source(pkg)
    if source is None:return dict(package=pkg,status='missing-cooked-source'),[]
    output=OUT/'decoded-materials'/(relative+'.json');output.parent.mkdir(parents=True,exist_ok=True)
    if not output.exists():
        result=subprocess.run([str(TOOLS/'uasset-net472/UAssetGUI.exe'),'tojson',str(source),str(output),'VER_UE4_27'],
                              capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
        if result.returncode or not output.exists():return dict(package=pkg,status='decoder-failed',exitCode=result.returncode),[]
    doc=read(output);imports=[];follow=[]
    for i,imp in enumerate(doc['Imports']):
        dependency=package(doc,-i-1)
        if dependency and dependency!=pkg:
            imports.append(dict(package=dependency,className=imp['ClassName'],objectName=imp['ObjectName'],pointer=f'/Imports/{i}'))
            if imp['ClassName'] in ['Material','MaterialInstanceConstant','MaterialFunction','MaterialParameterCollection']:
                follow.append(dependency)
    exports=[]
    for i,e in enumerate(doc['Exports']):
        data=e.get('Data',[])
        exports.append(dict(name=e['ObjectName'],className=ref(doc,e.get('ClassIndex',0)),exportType=e.get('$type'),
            pointer=f'/Exports/{i}',properties={p['Name']:dict(value=simplify(p,doc),pointer=f'/Exports/{i}/Data/{j}') for j,p in enumerate(data)},
            rawExtrasEncodedBytes=len(e.get('Extras',{}).get('$value','')) if isinstance(e.get('Extras'),dict) else None))
    identities={str(source):sha(source)}
    if source.with_suffix('.uexp').exists():identities[str(source.with_suffix('.uexp'))]=sha(source.with_suffix('.uexp'))
    return dict(package=pkg,status='static-decoded',sourceHashes=identities,decodedFile=str(output.relative_to(ROOT)),
                decodedSha256=sha(output),dependencies=imports,exports=exports),follow


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    public,names=public_inventory()
    maps,overrides,deps=maps_audit()
    source_packages={('/Game/'+p.removeprefix('UNDEFEATED/Content/').removesuffix('.uasset')) for p in INVENTORY
                     if p.startswith('UNDEFEATED/Content/') and p.endswith('.uasset') and Path(p).stem in names}
    selected_overrides=read(ROOT/'research/evidence/city-layout-material-overrides.json')['actors']
    for row in selected_overrides:
        source_packages.update(p.rsplit('/',1)[0] for p in row['overrides'] if p)
    source_packages.update('/Game/Action_Male/Materials/'+n for n in ['M_Body_master','MI_Body_asian','M_Clothes_master','M_Hair_master','M_GlassLens_master_Black'])
    records={};queue=source_packages
    while queue:
        ensure_packages(queue)
        batch=sorted(queue);queue=set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for record,follow in pool.map(decode_material,batch):
                records[record['package']]=record
                queue.update(p for p in follow if p not in records and p not in batch)
        print('Decoded material dependency records',len(records),'next',len(queue),flush=True)
    texture_dependencies=sorted({d['package'] for r in records.values() for d in r.get('dependencies',[]) if d['className'] in ['Texture2D','TextureCube']})
    map_paths=sorted(p for p in INVENTORY if p.startswith('UNDEFEATED/Content/') and p.endswith('.umap'))
    flat=[m for f in public for m in f['materials']]
    statistics=dict(publishedGltfFiles=len(public),publishedMaterialEntries=len(flat),
        channelEntryCounts={c:sum(bool(m['channels'][c]) for m in flat) for c in ['baseColorTexture','normalTexture','metallicRoughnessTexture','occlusionTexture','emissiveTexture']},
        currentWebObjects=len(read(ROOT/'public/assets/city/manifest.json')['objects']),
        selectedStaticObjects=len(read(ROOT/'research/evidence/city-layout-source.json')['selectedStatic']),
        selectedSplineComponents=len(read(ROOT/'research/evidence/city-layout-source.json')['nearbySplines']),
        selectedActorsWithOverrideMaterials=len(selected_overrides),selectedDistinctOverrideMaterials=len({p for r in selected_overrides for p in r['overrides'] if p}),
        decodedMaterialDependencyRecords=len(records),referencedTextureDependencies=len(texture_dependencies),pakGameMaps=len(map_paths))
    report=dict(schemaVersion=1,evidenceKind='Independent static UAssetAPI/UModel/filesystem audit; NOT REA retained Evidence; no original-game runtime observation',
        scope='All current public glTF files; four already-decoded maps; current published materials and selected map override materials with recursive material-parent/function dependencies. Not a complete recovery of every game material.',
        statistics=statistics,published=public,maps=maps,mapMaterialOverrides=overrides,mapReferencedResourceDependencies=deps,
        sourceMaterialDependencyClosure=list(records.values()),textureDependencies=texture_dependencies,pakGameMapPaths=map_paths,
        knownCurrentOverrideApplication='None: exporter records overrides but publish_mesh uses mesh defaults; World.ts has no per-object override application.',
        provenance=dict(pakIdentity=read(ROOT/'research/evidence/pak-identity.json'),tools={str(TOOLS/'uasset-net472/UAssetGUI.exe'):sha(TOOLS/'uasset-net472/UAssetGUI.exe')},
            scripts={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/asset-pipeline/export-city.py',ROOT/'tools/asset-pipeline/publish_original.py',ROOT/'src/game/World.ts',ROOT/'src/game/Game.ts']}))
    write(OUT/'material-coverage.json',report)
    print(json.dumps(statistics,indent=2))


if __name__=='__main__':main()
