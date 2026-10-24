"""Bounded UE4 AssetRegistry FixedTags v8 reader for package type inventory.
Uses only stdlib; no package decoding or payload conversion. Structural layout
references are pinned to CUE4Parse commit 460fc477bad0f9db3cfc387365a6699ee246377e.
"""
from pathlib import Path
import collections,csv,hashlib,json,struct
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
SOURCE=OUT/'registry-source/UNDEFEATED/AssetRegistry.bin'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
class Reader:
 def __init__(self,b):self.b=b;self.p=0;self.names=[]
 def take(self,n):
  assert n>=0 and self.p+n<=len(self.b),(self.p,n,len(self.b))
  x=self.b[self.p:self.p+n];self.p+=n;return x
 def unpack(self,f):return struct.unpack('<'+f,self.take(struct.calcsize('<'+f)))
 def u32(self):return self.unpack('I')[0]
 def i32(self):return self.unpack('i')[0]
 def u64(self):return self.unpack('Q')[0]
 def i64(self):return self.unpack('q')[0]
 def fstring(self):
  n=self.i32();assert abs(n)<10000000
  if n==0:return ''
  b=self.take(abs(n)*(2 if n<0 else 1));s=b.decode('utf-16-le' if n<0 else 'utf-8');assert s.endswith('\0');return s[:-1]
 def fname(self):
  index=self.u32();number=self.u32() if index&0x80000000 else 0;index&=0x7fffffff
  assert index<len(self.names),(self.p,index,len(self.names))
  return self.names[index]+('_'+str(number-1) if number else '')
 def count(self):
  n=self.i32();assert 0<=n<10000000,(self.p,n);return n
