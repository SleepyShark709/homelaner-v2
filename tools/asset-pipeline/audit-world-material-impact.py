"""Count exact current runtime section bindings; not camera-visible pixel coverage."""
from pathlib import Path
import json,collections,hashlib,argparse
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
g=read(ROOT/'public/assets/world/geometry-manifest.json');m=read(ROOT/'public/assets/world/material-manifest.json')['materials']
assets={a['id']:a for a in g['assets']};rows={};hidden=0
for level in g['levels']:
 for obj in level['objects']:
  v=obj.get('visibilityProperties',{})
  if v.get('bHiddenInGame') is True or v.get('bVisible') is False or v.get('actorHidden') is True:hidden+=1;continue
  a=assets[obj['assetId']];ov={s['slotIndex']:s['material'] for s in obj.get('materialOverrides',[])};native={s['slotIndex']:s['material'] for s in a['sourceMaterialSlots']}
  seen=set()
  for section in a['gltfMaterials']:
   values={(ov.get(i) or native.get(i) or {}).get('package') for i in section['sourceSlotCandidates']}
   if len(values)!=1:continue
   pkg=next(iter(values))
   if not pkg or pkg not in m:continue
   mat=m[pkg];base=mat['baseMaterial'];identity=(level['id'],base)
   r=rows.setdefault(identity,{'level':level['id'],'scope':level['scope'],'baseMaterial':base,'sectionInstances':0,'objects':set(),'materialInstances':set(),'meshes':set(),'statuses':collections.Counter(),'withoutBaseColorSectionInstances':0,'sampleObjectIds':[]})
   r['sectionInstances']+=1;r['objects'].add(obj['id']);r['materialInstances'].add(pkg);r['meshes'].add(a.get('sourcePackage',a['id']));r['statuses'][mat['status']]+=1
   if not mat['channels']['baseColor'] and mat['factors']['baseColor'] is None and 'baseColor' not in mat.get('shaderRecovery',{}).get('authoritativeRoles',[]):r['withoutBaseColorSectionInstances']+=1
   if len(r['sampleObjectIds'])<5 and obj['id'] not in r['sampleObjectIds']:r['sampleObjectIds'].append(obj['id'])
out=[]
for r in rows.values():
 r['objectCount']=len(r.pop('objects'));r['materialInstances']=sorted(r['materialInstances']);r['meshes']=sorted(r['meshes']);out.append(r)
out.sort(key=lambda r:r['withoutBaseColorSectionInstances'],reverse=True)
summary={'method':'Same explicitlyHidden and sourceSlotCandidates/override fallback semantics as current runtime. Counts scene bindings, not rasterized screen pixels; level activation excluded from this static census.','hiddenObjectsExcluded':hidden,'levels':out}
parser=argparse.ArgumentParser();parser.add_argument('--output',default='material-shader-impact.json');args=parser.parse_args()
path=ROOT/'research/world-recovery'/args.output;path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for r in out[:35]:print(r['level'],r['baseMaterial'],r['objectCount'],r['withoutBaseColorSectionInstances'],dict(r['statuses']))
