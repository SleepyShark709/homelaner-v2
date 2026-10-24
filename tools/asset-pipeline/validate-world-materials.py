"""Validate published texture bytes, material bindings and pack contracts."""
from pathlib import Path
from urllib.parse import unquote
from functools import lru_cache
import collections,hashlib,json,math
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'public/assets/world';WORK=ROOT/'research/world-recovery'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
@lru_cache(maxsize=4096)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def local(url):return ROOT/'public'/unquote(url.lstrip('/'))
@lru_cache(maxsize=16)
def source_doc(p):return read(ROOT/p)
@lru_cache(maxsize=16384)
def checked_pointer(file,path):
 d=source_doc(file)
 for k in path.strip('/').split('/'):d=d[int(k)] if isinstance(d,list) else d[k]
 return True
def pointer(e):return checked_pointer(e['file'],e['pointer'])
m=read(OUT/'material-manifest.json');g=read(OUT/'geometry-manifest.json');errors=[];texture_bytes=0;proofs=0
refs=set()
for a in g['assets']:
 for s in a['sourceMaterialSlots']:
  if s.get('material') and s['material'].get('package'):refs.add(s['material']['package'])
for level in g['levels']:
 for o in level['objects']+level.get('unresolvedComponents',[]):
  for s in o.get('materialOverrides',[]):
   if s.get('material') and s['material'].get('package'):refs.add(s['material']['package'])
for o in g.get('unresolvedComponents',[])+g.get('gaps',[]):
 for s in o.get('materialOverrides',[]):
  if s.get('material') and s['material'].get('package'):refs.add(s['material']['package'])
missing=sorted(refs-set(m['materials']))
all_override_refs={s['materialPackage'] for o in m['instanceOverrides'] for s in o['slots'] if s['materialPackage']}
missing_override_descriptors=sorted(all_override_refs-set(m['materials']))
if missing_override_descriptors:errors.append({'missingOriginalMapOverrides':missing_override_descriptors})
for p,t in m['textures'].items():
 if t.get('url'):
  file=local(t['url'])
  if not file.exists():errors.append({'missingTexture':p});continue
  if sha(file)!=t['sha256']:errors.append({'changedTexture':p})
  texture_bytes+=file.stat().st_size
  if file.suffix=='.png':
   with Image.open(file) as im:
    if im.size!=(t['width'],t['height']):errors.append({'textureDimensionMismatch':p})
    im.verify()
  if t.get('normalConvention')=='directx' and 'inverted G hypothesis rejected' not in t.get('validation',''):errors.append({'weakNormalOrientationProof':p})
for p,mat in m['materials'].items():
 if mat['parent'] and mat['parent'] not in m['materials']:errors.append({'missingParent':p,'parent':mat['parent']})
 for role,c in mat.get('shaderRecovery',{}).get('textures',{}).items():
  if not local(c['url']).exists():errors.append({'missingShaderTexture':p,'role':role})
  pointer(c['evidence']);proofs+=1
  original=m['textures'][c['texturePackage']]
  if c['url']!=original['url'] or c['colorSpace']!=original['colorSpace']:errors.append({'shaderTextureIdentityMismatch':p,'role':role})
 for role,c in mat['channels'].items():
  if c:
   if not local(c['url']).exists():errors.append({'missingChannelTexture':p,'role':role})
   pointer(c['evidence']);proofs+=1
   if c['sourceParameter'].casefold() in ['compact','packedtexture','maskmetallicroughnestexture']:errors.append({'unprovenPackedBinding':p,'role':role})
 if pack:=mat.get('packedPBR'):
  assert pack['scalarFactorsAlreadyApplied'] is True
  assert pack['channels']=={'occlusion':'r','roughness':'g','metallic':'b'}
  file=local(pack['url'])
  if sha(file)!=pack['sha256']:errors.append({'changedOrm':p})
  with Image.open(file) as im:
   assert im.mode=='RGB' and im.size==(pack['width'],pack['height']);im.verify()
 if pack:=mat.get('packedOpacity'):
  assert pack['scalarFactorsAlreadyApplied'] is False and pack['channel']=='a' and pack['colorSpace']=='linear'
  file=local(pack['url']);c=mat['channels']['opacity'];src=local(c['url'])
  if sha(file)!=pack['sha256']:errors.append({'changedPackedOpacity':p})
  with Image.open(src) as original,Image.open(file) as image:
   assert image.mode=='RGBA' and image.size==(pack['width'],pack['height'])
   expected=original.convert('RGBA').getchannel(c['channel'].upper())
   if c['colorSpace']=='srgb' and c['channel']!='a':expected=expected.point([round(255*((v/255/12.92) if v/255<=.04045 else ((v/255+.055)/1.055)**2.4)) for v in range(256)])
   if ImageChops.difference(image.getchannel('A'),expected).getbbox():errors.append({'opacityAlphaMismatch':p})
   if image.convert('RGB').getextrema()!=((255,255),(255,255),(255,255)):errors.append({'opacityRgbNotWhite':p})
