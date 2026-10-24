"""Decode only missing material dependencies explicitly used by published geometry."""
import importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('restore',Path(__file__).with_name('restore-world-materials.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
nodes,files=m.inputs();g=m.read(m.OUT/'geometry-manifest.json');refs=set()
for asset in g['assets']:
 for s in asset['sourceMaterialSlots']:
  if s.get('material') and s['material'].get('package'):refs.add(s['material']['package'])
for level in g['levels']:
 for obj in level['objects']:
  for s in obj.get('materialOverrides',[]):
   if s.get('material') and s['material'].get('package'):refs.add(s['material']['package'])
for obj in g.get('unresolvedComponents',[])+g.get('gaps',[]):
 for s in obj.get('materialOverrides',[]):
  if s.get('material') and s['material'].get('package'):refs.add(s['material']['package'])
inventory={p.casefold():p for p in (m.ROOT/'research/evidence/pak-files.txt').read_text().splitlines()}
output=m.WORK/'material-supplement.json';old=m.read(output) if output.exists() else {'packages':{}}
records=old['packages'];pending={p for p in refs if '#export:' not in p}-set(files);seeds=sorted(pending);types={'Material','MaterialInstanceConstant','MaterialFunction','MaterialParameterCollection','SubsurfaceProfile','Texture2D','TextureCube'}
while pending:
 pkg=sorted(pending)[0];pending.remove(pkg)
 if pkg in files:continue
 record={'package':pkg,'status':'failed'}
 try:
  wanted=[inventory[(m.relative(pkg)+ext).casefold()] for ext in ['.uasset','.uexp'] if (m.relative(pkg)+ext).casefold() in inventory]
  assert wanted,'Exact package absent from Pak inventory; no broad extraction attempted'
  cmd=[m.TOOLS/'bin/repak.exe','unpack',m.PAK,'-o',m.SOURCE,'-q']
  for p in wanted:cmd+=['-i',p]
  result=m.run(cmd);assert result.returncode==0
  source=m.SOURCE/inventory[(m.relative(pkg)+'.uasset').casefold()];target=m.WORK/'material-decoded'/(m.relative(pkg)+'.json');target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():
   result=m.run([m.TOOLS/'uasset-net472/UAssetGUI.exe','tojson',source,target,'VER_UE4_27']);assert result.returncode==0 and target.exists()
  doc=m.read(target);record.update(status='decoded-imports-properties',decodedFile=str(target),decodedSha256=m.sha(target),sourceFiles=[{'path':str(m.SOURCE/p),'sha256':m.sha(m.SOURCE/p)} for p in wanted])
  record['dependencies']=[]
  for i,x in enumerate(doc['Imports']):
   if x.get('ClassName') in types:
    dst=m.ref(doc,-i-1)
    if dst and dst.startswith(('/Game/','/Engine/')) and dst!=pkg:
     record['dependencies'].append({'package':dst,'type':x['ClassName'],'pointer':f'/Imports/{i}'})
     if dst not in files and dst not in records:pending.add(dst)
  files[pkg]=target
 except Exception as exc:record['error']=str(exc)
 records[pkg]=record
 m.write(output,{'scope':'Only exact missing sourceMaterialSlots and materialOverrides from geometry-manifest, recursively expanded through material resource imports','geometrySha256':m.sha(m.OUT/'geometry-manifest.json'),'seedPackages':seeds,'packages':records,'pendingPackages':sorted(pending)})
 print(pkg,record['status'],'pending',len(pending),flush=True)
