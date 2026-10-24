"""Retain exact static Blueprint streaming call sites; never infer observed load state."""
import collections, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=pathlib.Path(__file__).resolve().parent
MANAGERS=OUT/'decoded-blueprints'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def walk(value,path=''):
    if isinstance(value,dict):
        yield path,value
        for k,v in value.items():yield from walk(v,path+'/'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value):yield from walk(v,path+'/'+str(i))
def literal(node):
    typ=node.get('$type','').split('.')[-1].split(',')[0]
    if typ=='EX_True':return True
    if typ=='EX_False':return False
    if typ in ['EX_NameConst','EX_StringConst','EX_IntConst']:return node.get('Value')
    return None
coverage=read(OUT/'world-coverage.json');paths=[pathlib.Path(r['decoded']) for r in coverage['levels'] if 'error' not in r]+[MANAGERS/(n+'.json') for n in ['BP_CityManager','BP_StoryManager','HeroGameMode']]
records=[]
for source in paths:
    d=read(source);lookup={-i:x['ObjectName'] for i,x in enumerate(d['Imports'],1)};calls=[];defaults={};wrappers=[]
    for e in d['Exports']:
        if e['ObjectName'].startswith('Default__'):
            defaults.update({p['Name']:p.get('Value') for p in e.get('Data',[]) if isinstance(p.get('Value'),(str,bool,int,float))})
        if 'FunctionExport' not in e['$type']:continue
        bytecode=e.get('ScriptBytecode',[])
        if len(bytecode)<=4:wrappers.append({'function':e['ObjectName'],'bytecode':bytecode})
        for path,node in walk(bytecode):
            callname=lookup.get(node.get('StackNode'))
            if callname not in ['LoadStreamLevel','UnloadStreamLevel','GetStreamingLevel','SetShouldBeLoaded','SetShouldBeVisible']:continue
            params=node.get('Parameters',[]);name=literal(params[1]) if len(params)>1 else None
            variable=(params[1].get('Variable',{}).get('New',{}).get('Path') if len(params)>1 else None)
            record={'function':e['ObjectName'],'bytecodeJsonPath':path,'nativeCall':callname,'levelLiteral':name,'levelVariable':variable,'exactBytecodeNode':node}
            if callname=='LoadStreamLevel':record.update(bMakeVisibleAfterLoad=literal(params[2]),bShouldBlockOnLoad=literal(params[3]))
            calls.append(record)
    if calls:
        for c in calls:
            if c['levelVariable'] and len(c['levelVariable'])==1:c['defaultVariableValue']=defaults.get(c['levelVariable'][0])
        records.append({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'callCount':len(calls),'defaultScalarProperties':defaults,'calls':calls,'shortEventWrappers':wrappers})
        print(source.stem,[(c['nativeCall'],c['levelLiteral'] or c.get('defaultVariableValue') or c['levelVariable'] or '<expression>',c.get('bMakeVisibleAfterLoad')) for c in calls])
result={'scope':'Static native streaming call sites in all decoded referenced maps plus BP_CityManager/BP_StoryManager/HeroGameMode. Branch reachability/latency completion is not assumed.','sources':records,'callCount':sum(x['callCount'] for x in records),'conclusion':'HeroGameMode contains explicit LoadStreamLevel requests for city districts with bMakeVisibleAfterLoad=true and bShouldBlockOnLoad=false. This proves intentional runtime loading code, not that every package is loaded in the current session. City/Story managers additionally load/unload selected challenge/story levels.'}
(OUT/'world-streaming-call-sites.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
coverage['streaming']['blueprintCallSites']='world-streaming-call-sites.json';coverage['streaming']['staticRuntimeRequestEvidence']=result['conclusion'];coverage['streaming']['staticNativeCallCount']=result['callCount'];(OUT/'world-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