summary={'geometryMaterialReferences':len(refs),'missingMaterialDescriptors':missing,'materialDescriptors':len(m['materials']),
 'allOriginalOverrideMaterialReferences':len(all_override_refs),'missingOriginalOverrideDescriptors':missing_override_descriptors,
 'referencedMaterialStatuses':dict(collections.Counter(m['materials'][p]['status'] for p in refs if p in m['materials'])),
 'statuses':dict(collections.Counter(x['status'] for x in m['materials'].values())),
 'textureStatuses':dict(collections.Counter(x['status'] for x in m['textures'].values())),
 'publishedTextureBytes':texture_bytes,'channelCounts':{role:sum(bool(x['channels'][role]) for x in m['materials'].values()) for role in ['baseColor','normal','roughness','metallic','occlusion','emissive','opacity']},
 'channelEvidencePointersValidated':proofs,'normalTextureConventions':dict(collections.Counter(x.get('normalConvention','not-normal') for x in m['textures'].values())),
 'runtimeReadyNormalBindings':sum(x['channels']['normal'] is not None and x['channels']['normal']['normalConvention']=='directx' for x in m['materials'].values()),
 'ormPackedMaterials':sum(bool(x.get('packedPBR')) for x in m['materials'].values()),
 'opacityPackedMaterials':sum(bool(x.get('packedOpacity')) for x in m['materials'].values()),'errors':errors,
 'shaderRecoveryKinds':dict(collections.Counter(x['shaderRecovery']['kind'] for x in m['materials'].values() if x.get('shaderRecovery'))),
 'manifestSha256':sha(OUT/'material-manifest.json'),'geometryManifestSha256':sha(OUT/'geometry-manifest.json'),
 'validationScope':'References/files/dimensions/hashes/source pointers/normal proof/ORM contract only. Not matched-camera original visual equivalence.'}