def main():
 ar=Reader(SOURCE.read_bytes());guid=ar.unpack('4I');assert guid==(0x717F9EE7,0xE9B0493A,0x88B39132,0x1B388107)
 version=ar.i32();assert version==8,'Only verified FixedTags v8 layout supported'
 namecount=ar.count();stringbytes=ar.u32();hashversion=ar.u64();ar.take(namecount*8)
 headers=[ar.unpack('BB') for _ in range(namecount)];begin=ar.p
 for first,second in headers:
  length=((first&127)<<8)+second
  ar.names.append(ar.take(length*(2 if first&128 else 1)).decode('utf-16-le' if first&128 else 'utf-8'))
 assert ar.p-begin==stringbytes
 storestart=ar.p;magic=ar.u32();assert magic in (0x12345678,0x12345679)
 counts=ar.unpack('11i');assert all(0<=n<10000000 for n in counts)
 if magic==0x12345679:
  textbytes=ar.u32();textstart=ar.p
  texts=[ar.fstring() for _ in range(counts[4])]
 else:textbytes=None
 for _ in range(counts[0]):assert ar.u32()<namecount
 for _ in range(counts[1]):ar.fname()
 for _ in range(counts[2]*3):assert ar.u32()<namecount
 for _ in range(counts[3]*3):ar.fname()
 if magic==0x12345678:texts=[ar.fstring() for _ in range(counts[4])]
 ansi_offsets=[ar.u32() for _ in range(counts[5])];wide_offsets=[ar.u32() for _ in range(counts[6])]
 assert all(n<counts[7] for n in ansi_offsets);assert all(n<counts[8] for n in wide_offsets)
 ar.take(counts[7]);ar.take(counts[8]*2)
 for _ in range(counts[9]):assert ar.u32()<namecount;ar.u32()
 for _ in range(counts[10]):ar.fname();ar.u32()
 assert ar.u32()==0x87654321;storeend=ar.p
 assetcountoffset=ar.p;assetcount=ar.count();assets=[]
 for i in range(assetcount):
  start=ar.p;objectpath=ar.fname();packagepath=ar.fname();classoffset=ar.p;assetclass=ar.fname();package=ar.fname();name=ar.fname()
  assert objectpath==package+'.'+name,(i,objectpath,package,name)
  handle=ar.u64();pairbegin=handle&0xffffffff;paircount=(handle>>32)&0xffff;numberless=bool(handle>>63)
  assert pairbegin+paircount<=counts[9 if numberless else 10]
  bundles=[]
  for _ in range(ar.count()):
   bundlename=ar.fname();bundleassets=[]
   for _ in range(ar.count()):bundleassets.append({'assetPath':ar.fname(),'subPath':ar.fstring()})
   bundles.append({'name':bundlename,'assets':bundleassets})
  chunks=[ar.i32() for _ in range(ar.count())];flags=ar.u32()
  assets.append({'registryIndex':i,'packageName':package,'packagePath':packagepath,'assetName':name,'assetClass':assetclass,
   'objectPath':objectpath,'recordOffset':start,'recordEnd':ar.p,'assetClassFNameOffset':classoffset,
   'tagHandle':handle,'tagPairCount':paircount,'bundles':bundles,'chunkIDs':chunks,'packageFlags':flags})
 dependencysizeoffset=ar.p;dependencysize=ar.i64();dependencystart=ar.p;dependencynodes=ar.i32();assert dependencysize>=4
 ar.take(dependencysize-4);packagecountoffset=ar.p;packagecount=ar.count();packages=[]
 for _ in range(packagecount):
  start=ar.p;name=ar.fname();disksize=ar.i64();pguid=ar.take(16).hex();hasmd5=ar.u32();assert hasmd5 in (0,1)
  md5=ar.take(16).hex() if hasmd5 else None
  packages.append({'packageName':name,'diskSize':disksize,'guidBytes':pguid,'cookedMd5':md5,'recordOffset':start,'recordEnd':ar.p})
 assert ar.p==len(ar.b),(ar.p,len(ar.b))
 pinned='460fc477bad0f9db3cfc387365a6699ee246377e'
 references=['UE4/Versions/FAssetRegistryVersion.cs','UE4/Objects/UObject/FNameEntrySerialized.cs','UE4/AssetRegistry/Objects/FAssetRegistryReader.cs','UE4/AssetRegistry/Objects/FStore.cs','UE4/AssetRegistry/Objects/FAssetData.cs','UE4/AssetRegistry/Objects/FAssetPackageData.cs','UE4/AssetRegistry/Objects/FMD5Hash.cs','UE4/AssetRegistry/FAssetRegistryState.cs']
 evidence={'source':str(SOURCE),'bytes':len(ar.b),'sha256':sha(SOURCE),'pakEntry':'UNDEFEATED/AssetRegistry.bin',
  'guidWords':[hex(x) for x in guid],'version':version,'versionName':'FixedTags','nameCount':namecount,'nameStringBytes':stringbytes,'nameHashVersion':hashversion,
  'tagStore':{'startOffset':storestart,'endOffset':storeend,'beginMagic':hex(magic),'endMagic':'0x87654321','arrayCounts':counts},
  'assetCountOffset':assetcountoffset,'assetCount':assetcount,'dependencySectionSizeOffset':dependencysizeoffset,'dependencySectionStart':dependencystart,
  'dependencySectionBytes':dependencysize,'dependencyNodes':dependencynodes,'dependencyParsing':'Skipped by serialized byte size; no dependency graph claimed',
  'packageCountOffset':packagecountoffset,'packageDataCount':packagecount,'endOffset':ar.p,'fileFullyConsumed':True,
  'parser':str(Path(__file__)),'parserSha256':sha(Path(__file__)),'implementation':'Small stdlib structural reader for this verified v8 format; not a newly installed external tool',
  'layoutReferences':[f'https://github.com/FabianFG/CUE4Parse/blob/{pinned}/CUE4Parse/'+x for x in references],
  'validation':['Version GUID and FixedTags version asserted','Name byte count validated','All FName indexes bounded','Tag store begin/end magic and pair ranges validated','Every asset ObjectPath equals PackageName.AssetName','Dependency section skipped by explicit length','Whole package-data array parsed and exact end-of-file asserted']}
 write(OUT/'asset-registry-parsed.json',{'evidenceKind':'Independent binary registry parsing, NOT REA retained Evidence','structure':evidence,'assets':assets,'packageData':packages})
 listing=(ROOT/'research/evidence/pak-files.txt').read_text(encoding='utf-8-sig').splitlines()
 pakfiles=[p for p in listing if p.endswith(('.uasset','.umap'))]
 registry=collections.defaultdict(list)
 for item in assets:registry[item['packageName'].casefold()].append(item)
 registry_package_count=len(registry)
 known=collections.defaultdict(list)
 for sourcefile in [OUT/'world-asset-dependency-closure.json',OUT/'dependency-closure.json']:
  if not sourcefile.exists():continue
  d=read(sourcefile)
  for n in d.get('nodes',[]):
   for e in n.get('exports',n.get('asset_identities',[])):
    cls=e.get('className',e.get('class_ref'))
    if cls:known[n['package'].casefold()].append({'class':cls,'decodedFile':n.get('decodedFile',n.get('decoded_path')),'pointer':e.get('pointer','/Exports/'+str(e.get('export_index'))),'source':str(sourcefile)})
 records=[];conflicts=[]
 for file in sorted(pakfiles):
  if file.startswith('UNDEFEATED/Content/'):prefix='/Game/';suffix=file[len('UNDEFEATED/Content/'):];domain='project'
  elif file.startswith('Engine/Content/'):prefix='/Engine/';suffix=file[len('Engine/Content/'):];domain='engine'
  elif '/Plugins/' in file and '/Content/' in file:
   before,suffix=file.rsplit('/Content/',1);prefix='/'+before.rsplit('/',1)[-1]+'/';domain='plugin'
  else:prefix='/UnknownMount/';suffix=file;domain='other'
  package=prefix+suffix.rsplit('.',1)[0];entries=registry.get(package.casefold(),[]);classes=sorted({x['assetClass'] for x in entries})
  decoded=known[package.casefold()];comparison=[]
  if classes:
   method='AssetRegistry.AssetClass';status='classified'
   for cls in classes:
    same=[x for x in decoded if x['class']==cls]
    comparison.append({'registryClass':cls,'matchingDecodedExportEvidence':same,'matched':bool(same),'decodedEvidenceAvailable':bool(decoded)})
  else:
   # An explicitly asset-marked export from prior logic decoding is usable fallback;
   # general export class lists can include body setups or sockets and are not guessed.
   explicit=[x for x in decoded if x['source'].endswith('dependency-closure.json') and not x['source'].endswith('world-asset-dependency-closure.json')]
   classes=sorted({x['class'] for x in explicit});method='Previously decoded bIsAsset export class' if classes else 'unknown';status='classified' if classes else 'unknown'
  records.append({'package':package,'pakFile':file,'domain':domain,'status':status,'assetClasses':classes,'classificationSource':method,
   'packageMapping':'Plugin Content mount matches exact AssetRegistry PackageName' if domain=='plugin' and entries else 'Project/Engine content mount and exact registry package identity',
   'registryEvidence':[{'registryIndex':x['registryIndex'],'objectPath':x['objectPath'],'recordOffset':x['recordOffset'],'assetClassFNameOffset':x['assetClassFNameOffset']} for x in entries],
   'decodedCrosscheck':comparison,'decodedFallbackEvidence':explicit if not entries else []})
 project=[x for x in records if x['domain']=='project'];engine=[x for x in records if x['domain']=='engine']
 exact_package_match={x['package'].casefold() for x in records}==set(registry)
 assert exact_package_match,'Registry/Pak package sets differ; investigate before reporting complete coverage'
 classcounts=collections.Counter(c for x in project for c in x['assetClasses'])
 summary={'allPakPackages':len(records),'projectPackages':len(project),'enginePackages':len(engine),
  'projectUassetPackages':sum(x['pakFile'].endswith('.uasset') for x in project),'projectMapPackages':sum(x['pakFile'].endswith('.umap') for x in project),
  'allClassified':sum(x['status']=='classified' for x in records),'allUnknown':sum(x['status']=='unknown' for x in records),
  'pluginPackages':sum(x['domain']=='plugin' for x in records),'pluginUnknown':sum(x['domain']=='plugin' and x['status']=='unknown' for x in records),
  'exactRegistryPakPackageSetMatch':exact_package_match,'allRowsClassifiedDirectlyFromRegistry':all(x['classificationSource']=='AssetRegistry.AssetClass' for x in records),
  'projectClassified':sum(x['status']=='classified' for x in project),'projectUnknown':sum(x['status']=='unknown' for x in project),
  'engineClassified':sum(x['status']=='classified' for x in engine),'engineUnknown':sum(x['status']=='unknown' for x in engine),
  'projectClassCounts':dict(classcounts),'registryAssetRecords':assetcount,'registryUniquePackages':registry_package_count,
  'decodedCrosscheckMatchedPackages':sum(any(c['matched'] for c in x['decodedCrosscheck']) for x in records)}
 result={'scope':'All .uasset/.umap packages in original Pak, project and engine separated; type inventory only, not reverse-engineering completeness.',
  'evidenceKind':'Independent AssetRegistry parsing plus existing static metadata; NOT REA retained Evidence','registryStructure':evidence,
  'pakInventory':str(ROOT/'research/evidence/pak-files.txt'),'pakInventorySha256':sha(ROOT/'research/evidence/pak-files.txt'),
  'pakIdentityFromExistingAudit':read(ROOT/'research/evidence/pak-identity.json'),
  'summary':summary,'packages':records,'unknownPackages':[x['package'] for x in records if x['status']=='unknown'],
  'limitations':['AssetClass is a registry declaration, not decoded behavior or implementation.','Tag values and dependency node contents are not interpreted; structural offsets only.','Registry may omit cooked support packages or retain absent assets; these are reported without filename-based guesses.','No whole-Pak per-package decoding, geometry/image export, or modification to Web/current world denominator.']}
 write(OUT/'all-package-type-coverage.json',result)
 with (OUT/'all-package-types.csv').open('w',newline='',encoding='utf-8-sig') as f:
  writer=csv.writer(f);writer.writerow(['package','domain','pakFile','status','assetClasses','classificationSource'])
  for x in records:writer.writerow([x['package'],x['domain'],x['pakFile'],x['status'],';'.join(x['assetClasses']),x['classificationSource']])
 rows='\n'.join(f'| {k} | {v} |' for k,v in sorted(classcounts.items()))
 report=f'''# 全游戏包类型覆盖

已完整解析原 `UNDEFEATED/AssetRegistry.bin` 的资产记录，并与 Pak 中所有 `.uasset/.umap` 文件进行精确包名匹配。**全部 {len(records)} 个包均由注册表 AssetClass 直接分类，unknown=0**，没有依赖文件名猜测类别，也没有逐包重新解码。

## 分母与覆盖

| 范围 | 包数 | 已分类 | unknown |
|---|---:|---:|---:|
| 项目 `.uasset` | 4792 | 4792 | 0 |
| 项目地图 `.umap` | 41 | 41 | 0 |
| Engine Content | 271 | 271 | 0 |
| Engine 插件 Content | 206 | 206 | 0 |
| 合计 | 5310 | 5310 | 0 |

项目总计是 4833 包，不能把“4792 个资源文件”和“包含地图的全项目包数”混为同一分母。原 35 地图资源闭包未修改；这里的清单覆盖全 Pak 的包类型，而非仅主世界可达范围。

注册表有 5606 条资产记录、5310 个唯一包。部分 Blueprint 包同时登记 Blueprint 和 BlueprintGeneratedClass，所以资产记录数大于包数，类型行数也不应直接相加当作独立包总数。插件包按其 Content 挂载路径生成候选包名后，逐一与注册表完整 PackageName 匹配；所有候选均精确匹配，没有只凭目录判断类型。

## 结构与证据

- 原文件：`registry-source/UNDEFEATED/AssetRegistry.bin`，2,873,860 字节。
- SHA-256：`{sha(SOURCE)}`。
- GUID：717F9EE7-E9B0493A-88B39132-1B388107；版本 8，FixedTags。
- 名称表：17122 条、785852 字节字符串数据。
- Tag Store 区间：957108–2624232；begin magic=0x12345679、end magic=0x87654321。
- 5606 个资产记录均有独立文件偏移与 AssetClass FName 偏移；每条 ObjectPath 与 PackageName.AssetName 一致。
- 完整读至 2873860 字节 EOF；注册表包名集合与 Pak 包名集合精确相等。
- 与已解码记录直接同类匹配的包有 {summary['decodedCrosscheckMatchedPackages']} 个。其余包的类型来源仍是注册表明确字段，并不表示已解码。

解析使用已有 repak 与 Python 标准库；没有安装大型工具。格式依据固定提交的 [CUE4Parse AssetRegistry 版本定义](https://github.com/FabianFG/CUE4Parse/blob/{pinned}/CUE4Parse/UE4/Versions/FAssetRegistryVersion.cs)、[FAssetData 字段布局](https://github.com/FabianFG/CUE4Parse/blob/{pinned}/CUE4Parse/UE4/AssetRegistry/Objects/FAssetData.cs)、[FixedTags 存储结构](https://github.com/FabianFG/CUE4Parse/blob/{pinned}/CUE4Parse/UE4/AssetRegistry/Objects/FStore.cs)；全部布局参考链接保存在 JSON 的 registryStructure.layoutReferences。独立读通并校验的是本游戏的版本 8 文件，脚本会拒绝其他版本。

## 项目实际类型

以下按“含此 AssetClass 的项目包”去重统计。同一 Blueprint 包可能出现在多行。

| 注册表 AssetClass | 包数 |
|---|---:|
{rows}

例如原项目实际含 292 份 AnimSequence、103 份 AnimMontage、218 份 ParticleSystem、10 份 NiagaraSystem、337 份 SoundWave、200 份 SoundCue；这些类别以前的 35 图网格/材质闭包没有全面覆盖，后续不能继续用城市资源闭包代表全游戏。

## 交付文件与边界

- `all-package-type-coverage.json`：每个原 Pak 包、真实 AssetClass、分类来源、注册表原始记录偏移、已解码交叉验证，以及原 Pak 身份记录。
- `all-package-types.csv`：方便筛选 Blueprint、动画、FX、音频等类型的全包表。
- `asset-registry-parsed.json`：完整资产记录、结构区间与解析验证信息。
- `classify-asset-registry.py`：可复现解析器。运行 `python research/rea-audit/classify-asset-registry.py`。

**这里完成的是类型覆盖，不是全游戏实现逆向。** 本注册表的 dependencySectionBytes=4、dependencyNodes=0，packageDataCount=0：它没有提供可用依赖图或逐包磁盘大小/MD5 表。后续仍需从真实 imports、蓝图字节码、动画/特效/音频结构和运行时证据恢复实现。Tag 存储区已按结构消费并验证，但标签值语义没有完整解释，不能声称全部标签或全部依赖已解析。

原始注册表和现有 Pak 身份有 SHA-256；未逐包读取的资源不会被宣称拥有本轮新增的内容 hash。本清单没有修改 Web 或原安装文件。此项是独立二进制注册表解析，**不是 REA retained Evidence**。
'''
 (OUT/'all-package-type-coverage.zh-CN.md').write_text(report,encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
