"""Read-only Pak extraction and typed-import UE static closure; not REA evidence."""
from pathlib import Path
import concurrent.futures, hashlib, json, subprocess, time, traceback

ROOT = Path('E:/undefeated-web/research/rea-audit')
OLD = Path('C:/Users/Shark/OneDrive/文档/ChatGPT/homerlander/analysis')
PAK = Path('E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak')
TOOL = OLD / 'tools/uasset-legacy/net472/UAssetGUI.exe'
REPAK = OLD / 'tools/repak/repak.exe'
EXTRACTED = ROOT / 'extracted'
DECODED = ROOT / 'decoded'
for directory in (ROOT, EXTRACTED, DECODED): directory.mkdir(parents=True, exist_ok=True)

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, data): (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def pakfile(package, suffix='.uasset'): return 'UNDEFEATED/Content/' + package.removeprefix('/Game/') + suffix
def call(args, timeout=120):
    return subprocess.run([str(x) for x in args], capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)

listing = set((ROOT.parent/'evidence/pak-files.txt').read_text(encoding='utf-8-sig').splitlines())
audit = read(ROOT/'logic-coverage.json')
old_sources = {}
raw_sources = {}
for base in [OLD/'extracted', OLD/'extracted-systems', ROOT.parent/'exports/unpacked', EXTRACTED]:
    if not base.exists(): continue
    for asset in base.rglob('*.uasset'):
        parts = asset.as_posix().split('/UNDEFEATED/Content/', 1)
        if len(parts)==2: raw_sources.setdefault('/Game/'+parts[1][:-7], asset)
for item in audit['decoded_packages']:
    path = Path(item['path']); data = read(path)
    candidates = [n for n in data.get('NameMap',[]) if isinstance(n,str) and n.startswith('/Game/') and n.rsplit('/',1)[-1]==item['name']]
    candidates = list(dict.fromkeys(candidates))
    if len(candidates)==1 and pakfile(candidates[0]) in listing:
        old_sources[candidates[0]] = path

TARGET_TYPES = {'DataTable','CurveTable','UserDefinedStruct','UserDefinedEnum','BehaviorTree','BlackboardData','CurveFloat','CurveVector','CurveLinearColor'}
def eligible(t): return t.endswith('BlueprintGeneratedClass') or t in TARGET_TYPES
def resolve_ref(data, index):
    if index < 0: return data['Imports'][-index-1]['ObjectName']
    if index > 0: return data['Exports'][index-1]['ObjectName']
    return None
def outer_package(data, item):
    seen=set(); current=item
    while True:
        if current.get('ClassName')=='Package': return current.get('ObjectName')
        idx=current.get('OuterIndex',0)
        if idx>=0 or idx in seen: return None
        seen.add(idx); current=data['Imports'][-idx-1]

nodes={}; edges=[]; exclusions={}; processed=set(); pending=set(old_sources)
pending.update(x['package'] for x in audit['confirmed_blueprint_dependencies'])
started=time.time(); wave=0
write('closure-seeds.json', {'classification':'typed import identities, not filename guessing','original_decoded_sources':{k:str(v) for k,v in old_sources.items()},'seed_packages':sorted(pending),'source_pak':str(PAK),'pak_sha256_from_existing_identity':read(ROOT.parent/'evidence/pak-identity.json')['sha256'],'decoder':str(TOOL),'decoder_sha256':digest(TOOL),'scope':'Project /Game typed hard-import closure only; no unrelated Engine resources, no Web modifications'})

def save(finished=False):
    progress={'wave':wave,'elapsed_seconds':round(time.time()-started,1),'processed':len(processed),'pending':len(pending),'decoded_ok':sum(x.get('status')=='decoded' for x in nodes.values()),'reused':sum(x.get('reused',False) for x in nodes.values()),'failed':sum(x.get('status')!='decoded' for x in nodes.values()),'edges':len(edges),'finished':finished}
    write('closure-progress.json',progress)
    write('dependency-closure.json',{'evidence_kind':'UAssetAPI cooked UE static dependency closure; NOT REA Evidence; NOT runtime validation','scope':'Reachable /Game BlueprintGeneratedClass subclasses, DataTable/CurveTable, user structs/enums, BehaviorTree/BlackboardData and gameplay curves via typed imports. Soft refs are recorded but not recursively loaded unless already reached by typed import.','progress':progress,'nodes':list(nodes.values()),'edges':edges,'excluded_import_types':exclusions,'pending_packages':sorted(pending),'limitations':['A decoded AST is not a complete behavioral explanation or Web implementation.','Native /Script and unrelated Engine imports are not recursively parsed.','Soft-only, string-built loads, LevelScript and unreferenced assets remain outside this hard-import closure.','False default fields still require inheritance/native-default interpretation.']})
    print(json.dumps(progress),flush=True)

def decode_one(package):
    node={'package':package,'pak_path':pakfile(package),'status':'failed','reused':package in old_sources}
    try:
        asset=raw_sources.get(package,EXTRACTED/pakfile(package))
        if not asset.exists():
            node['failure_reason']='package missing from extracted snapshot';return node,None
        node['source_asset']=str(asset);node['source_sha256']=digest(asset)
        for ext in ['.uexp','.ubulk']:
            companion=asset.with_suffix(ext)
            if companion.exists():node[ext[1:]+'_sha256']=digest(companion)
        target=old_sources.get(package,DECODED/(package.removeprefix('/Game/')+'.json'))
        if not node['reused']:
            target.parent.mkdir(parents=True,exist_ok=True)
            run=call([TOOL,'tojson',asset,target,'VER_UE4_27'],90)
            node['decoder_exit_code']=run.returncode
            if run.returncode or not target.exists():
                node['failure_reason']=(run.stdout+run.stderr).decode(errors='replace')[-5000:] or 'No decoder JSON';return node,None
        data=read(target);node['decoded_path']=str(target);node['decoded_sha256']=digest(target)
        node['class_identities']=[{'export_index':i,'object_name':e['ObjectName'],'serialized_export_type':e.get('$type'),'class_ref':resolve_ref(data,e.get('ClassIndex',0)),'super_ref':resolve_ref(data,e.get('SuperStruct',0))} for i,e in enumerate(data.get('Exports',[])) if 'ClassExport' in e.get('$type','')]
        node['asset_identities']=[{'export_index':i,'object_name':e['ObjectName'],'class_ref':resolve_ref(data,e.get('ClassIndex',0)),'serialized_export_type':e.get('$type')} for i,e in enumerate(data.get('Exports',[])) if e.get('bIsAsset')]
        node['functions']=[{'export_index':i,'name':e['ObjectName'],'ast_top_level_nodes':len(e.get('ScriptBytecode') or [])} for i,e in enumerate(data.get('Exports',[])) if 'FunctionExport' in e.get('$type','')]
        node['raw_exports']=[e.get('ObjectName') for e in data.get('Exports',[]) if 'RawExport' in e.get('$type','')]
        node['soft_package_references']=data.get('SoftPackageReferenceList')
        node['status']='decoded';return node,data
    except Exception as exc:node['failure_reason']=type(exc).__name__+': '+str(exc);return node,None

while pending:
    wave+=1;batch=sorted(pending-processed);pending.clear()
    if not batch:break
    missing=[p for p in batch if p not in raw_sources and pakfile(p) in listing]
    if missing:
        args=[REPAK,'unpack',PAK,'-o',EXTRACTED,'-q']
        for p in missing:
            for ext in ['.uasset','.uexp']:
                if pakfile(p,ext) in listing:args.extend(['-i',pakfile(p,ext)])
        run=call(args,180)
        if run.returncode:write('extraction-error-wave-'+str(wave)+'.json',{'exit_code':run.returncode,'error':(run.stdout+run.stderr).decode(errors='replace')[-5000:]})
        for p in missing:
            candidate=EXTRACTED/pakfile(p)
            if candidate.exists():raw_sources[p]=candidate
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for node,data in pool.map(decode_one,batch):
            package=node['package'];processed.add(package);nodes[package]=node
            if data is None:continue
            for i,item in enumerate(data.get('Imports',[])):
                kind=item.get('ClassName','');destination=outer_package(data,item)
                if not destination or not destination.startswith('/Game/'):continue
                if not eligible(kind):exclusions[kind]=exclusions.get(kind,0)+1;continue
                edge={'from':package,'to':destination,'import_type':kind,'import_name':item['ObjectName'],'json_pointer':f'/Imports/{i}','present_in_pak':pakfile(destination) in listing}
                edges.append(edge)
                if destination not in processed:pending.add(destination)
    save()
save(True)