(WORK/'material-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f'| {k} | {v} |' for k,v in summary['channelCounts'].items())
text=f'''# 原材质恢复：实际交付与缺口

独立入口：`public/assets/world/material-manifest.json`，schemaVersion=1。没有修改几何 glTF 或游戏 src；原安装只读。

## 已交付

- 材质描述 {len(m['materials'])} 个，采用完整 UE 包名作键，保留实例父链、源参数、BasePropertyOverrides、blend/two-sided/alpha clip。
- 场景几何与组件覆写共引用 {len(refs)} 种材质包；缺失描述 {len(missing)}。
- 原像素 PNG {summary['textureStatuses'].get('exported-original-pixels',0)} 张，另保留原 HDR {summary['textureStatuses'].get('exported-original-hdr-not-bound',0)} 张；按 Game/Engine 完整包路径发布，避免同名冲突。纹理合计 {texture_bytes/1024/1024:.1f} MiB。
- {summary['normalTextureConventions'].get('directx',0)} 张法线通过原 BC5 独立解码与 PNG R/G 对照，且反向绿通道假设被数据排除；{summary['normalTextureConventions'].get('unknown',0)} 张仍为 unknown。材质中可直接使用的 normal 绑定为 {summary['runtimeReadyNormalBindings']} 个。
- ORM {summary['ormPackedMaterials']} 份，R=AO、G=roughness、B=metallic，linear；scalarFactorsAlreadyApplied=true，运行时乘数为 1。
- {len(m['instanceOverrides'])} 个原组件覆写记录另存于 instanceOverrides。运行时应使用 geometry-manifest 各对象完整 slot 覆写，并优先使用 gltfMaterials.sourceMaterial 的原 native section/slot 证据；不能把 glTF materialIndex 当 UE slotIndex，也不能按同名材质猜测。

| 绑定通道 | 材质数 |
|---|---:|
{rows}

## 使用约定

materials 为 package→descriptor。channels 的每个值是 null 或包含 texturePackage/url/colorSpace/channel/texCoord/sourceParameter/evidence 的对象；channel 明确是 rgb 或 r，未猜测 Compact 或 MR 包装图各通道用途。normalConvention=directx 的纹理保留原 UE 压缩像素的绿通道；根据 root 已验证的 Babylon RH/glTF 切线约定，运行时对应 invertY=false。unknown 不作已正确处理。

每张 verified normal 独立读取原 .ubulk 的 BC5 压缩块，覆盖多个分散位置，与 PNG 的 R/G 比较（≤1/255 压缩取整误差），并要求 255-G 假设不能同样匹配。小纹理内嵌数据、没有可验证 ubulk、或近乎平坦绿通道无法区分方向者保持 unknown。该证明确认导出未翻绿通道，不是整套网格法线着色的原游戏截图等价证明。

roughness/metal/AO/opacity 仅从明确单一语义的原参数挑选；当 RGB 分量相差≤8/255 时，允许把它作为 BC1 RGB565 量化后的近灰度标量图取 R，记录 scalarProjection。此为有界 PBR 投影，不声称恢复了原 shader 的所有数学运算。ORM 会按源 SRGB 状态线性化输入并烘入显式标量，必要时双线性调整尺寸。未知通道使用的 AO=1/roughness=1/metal=0 中性常量列入 fallbackChannels，**不计为原效果恢复**。

## 尚未恢复

status=partial-pbr-projection 的材质 {summary['statuses'].get('partial-pbr-projection',0)} 个，表示可利用部分原数据；partial-dxbc-recovery 的材质 {summary['statuses'].get('partial-dxbc-recovery',0)} 个，附有从原 DXBC 验证的 shaderRecovery 运算契约；shader-unmapped 的材质 {summary['statuses'].get('shader-unmapped',0)} 个，没有足够证据绑定其主要着色输入。没有任何状态声称完整 UE 渲染效果已重建。

源参数可证明纹理的作者语义，但完整编译 shader 的连接和表达式仍未还原。固定 ReferencedTextures 没有明确角色的材料不会按纹理文件名或旧 UModel Diffuse 猜接。原 Compact/MR 通道、地形 Grass/Sand/Ground 权重混合、SSS、服装 ID 区域染色、风摆/顶点偏移、detail normal、world-aligned UV、积水/雪层、透明折射和自定义玻璃均保留缺口。普通纹理绑定使用 mesh UV0 投影，原 shader UV 计算未证明的部分有 uvMappingStatus 标记。

HDR 原数据已保留，但未强制转为普通颜色 PNG 绑定。材质父链中没有的运行时 DynamicMaterial 参数变化也未模拟。颜色与系数来自原参数，未沿用旧脚本按材料文件名填色的策略。

## 验证与复现

`material-validation.json` 记录全部文件/hash/尺寸、{proofs} 个源指针、原几何材质引用和 ORM 契约核查；当前错误 {len(errors)}。未执行原游戏与 Web 同机位视觉等价测试。本项是独立原资产处理，不是 REA retained Evidence。

使用已提供的带 Pillow 的 Python 运行：

```powershell
python tools/asset-pipeline/supplement-world-materials.py
python tools/asset-pipeline/restore-world-materials.py
python tools/asset-pipeline/restore-embedded-materials.py
python tools/asset-pipeline/restore-evidenced-shaders.py
python tools/asset-pipeline/restore-evidenced-shaders-round2.py
python tools/asset-pipeline/validate-evidenced-shaders.py
python tools/asset-pipeline/validate-evidenced-shaders-round2.py
python tools/asset-pipeline/validate-world-materials.py
```

若仅更新绑定规则，可加 `--skip-export --reuse-texture-cache` 复用刚验证过且解码源 hash 不变的纹理缓存。完整恢复的源提取、工具日志与新增材料依赖均保存在 `research/world-recovery/material*`。
'''
(WORK/'material-restoration-report.zh-CN.md').write_text(text,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
assert not errors and not missing,(errors,missing)
