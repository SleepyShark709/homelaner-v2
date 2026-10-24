"""Bounded supplement: six shipped maps outside MainLevel's stored reference closure."""
import collections, concurrent.futures, importlib.util, json, pathlib, re

OUT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_audit',OUT/'audit-world.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def main():
    world_path=OUT/'world-coverage.json'; before=a.digest(world_path); world=a.read(world_path)
    pak_index=a.ROOT/'research/evidence/pak-files.txt'
    entries=[s.strip() for s in pak_index.read_text(encoding='utf-8-sig').splitlines() if s.strip().endswith('.umap')]
    game={ '/Game/'+s.removeprefix('UNDEFEATED/Content/').removesuffix('.umap'):s for s in entries if s.startswith('UNDEFEATED/Content/') }
    known={r['package'] for r in world['levels']}; remaining=sorted(set(game)-known)
    assert len(game)==41 and len(known)==35 and len(remaining)==6
    a.DECODED=OUT/'decoded-other-maps'
    records=list(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(a.decode,remaining))
    a.write(OUT/'other-map-decode-manifest.json',{'tool':str(a.TOOL),'toolSha256':a.digest(a.TOOL),'records':records})
    a.OUT=OUT/'other-map-details'
    summaries=[a.summarize(r,{'objects':[]})[0] for r in records if 'error' not in r]
    names={s.rsplit('/',1)[1]:s for s in remaining}
    # Exact decoded string values only. NameMap matches are separated from executable/data references.
    roots=[OUT/'decoded',OUT/'decoded-blueprints',OUT/'decoded-world',OUT/'decoded-other-maps',a.ROOT/'research/exports/decoded',a.EXISTING,a.ROOT/'research/evidence/combat-decoded']
    files=sorted({p for root in roots if root.exists() for p in root.rglob('*.json')})
    corpus=[]; hits=[]; calls=[]; soft=[]; parsed_count=0
    def identify(value):
        if not isinstance(value,str):return None
        if value in names:return value
        for name,package in names.items():
            if value in (package,package+'.'+name,"World'"+package+'.'+name+"'"):return name
        return None
    for file in files:
        content=file.read_text(encoding='utf-8-sig')
        corpus.append({'path':str(file),'sha256':a.digest(file),'bytes':file.stat().st_size})
        if not any(name in content for name in names):continue
        data=json.loads(content)
        if not isinstance(data,dict) or 'Exports' not in data:continue
        parsed_count+=1;pkg=a.Package(data,file.stem)
        def walk(v,path,ancestors,export_index=None):
            if isinstance(v,dict):
                if v.get('StackNode') and isinstance(v.get('Parameters'),list):
                    targets=[identify(x.get('Value')) for x in v['Parameters'] if isinstance(x,dict)]
                    targets=[x for x in targets if x]
                    for name in targets:
                        calls.append({'targetMap':name,'source':str(file),'exportIndex':export_index,'function':pkg.objname(export_index) if export_index else None,'jsonPath':path,'callee':pkg.objname(v['StackNode']),'node':v})
                for k,x in v.items():walk(x,path+'/'+k,ancestors+[v],export_index)
            elif isinstance(v,list):
                for i,x in enumerate(v):walk(x,path+'/'+str(i),ancestors,export_index)
            else:
                target=identify(v)
                if target:
                    kind='name-table-only' if path.startswith('/NameMap/') else 'serialized-reference-or-value'
                    if '/ScriptBytecode/' in path:kind='bytecode-exact-name-or-string'
                    if path.startswith('/Imports/'):kind='import'
                    types=[d.get('$type','') for d in ancestors]
                    if any('SoftObject' in t or 'SoftObjectPath' in t for t in types):kind='soft-object-reference'
                    # World own object names are not incoming references from another package.
                    own=file.stem==target
                    rec={'targetMap':target,'source':str(file),'exportIndex':export_index,'exportName':pkg.objname(export_index) if export_index else None,'jsonPath':path,'value':v,'kind':kind,'isOwnPackage':own}
                    if '/ScriptBytecode/' in path:
                        rec['expression']=next((d for d in reversed(ancestors) if 'EX_' in d.get('$type','')),None)
                        rec['statementContext']=next((d for d in reversed(ancestors[:-1]) if any(t in d.get('$type','') for t in ('EX_Let','EX_Call','EX_Context'))),None)
                    hits.append(rec)
                    if kind=='soft-object-reference':soft.append(rec)
        for k in ['NameMap','Imports','SoftPackageReferenceList']:
            if k in data:walk(data[k],'/'+k,[])
        for i,export in enumerate(pkg.ex,1):walk(export,'/Exports/'+str(i-1),[],i)
    # Detailed per-package reports remain separate from the 35-map world statistics.
    rows=[]
    for s in summaries:
        name=s['name'];detail=a.read(a.OUT/s['details'])
        s['details']=str((a.OUT/s['details']).relative_to(OUT))
        external=[h for h in hits if h['targetMap']==name and not h['isOwnPackage'] and h['kind']!='name-table-only']
        incoming_stream=[]
        for source in world['levels']:
            d=a.read(OUT/source['details'])
            incoming_stream.extend({'sourcePackage':source['package'],'record':r} for r in d['streamingRecords'] if r.get('package')==s['package'])
        rows.append({**s,'pakEntry':game[s['package']],'scopeClassification':'outside MainLevel stored streaming-reference closure; runtime use not established','runtimeUseProven':False,'externalExactReferences':external,'directNameCallSites':[c for c in calls if c['targetMap']==name],'incomingStoredStreamingFromMainClosure':incoming_stream,'outgoingStoredStreaming':detail['streamingRecords'],'directMeshImports':detail['meshImports'],'directMaterialImports':detail['materialImports'],'referenceInterpretation':'Exact bytecode/data matches prove retained references, not branch reachability or successful loading. Own-package identity and name-table-only strings are not incoming use evidence.'})
    result={'scope':'All 41 shipped /Game maps: existing 35-map stored MainLevel reference closure + six separately audited packages. Engine Entry is excluded from game map count. No runtime activity inferred.','pakInventory':str(pak_index),'pakInventorySha256':a.digest(pak_index),'gameMapCount':len(game),'mainWorldStoredClosureCount':len(known),'supplementalMapCount':len(rows),'engineMapsExcluded':[x for x in entries if not x.startswith('UNDEFEATED/Content/')],'mainWorldSummary':{'file':'world-coverage.json','sha256':before,'unchangedAfterSupplement':a.digest(world_path)==before},'allMaps':[{'package':p,'pakEntry':entry,'scope':'main-world-stored-reference-closure' if p in known else 'supplemental-runtime-use-unproven'} for p,entry in sorted(game.items())],'supplementalMaps':rows,'referenceScan':{'method':'Exact decoded scalar match to short map name, full package or World object path; distinguishes NameMap, own package identity, bytecode, import, serialized values and soft objects. Native binary computed names and runtime-generated strings not covered.','snapshotFiles':len(files),'candidateDecodedPackagesParsed':parsed_count,'corpusManifest':'other-map-reference-scan-corpus.json','allExactHits':'other-map-exact-reference-hits.json','directCallCount':len(calls),'softObjectHitCount':len(soft)},'limitations':['Package names containing Test are not proof of unused or editor-only status.','Direct LoadStreamLevel calls prove compiled requests only; branch reachability and successful dynamic registration/loading remain unknown.','Blueprint-inherited meshes absent from map component properties are not counted as explicit mesh references.','No changes to world-coverage.json denominators or demo assets/source.']}
    a.write(OUT/'other-map-reference-scan-corpus.json',corpus)
    a.write(OUT/'other-map-exact-reference-hits.json',{'hits':hits,'calls':calls,'softObjects':soft})
    a.write(OUT/'all-map-inventory.json',result)
    lines=['全部已打包游戏地图补充调查','',f'Pak 包含41份 /Game 地图；既有 MainLevel 存储引用闭包为35份。本次单独解析剩余6份，不将它们混入现有主世界统计。另有 Engine/Content/Maps/Entry.umap，不计作游戏地图。','',f'引用扫描范围：{len(files)}份现有解码JSON的快照。精确匹配短关卡名、完整包路径及World对象路径，名称表与自身包标识单列，不视作调用证据。','', '重要发现：不能因为名字含 Test 就判定未使用。DPropTest、FPropTest有明确 LoadStreamLevel / UnloadStreamLevel 字节码调用；三份 TestBossLevel 名字出现在 BP_CityManager 的名字变量赋值中。当前证据未证明这些分支在正式流程实际执行、对应动态流对象注册或异步加载成功；故仍标记为“未证明在主游戏运行时使用”。','']
    for row in rows:
        c=row['counts'];name=row['name'];lines.extend([name,'  原包：'+row['pakEntry'],f"  Actor {c['actorInstances']}；组件 {c['actorOwnedComponents']}；显式mesh组件引用 {c['resolvedMeshComponentReferences']}；直接mesh import {c['meshImports']}；直接material import {c['uniqueMaterialImports']}；地形组件 {c['landscapeComponents']}；灯光组件 {c['lightComponents']}。",'  Actor类：'+json.dumps(row['actorClassCounts'],ensure_ascii=False),'  向外存储Streaming引用：'+(', '.join(x['package'] or '?' for x in row['outgoingStoredStreaming']) or '未找到可验证的非空计数表'),f"  外部精确值/代码引用 {len(row['externalExactReferences'])} 条；直接名字实参调用 {len(row['directNameCallSites'])} 处。",'  资源与原始变换详情：'+row['details']])
        by_source=collections.Counter((pathlib.Path(h['source']).stem,h.get('exportName'),h['kind']) for h in row['externalExactReferences'])
        lines.extend('  引用来源：'+str(key)+'，'+str(count)+'条' for key,count in by_source.items())
        by_call=collections.Counter((pathlib.Path(h['source']).stem,h['callee']) for h in row['directNameCallSites'])
        lines.extend('  调用：'+str(key)+'，'+str(count)+'处' for key,count in by_call.items())
        if not row['externalExactReferences']:lines.append('  此快照扫描中未发现外部精确引用；这不是未使用的证明，也未覆盖原生代码计算名称。')
        lines.append('')
    lines.extend(['这六份地图之间的确切关系','TestLevel 的 UWorld 计数表含12个 StreamingLevels：2个 AlwaysLoaded（LightingTest、CustomEventLevel）和10个 Dynamic。后者包括剩余五份 DPropTest、FPropTest、TestBossLevelWind/Fire/Lightning，以及 TutorialLevel、Story1/2/3、EnelightMeteor。五份补充子图通过 WorldAsset 软对象路径被 TestLevel 明确引用，不只是名字相似。','BP_ChallengQuestSpawnPoint 对 DPropTest、FPropTest 各有2处 LoadStreamLevel、5处 UnloadStreamLevel。加载参数均为可见true、不阻塞false。这些编译代码与 TestLevel 的流式子图配置相符；尚未证明它们在 MainLevel 正式流程中实际生效。','BP_CityManager 对三个 TestBossLevel 各保留2处 EX_NameConst 赋值。不能将赋值本身等同已加载；精确上下文已保留。','未发现指向 TestLevel 的外部精确名字/软对象引用，但扫描范围仅限列明的已解码JSON快照，不排除原生代码、配置、命令行或动态拼接路径。','DPropTest有19个原破坏道具蓝图Actor；FPropTest有11个飞行环；三份Boss子图各含对应Boss Actor。它们显式mesh组件引用为0，不代表没有可见模型，模型可能由蓝图模板继承。TestLevel还含真实InstancedFoliageActor，不能套用35图闭包中没有此类Actor的结论。','', '统计边界与完成状态','world-coverage.json 的35图、8,817 Actor、5,463个显式mesh引用分母保持不变；这只是存储引用闭包，不可称所有可能活动地图。新增6图的内容与关系独立存放。','这次完成41份已打包游戏地图的静态内容调查范围，不等于41图全导出、全渲染或运行时使用状态全部确定。','all-map-inventory.json 为总入口；other-map-decode-manifest.json 保留源文件和解码哈希；other-map-exact-reference-hits.json 保留精确JSON路径、表达式和调用节点；扫描快照清单保留于 other-map-reference-scan-corpus.json。'])
    (OUT/'all-map-inventory.zh-CN.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    assert a.digest(world_path)==before
    print(json.dumps({'gameMaps':len(game),'supplemental':len(rows),'scanFiles':len(files),'calls':len(calls),'soft':len(soft),'worldSummaryUnchanged':True}))

if __name__=='__main__':main()
