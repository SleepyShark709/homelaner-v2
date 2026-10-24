"""Retain exact BP_Sky function AST plus a bounded human-readable expression projection."""
import pathlib,importlib.util,json
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'research/world-recovery/sky-recovery'
spec=importlib.util.spec_from_file_location('g',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
file=g.AUDIT/'decoded/Skies/Blueprints/BP_Sky.json';d=g.READ(file);p=g.a.Package(d,'BP_Sky')
def fmt(x):
    if isinstance(x,list):return '['+', '.join(map(fmt,x))+']'
    if not isinstance(x,dict):return repr(x)
    typ=x.get('$type','').split(',')[0].rsplit('.',1)[-1]
    if typ in ('EX_InstanceVariable','EX_LocalVariable','EX_LocalOutVariable'):return '.'.join(x['Variable']['New']['Path'])
    if typ=='EX_Context':return fmt(x['ObjectExpression'])+'.'+fmt(x['ContextExpression'])
    if typ in ('EX_FinalFunction','EX_CallMath','EX_LocalFinalFunction'):return p.path(x['StackNode'])+'('+', '.join(map(fmt,x['Parameters']))+')'
    if typ in ('EX_VirtualFunction','EX_LocalVirtualFunction'):return x['VirtualFunctionName']+'('+', '.join(map(fmt,x['Parameters']))+')'
    if typ in ('EX_LetObj','EX_LetBool'):return fmt(x['VariableExpression'])+' = '+fmt(x['AssignmentExpression'])
    if typ=='EX_Let':return fmt(x['Variable'])+' = '+fmt(x['Expression'])
    if typ=='EX_ObjectConst':return p.path(x['Value'])
    if typ.endswith('Const'):return repr(x.get('Value',x))
    if typ in ('EX_False','EX_True','EX_IntZero','EX_IntOne','EX_Self','EX_NoObject'):return typ.removeprefix('EX_')
    return typ+' '+json.dumps({k:v for k,v in x.items() if k!='$type'},ensure_ascii=False)
functions=[];lines=[]
for i,e in enumerate(p.ex,1):
    if 'FunctionExport' not in e['$type']:continue
    code=e['ScriptBytecode'];functions.append({'name':e['ObjectName'],'exportIndex':i,'ast':code})
    lines.append(e['ObjectName']+' export:'+str(i))
    for j,node in enumerate(code):lines.append(str(j)+': '+fmt(node))
    lines.append('')
defaults=[{'exportIndex':i,'object':e['ObjectName'],'class':p.cls(i),'properties':p.props(i)} for i,e in enumerate(p.ex,1) if e['ObjectName'].startswith('Default__') or e['ObjectName'].endswith('GEN_VARIABLE')]
mapfile=g.AUDIT/'decoded-world/LightingTest.json';ld=g.READ(mapfile);lp=g.a.Package(ld,'LightingTest');instances=[{'exportIndex':i,'object':e['ObjectName'],'class':lp.cls(i),'properties':lp.props(i)} for i,e in enumerate(lp.ex,1) if lp.cls(i)=='BP_Sky_C' or i==22]
g.WRITE(OUT/'blueprint-evidence.json',{'source':str(file),'sha256':g.HASH(file),'functions':functions,'defaults':defaults,'mapSource':str(mapfile),'mapSourceSha256':g.HASH(mapfile),'instances':instances});(OUT/'blueprint-readable.txt').write_text('\n'.join(lines),encoding='utf-8');print('\n'.join(lines));print('DEFAULTS',defaults);print('INSTANCES',instances)
