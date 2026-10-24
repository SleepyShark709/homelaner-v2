"""Bounded registry-typed static decode supplement. Original closure/Pak unchanged."""
from pathlib import Path
import ast, concurrent.futures, hashlib, json, re, subprocess, time

ROOT=Path('E:/undefeated-web/research/rea-audit')
OLD=Path('C:/Users/Shark/OneDrive/文档/ChatGPT/homerlander/analysis')
PAK=Path('E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak')
TOOL=OLD/'tools/uasset-legacy/net472/UAssetGUI.exe'
REPAK=OLD/'tools/repak/repak.exe'
EXTRACTED=ROOT/'extracted'
DECODED=ROOT/'decoded'
# Reuse audited read-only decoder helpers without executing the old closure driver.
tree=ast.parse((ROOT/'expand-logic-closure.py').read_text(encoding='utf-8'))
helpers={'read','digest','write','pakfile','call','resolve_ref','outer_package','decode_one'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<audited helpers>','exec'))
base=read(ROOT/'dependency-closure.json')
baseline_hash=digest(ROOT/'dependency-closure.json')
registry=read(ROOT/'all-package-type-coverage.json')
assets=read(ROOT/'asset-registry-parsed.json')['assets']
rows={p['package']:p for p in registry['packages']}
class_types={'BlueprintGeneratedClass','AnimBlueprintGeneratedClass','WidgetBlueprintGeneratedClass'}
logic_types=class_types|{'DataTable','CurveTable','UserDefinedStruct','UserDefinedEnum','BehaviorTree','BlackboardData','CurveFloat','CurveVector','CurveLinearColor'}
targets={p:r for p,r in rows.items() if p.startswith('/Game/') and class_types.intersection(r['assetClasses'])}
maps={p for p,r in targets.items() if 'World' in r['assetClasses']}
old={n['package']:n for n in base['nodes']}
missing=set(targets)-set(old)-maps
listing=set((ROOT.parent/'evidence/pak-files.txt').read_text(encoding='utf-8-sig').splitlines())
old_sources={};raw_sources={}
new={};edges=[];pending=set(missing);started=time.time();wave=0
write('all-blueprint-seeds.json',{'source':'AssetRegistry.AssetClass exact set difference','target_types':sorted(class_types),'all_target_packages':sorted(targets),'original_closure_packages':sorted(old),'missing_nonmap_packages':sorted(missing),'map_class_packages_reuse_only':sorted(maps),'original_closure_sha256':baseline_hash,'registry_sha256':digest(ROOT/'all-package-type-coverage.json'),'decoder_sha256':digest(TOOL)})
while pending:
    wave+=1;batch=sorted(pending-set(old)-set(new)-maps);pending.clear()
    if not batch:break
    args=[REPAK,'unpack',PAK,'-o',EXTRACTED,'-q']
    for p in batch:
        for ext in ['.uasset','.uexp']:
            if pakfile(p,ext) in listing and not (EXTRACTED/pakfile(p,ext)).exists():args.extend(['-i',pakfile(p,ext)])
    if '-i' in args:
        result=call(args,180)
        if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode(errors='replace'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for node,data in pool.map(decode_one,batch):
            p=node['package'];node['role']='missing_registry_class' if p in missing else 'necessary_logic_hard_dependency';new[p]=node
            if data is None:continue
            for i,imp in enumerate(data['Imports']):
                dest=outer_package(data,imp)
                if not dest or not dest.startswith('/Game/') or dest==p:continue
                row=rows.get(dest)
                if not row or not logic_types.intersection(row['assetClasses']) or 'World' in row['assetClasses']:continue
                edges.append({'from':p,'to':dest,'import_type':imp.get('ClassName'),'import_name':imp.get('ObjectName'),'pointer':f'/Imports/{i}','registry_types':row['assetClasses']})
                if dest not in old and dest not in new:pending.add(dest)
    progress={'wave':wave,'new_parsed':len(new),'pending':len(pending),'failed':sum(n['status']!='decoded' for n in new.values()),'elapsed_seconds':round(time.time()-started,1)}
    write('all-blueprint-progress.json',progress);print(json.dumps(progress),flush=True)

def iter_json_array(path,key):
    """Stream individual UAssetAPI Exports/Imports without retaining whole map JSON."""
    decoder=json.JSONDecoder();buf='';found=False;eof=False
    with path.open(encoding='utf-8-sig') as f:
        while True:
            if not found:
                chunk=f.read(1048576)
                if not chunk:raise ValueError('Missing array '+key)
                buf+=chunk;m=re.search(r'"'+re.escape(key)+r'"\s*:\s*\[',buf)
                if not m:buf=buf[-100:];continue
                buf=buf[m.end():];found=True
            buf=buf.lstrip(' \r\n\t,')
            if buf.startswith(']'):return
            try:
                obj,end=decoder.raw_decode(buf)
                yield obj;buf=buf[end:]
            except json.JSONDecodeError:
                chunk=f.read(1048576)
                if not chunk:raise
                buf+=chunk

map_audit=read(ROOT/'all-map-inventory.json')
world=read(ROOT/'world-coverage.json')
map_sources={n['package']:n for n in world['levels']+map_audit['supplementalMaps']}
map_nodes={}
for p in sorted(maps):
    m=map_sources[p];path=Path(m['decoded']);imports=list(iter_json_array(path,'Imports'))
    classes=[];functions=[];raw=[]
    for i,e in enumerate(iter_json_array(path,'Exports')):
        typ=e.get('$type','');ci=e.get('ClassIndex',0)
        cr=imports[-ci-1]['ObjectName'] if ci<0 else None
        if 'ClassExport' in typ:
            classes.append({'export_index':i,'object_name':e['ObjectName'],'class_ref':cr,'pointer':f'/Exports/{i}','script_bytecode_nodes':len(e.get('ScriptBytecode') or [])})
        if 'FunctionExport' in typ:
            functions.append({'export_index':i,'name':e['ObjectName'],'outer_index':e.get('OuterIndex'),'ast_top_level_nodes':len(e.get('ScriptBytecode') or []),'pointer':f'/Exports/{i}/ScriptBytecode'})
        if 'RawExport' in typ:raw.append({'export_index':i,'object_name':e['ObjectName'],'class_ref':cr})
    map_nodes[p]={'package':p,'status':'decoded','group':'reused_map_embedded_class','decoded_path':str(path),'decoded_sha256':digest(path),'source_files':m.get('sourceFiles'),'class_identities':classes,'functions':functions,'raw_exports':raw}
    print(json.dumps({'map_class_checked':p,'classes':len(classes),'functions':len(functions),'raw':len(raw)}),flush=True)

allnodes={**old,**new,**map_nodes};report=[]
for p,row in sorted(targets.items()):
    n=allnodes.get(p);class_assets=[a for a in assets if a['packageName']==p and a['assetClass'] in class_types]
    expected={(a['assetName'],a['assetClass']) for a in class_assets}
    actual={(a['object_name'],a['class_ref']) for a in (n or {}).get('class_identities',[])}
    missing_identities=expected-actual
    matched=bool(n and n['status']=='decoded' and not missing_identities)
    report.append({'package':p,'registry_classes':sorted(set(row['assetClasses'])&class_types),'registry_evidence':row['registryEvidence'],'group':'map_embedded_class' if p in maps else 'original_306_closure' if p in old else 'registry_gap_supplement','decode_status':('decoded_class_verified' if matched else 'class_identity_mismatch' if n and n['status']=='decoded' else 'failed_or_missing'),'expected_class_identities':[list(x) for x in sorted(expected)],'unmatched_class_identities':[list(x) for x in sorted(missing_identities)],'class_identities':(n or {}).get('class_identities',[]),'decoded_path':(n or {}).get('decoded_path'),'decoded_sha256':(n or {}).get('decoded_sha256'),'source_sha256':(n or {}).get('source_sha256'),'source_files':(n or {}).get('source_files'),'function_count':len((n or {}).get('functions',[])),'nonempty_function_count':sum(f['ast_top_level_nodes']>0 for f in (n or {}).get('functions',[])),'functions':(n or {}).get('functions',[]),'raw_export_count':len((n or {}).get('raw_exports',[])),'raw_exports':(n or {}).get('raw_exports',[]),'failure_reason':(n or {}).get('failure_reason'),'behavior_status':'not_fully_explained; selected prior contracts do not prove complete behavior','runtime_verified':False,'implemented_by_this_task':False})
summary={'registry_target_class_packages':len(targets),'registry_package_counts_by_generated_class':{t:sum(t in r['assetClasses'] for r in targets.values()) for t in sorted(class_types)},'original_logic_closure_denominator_preserved':len(old),'target_packages_reused_from_306':sum(p in old for p in targets),'nonmap_gap_packages':len(missing),'new_successful_packages_including_dependencies':sum(n['status']=='decoded' for n in new.values()),'new_necessary_nonclass_logic_dependencies':sum(p not in targets for p in new),'map_embedded_class_packages_reused':len(map_nodes),'target_packages_class_identity_verified':sum(r['decode_status']=='decoded_class_verified' for r in report),'target_packages_failed_missing_or_identity_mismatch':sum(r['decode_status']!='decoded_class_verified' for r in report),'target_packages_with_raw_exports':sum(r['raw_export_count']>0 for r in report),'target_raw_export_count':sum(r['raw_export_count'] for r in report),'target_nonempty_function_count':sum(r['nonempty_function_count'] for r in report),'target_packages_fully_behavior_explained':0,'target_packages_not_fully_behavior_explained':len(targets),'runtime_verified_packages':0,'original_closure_sha256_unchanged':digest(ROOT/'dependency-closure.json')==baseline_hash}
result={'evidence_kind':'AssetRegistry identities + UAssetAPI static decoding; NOT REA native evidence; NOT runtime or Web implementation proof','scope':'All /Game packages carrying exact requested generated-class identities. Map packages reused only; no new maps/material/audio parsing. Old306 closure unchanged.','summary':summary,'sources':{'registry_path':str(ROOT/'all-package-type-coverage.json'),'registry_sha256':digest(ROOT/'all-package-type-coverage.json'),'closure_path':str(ROOT/'dependency-closure.json'),'closure_sha256':baseline_hash,'pak_identity':registry['pakIdentityFromExistingAudit']},'packages':report,'new_nodes':list(new.values()),'necessary_logic_edges':edges,'limitations':['RawExport presence is a partial parser fallback, not whole-package decode failure. Map RawExports may be geometry/landscape rather than logic; class identity and function AST are checked separately.','Verified class identities/AST do not establish reachability, runtime use, algorithm interpretation, native helper semantics, or behavior parity.','Fully behavior explained=0 is a conservative full-package standard; prior player/combat/city contracts still provide partial evidence.','BPGC inside LevelSequence and World remain distinct groups even when decoded; registry type is never inferred from filename.','Original306 hard-import closure remains a separate denominator and is not rewritten.']}
write('all-blueprint-coverage.json',result)
md=['# 全项目蓝图静态覆盖补充','','本报告按 AssetRegistry 的真实生成类身份统计，包含地图/序列共包类。新增解析严格限非地图缺口及其必要逻辑硬依赖；17个地图内类仅复查已有JSON。原306包闭包及其报告不变。','','| 指标 | 包数/数量 |','|---|---|']
labels={'registry_target_class_packages':'真实目标类包','target_packages_reused_from_306':'原306闭包已覆盖目标类包','nonmap_gap_packages':'本轮非地图类包缺口','new_necessary_nonclass_logic_dependencies':'新增必要非类逻辑依赖','map_embedded_class_packages_reused':'复用既有地图内类包','target_packages_class_identity_verified':'已解析且类身份匹配','target_packages_failed_missing_or_identity_mismatch':'失败/缺失/类身份不匹配','target_packages_with_raw_exports':'含RawExport的目标包','target_raw_export_count':'目标包RawExport总数','target_nonempty_function_count':'非空函数AST数量','target_packages_not_fully_behavior_explained':'尚未完整解释行为的包','runtime_verified_packages':'运行时验证包'}
md += [f'|{label}|{summary[k]}|' for k,label in labels.items()]
md += ['','类型分母：'+json.dumps(summary['registry_package_counts_by_generated_class'],ensure_ascii=False)+'。','','解析成功只说明类身份、函数AST/默认属性可读；不是完整行为解释或Web功能实现。所有291包按完整包标准仍未全面解释；此前玩家/战斗/市民合同是局部解释，不应丢弃或夸大。','','RawExport按包单列。地图中的RawExport可能属于几何/地形数据；不能据此断言LevelScript函数未解析，也不能把有RawExport的包称作完全解析。','','逐包注册表证据、ClassExport身份、函数数量、RawExport对象、失败原因、SHA与必要依赖见 [all-blueprint-coverage.json](./all-blueprint-coverage.json)。','']
for group in ['original_306_closure','registry_gap_supplement','map_embedded_class']:
    rr=[x for x in report if x['group']==group]
    md += [f'## {group}：{len(rr)} 包','','| 包 | 身份状态 | 函数 | RawExport |','|---|---|---|---|']
    md += [f"|{x['package']}|{x['decode_status']}|{x['function_count']}|{x['raw_export_count']}|" for x in rr]
    md += ['']
md += ['## 边界','']+['- '+s for s in result['limitations']]
(ROOT/'all-blueprint-coverage.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(summary),flush=True)
