"""Write the Chinese audit report and per-level comparison table from measured data."""
import csv,json,pathlib
OUT=pathlib.Path(__file__).resolve().parent
report=json.loads((OUT/'world-coverage.json').read_text(encoding='utf-8'))
levels=report['levels'];tot=report['totals'];comparison=report['webComparison'];streams=report['streaming']
direct={x['package']:x['class'] for x in streams['alwaysLoaded']+streams['dynamic']}
fields=['level','streamingClass','actors','components','sceneTransforms','staticMeshComponents','skeletalMeshComponents','splineMeshComponents','resolvedMeshRefs','distinctMeshRefs','directMaterialImports','embeddedMaterialInstances','materialOverrideComponents','lightComponents','postProcessVolumes','fogActors','landscapeComponents','landscapeCollisionComponents','foliageActors','instancedMeshComponents','webRepresentedMeshComponents']
rows=[]
for level in levels:
    c=level['counts'];rows.append([level['name'],direct.get(level['package'],'persistent' if level['name']=='MainLevel' else 'transitive reference; not assumed loaded'),c['actorInstances'],c['actorOwnedComponents'],c['sceneComponentTransforms'],c['staticMeshComponents'],c['skeletalMeshComponents'],c['splineMeshComponents'],c['resolvedMeshComponentReferences'],c['uniqueReferencedMeshAssets'],c['uniqueMaterialImports'],c['embeddedMaterialInstances'],c['componentsWithMaterialOverrides'],c['lightComponents'],c['postProcessVolumeActors'],c['fogActors'],c['landscapeComponents'],c['landscapeCollisionComponents'],c['foliageActors'],c['foliageOrInstancedMeshComponents'],level['webCoverage']['resolvedOriginalMeshComponentsRepresented']])
with (OUT/'world-coverage-by-level.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.writer(f);writer.writerow(fields);writer.writerows(rows)
table=['关卡 | Actor | 组件 | 明确mesh引用 | 材质import | 灯光 | 地形块 | ISM组件 | Web对应mesh组件']
for level in levels:
    c=level['counts'];w=level['webCoverage'];table.append(f"{level['name']} | {c['actorInstances']} | {c['actorOwnedComponents']} | {c['resolvedMeshComponentReferences']} | {c['uniqueMaterialImports']} | {c['lightComponents']} | {c['landscapeComponents']} | {c['foliageOrInstancedMeshComponents']} | {w['resolvedOriginalMeshComponentsRepresented']}")
text=f'''UNDEFEATED 原主地图与现 Web 覆盖差异审计

结论

现 Web 确实使用了原版模型和一片原布局，但距离完整原场景有显著差距。它只表示 MainLevel 与 ResidentialArea1 中的 252 个可明确对应源 mesh 的组件；本次审计的原关卡闭包中，直接可解析到 mesh 资源的组件为 5,463 个，前者占 4.61285%。这是“明确 mesh 引用组件”计数比，不是完成率、城市面积比、画面像素比或游戏功能完成率。大量模板继承网格、运行时生成内容和合并网格内部物体未包含在这个分母中。

因此，先前42个对象的街区不能称作“已将原游戏完整移植到Web”。它是部分真实资产/布局验证，并混合了新设计的人车巡逻、简化材质和新控制器。用户认为原场景没有充分用上，与本次覆盖数据一致。当前审计不再扩展演示功能，也未改动src或public文件。

一、范围是怎样确定的

不是把pak里所有.umap都当作已加载地图。MainLevel中UWorld export 11844的序列化尾部为148字节；其中offset 12处的int32 count为33，之后33个export index逐项解析为LevelStreaming对象，末尾恰好用完。原字节词表、哈希、索引、对象实际类和WorldAsset引用均在mainlevel-streaming-table.json。

直接引用33个子关卡，加MainLevel共34个包。另有11个子关卡自身保留对Lighting.umap的流送引用，传递闭包额外纳入Lighting，总计35份地图全部成功静态解码。Lighting与LightingTest不能混为一个关卡，也不能因此断言二者在游戏中同时生效。

4个对象的实际类为LevelStreamingAlwaysLoaded：CitizenWayPoint、LightingTest、CustomEventLevel、TitleMenuLevel。29个对象的实际类为LevelStreamingDynamic，尽管许多实例名字仍叫LevelStreamingKismet_*，这里按实际类判断。

Epic UE4.27文档说明AlwaysLoaded类随持续关卡加载并可见；动态类可由蓝图/C++控制。官方来源：
https://dev.epicgames.com/documentation/unreal-engine/level-streaming-overview?application_version=4.27

33个对象都没有显式序列化bShouldBeLoaded/bShouldBeVisible等加载状态字段。报告将缺失值记为null，不编造true或false；这些是配置和静态包数据，不是运行时内存快照。

二、动态加载不是仅凭名字推测

从当前pak重新提取并解码HeroGameMode、BP_CityManager、BP_StoryManager，连同全部地图蓝图扫描，共发现23个原生LoadStreamLevel/UnloadStreamLevel调用点，精确节点保存在world-streaming-call-sites.json。

HeroGameMode明确含Coast、ResidentialArea1/2/3、Slam、Beach、IndustrialArea、CommercialArea、FinancialDistrict、Park、DownTown的LoadStreamLevel调用，还涉及LoadLevel、DynamicProps与EnelightMeteor。读取到的加载调用参数均为bMakeVisibleAfterLoad=true、bShouldBlockOnLoad=false。BP_CityManager与BP_StoryManager分别有基于选择表达式/故事关卡变量的加载和卸载。

这证明原游戏有主动加载大城区与玩法关卡的代码。尚未完成每个分支的可达性、异步加载完成次序和实际游戏时刻的观察，因此本报告不把所有调用点解释为“开局全同时可见”。下一步应把这些管理蓝图的控制流、保存状态和区域触发与运行时观察闭合。

三、实际统计

35个包合计：
  Actor实例：{tot['actorInstances']:,}
  Actor所属组件：{tot['actorOwnedComponents']:,}
  已保留原局部/父链变换的场景组件：{tot['sceneComponentTransforms']:,}
  StaticMesh/SplineMesh组件：{tot['staticMeshComponents']:,}（其中SplineMesh {tot['splineMeshComponents']:,}）
  SkeletalMesh组件：{tot['skeletalMeshComponents']:,}
  有明确mesh资源引用的组件：{tot['resolvedMeshComponentReferences']:,}
  跨包去重的直接mesh imports：{report['uniqueAssetsAcrossReferencedWorld']['meshImports']}
  跨包去重的直接material imports：{report['uniqueAssetsAcrossReferencedWorld']['materialImports']}
  内嵌材质实例export：{tot['embeddedMaterialInstances']:,}
  存在OverrideMaterials的组件：{tot['componentsWithMaterialOverrides']:,}，非空覆写槽位{tot['nonNullMaterialOverrideSlots']:,}
  LandscapeComponent：{tot['landscapeComponents']}；Landscape碰撞组件：{tot['landscapeCollisionComponents']}
  灯光组件：{tot['lightComponents']}；PostProcessVolume：{tot['postProcessVolumeActors']}；Fog Actor：{tot['fogActors']}
  InstancedFoliageActor：{tot['foliageActors']}；InstancedStaticMesh类组件：{tot['foliageOrInstancedMeshComponents']}

注意：4个灯光、2个后处理、4个雾包含Lighting和LightingTest两个存储包，不代表同一时刻叠加渲染。StaticMeshComponent数量也包含由模板继承mesh、可能隐藏的辅助组件，不等同于可见物件数。没有RawExport不等于没有未解析内容：NormalExport的Extras仍包含原生二进制负载。

逐关卡简表（完整字段见world-coverage-by-level.csv）：

{chr(10).join(table)}

四、当前Web漏掉的具体内容

1. 整片城区缺失。DownTown的784个明确mesh组件、CommercialArea的533个、FinancialDistrict的307个、IndustrialArea的272个、Park的339个、ResidentialArea2的314个、ResidentialArea3的158个、Beach的122个、Coast的22个、Slam的69个均没有对应Web对象。这里是组件数，不把合并mesh拆成虚构的建筑数量。

2. 主地图道路与交通环境缺失。MainLevel有1,952个SplineMesh组件，目前只恢复211段。现Web另有11个MainLevel静态路口/路沿，对应源MainLevel的2,079个明确mesh组件中的222个。原MainLevel还包含114个BP_LightCrosswalk、113个BP_LightTraffic、6个BP_VehicleWaypoint、车辆管理器/车辆池等场景对象；它们的系统没有随mesh导出自动恢复。

3. ResidentialArea1也只是部分恢复。307个明确mesh组件仅有30个被表示；除此之外还有喷泉、彩蛋、雕像和水面蓝图。当前6种公寓及少量铺装不覆盖住宅区全部街具、植被、墙体、装饰和交互对象。

4. 原地形未恢复。MainLevel有144块LandscapeComponent与144块碰撞组件。组件记录包括ComponentSizeQuads=126、SubsectionSizeQuads=63、NumSubsections=2，以及HeightmapTexture、Weightmap、材质、LOD引用。现Web没有导入这些高度场、分层权重、地形碰撞和地形LOD，替代地面/几何面不能算原地形。

5. 原光照/天空/后处理未恢复。实际AlwaysLoaded的LightingTest有DirectionalLight、SkyLight、BP_Sky、AtmosphericFog、ExponentialHeightFog、PostProcessVolume。已保留原强度、颜色/阴影/雾/后处理属性与变换；当前Web使用的演示照明不等于这些数据。示例：DirectionalLight Intensity=5，SkyLight Intensity=0.75。

6. 材质恢复不足。不仅有1,755组件、4,352个非空OverrideMaterials槽位；地图直接material imports也只是依赖链的一层。现Web的简化PBR并未恢复原材质图、每actor覆写、分层/遮罩、原法线方向、贴花、玻璃反射、皮肤散射、烘焙光照等。完整材质/纹理覆盖必须沿mesh与材质父子依赖继续追踪，不能用“已导出18张颜色图”代替。

7. 植被与实例化不能混算。正式InstancedFoliageActor计数为0，不代表原城没有树。树木可作为合并/普通StaticMesh保存。Park的11个InstancedStaticMeshComponent实际引用Path_A/B/C/D、OrnateWall、Pillar、Stairs等公园道路墙体，不应全称为树木。其Extras中的实例矩阵/渲染负载尚未完整解释，因此实例总数明确标未知，不凭文件长度硬算。

8. 原人车和破坏生态缺失。AlwaysLoaded的CitizenWayPoint有2,806个BP_CharaSpawnPoint、559个BP_CharaChildWaypoint、85个BP_CharacterWayPoint。DynamicProps有430个BP_LightPost和122个BP_BaseBreakProps。现Web的8市民/3车/3报刊箱及新设计巡逻，不能替代这些原出生点、关系图、管理/复用池、可破坏物分布与状态行为。

9. 故事、教程、挑战与首领场景未接入。Story1/2/3、Tutorial、CQ_D/CQ_F难度关卡、首领关卡、LoadLevel和TitleMenuLevel都有已解码Actor和管理引用。它们即便不一定始终可见，也属于原游戏世界和加载生命周期，不能在“完整移植”声明中忽略。

五、变换和来源可以怎样追查

levels/<关卡名>.json逐项保存Actor export index/类、root component、component原RelativeLocation/Rotation/Scale、AttachParent、AttachSocket、绝对变换标记、可见性标记和父链组合结果；mesh、material override、灯光、地形和实例化记录都能回到对应组件与Actor。

原变换单位仍是UE厘米与UE轴，不提前换成Web轴。父链组合未应用未解析的骨骼socket变换、Blueprint/native模板默认覆写或streaming LevelTransform；这些限制逐项注明。170个组件有AttachSocketName，不能忽略挂点后宣称其世界坐标准确。原始JSON仍保留，进一步恢复不必依赖之前筛选过的街区manifest。

六、此次完成和未完成

完成的是“MainLevel实际流送引用及传递引用包的全量静态清单、原变换和Web覆盖差异审计”，不是声称整个游戏的所有代码、原生二进制、渲染和运行时行为已经逆向完毕。本次没有修改原安装、启动游戏或继续修改Web演示。

要让完整原场景恢复可验收，接下来必须完成：动态加载控制流与实际加载状态；全部actor模板继承和实例矩阵；完整mesh→material→texture/shader依赖；原地形/光照/可见性；原人车路径与生成/复用系统；按固定原版视点做逐区域画面对照。应先把这些缺口逐项闭合，再继续增添新玩法。

证据入口
  world-coverage.json：总审计与每关卡计数/覆盖
  world-coverage-by-level.csv：完整逐关卡对比表
  mainlevel-streaming-table.json：UWorld原序列化表与实际流送类
  world-streaming-call-sites.json：23个加载/卸载调用点的精确字节码节点
  world-decode-manifest.json：35份地图的源文件与解码SHA-256
  streaming-manager-decode.json：从当前pak重新提取的三个管理蓝图源身份
  levels/*.json：全部Actor/组件/原变换/资源与环境细目
  decoded-world/*.json：本轮新增地图解码；已存在的MainLevel等原缓存位置见manifest

工具说明
使用已存在的repak及UAssetGUI/UAssetAPI以VER_UE4_27静态解析，本报告不把这些证据冒称REA原生反编译器输出。REA总调查中的工具身份、目标二进制逻辑与运行时证据由主审计合并。
'''
(OUT/'world-coverage.zh-CN.txt').write_text(text,encoding='utf-8')
print('Wrote Chinese report and CSV; levels',len(levels),'characters',len(text))
