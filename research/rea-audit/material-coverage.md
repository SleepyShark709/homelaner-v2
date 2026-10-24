# 原材质与当前 Web 外观差异审计

当前 Web 确实用了部分原网格、骨骼、动画和颜色贴图，但没有复原原游戏画面。差异主要来自**场景只导出一个选区、场景材质覆写没有应用、材质只保留颜色通道、原灯光环境未恢复**。因此不能把当前结果称为完整移植或完整逆向。

本报告基于原 Pak 的只读提取、UAssetAPI 静态解码、UModel 导出文件与当前实现对照，**不属于 REA retained Evidence**。没有运行原游戏做同机位画面对比，也没有把缓存参数解释为已恢复的完整着色器。原安装目录未修改；本次仅写 `research/rea-audit/`。

## 可核实范围

机器可读结果：`material-coverage.json`。其中每条原材质记录包含原 `.uasset/.uexp` SHA-256、解码文件 SHA-256、参数值、原 JSON pointer 与导入依赖。原始解码结果保留在 `decoded-materials/`；不要只依赖摘要。

| 检查项 | 结果 | 边界 |
|---|---:|---|
| 当前已发布 glTF | 31 份 | 包括 original/animated/character 等重复版本，非 31 个独立可见物体 |
| 材质条目 | 290 | 含重复材质，非独立材质总数 |
| 挂颜色贴图的条目 | 160 | 其余主要使用常量颜色 |
| 挂法线/金属粗糙度/AO/自发光贴图 | 各 0 | 现有 glTF 中这些纹理槽全部缺失 |
| 场景选出的静态物体/样条组件 | 41 / 211 | manifest 合并道路后是 42 个对象 |
| 已选物体中存在原材质覆写 | 21 个物体、27 种非空材质 | 覆写被记录，但未应用 |
| 本次原材质/父材质/函数/参数集合记录 | 129 | 全部完成静态解码，不等于全游戏材质集 |
| 这批材质引用的纹理依赖 | 164 | 完整列表见 `textureDependencies`；不等于所有纹理已转成 Web 图像 |
| 抽查纹理元数据 | 19 | 已保留源 hash、属性与 pointer |
| Pak 中游戏地图 | 41 | 含剧情、测试、标题等地图，不能全部同时加载 |
| 本次检查地图 | 4 | MainLevel、ResidentialArea1、ResidentialArea2、DownTown，共找到 330 个网格/材质/纹理资源包依赖 |

复现：先运行 `python research/rea-audit/audit-materials.py`，再运行 `python research/rea-audit/complete-material-audit.py`。两者只生成审计输出，不改发布资源。

## 1. 稀疏道路和空旷城市来自选区导出

`tools/asset-pipeline/export-city.py:15` 定义 UE 坐标矩形 `(-32000,15000,-70000,-42000)`。第 256–260 行仅选择 ResidentialArea1 中指定 Apartment/Ornate/Floor 网格，以及 MainLevel 选区内的 RoadProps 和 SplineMesh。当前导出并没有遍历完整城市。

`research/exports/city-decoded/MainLevel.json` 实际包含 1952 个 `SplineMeshComponent`、144 个 `LandscapeComponent`、1614 个 `StaticMeshComponent`；ResidentialArea1/2、DownTown 分别有 327/347/819 个 StaticMeshComponent。当前仅选中 211 条样条组件，并未恢复原 Landscape。**这些是组件计数，不是画面面积或完整度百分比；也不能把所有样条都断言成可见道路。**

当前路网使用原路面网格和原样条数据烘焙，所以不能说完全没用原道路；但样条、地形、其他城区的覆盖不足足以解释大片空地。`export-city.py:246` 的烘焙输出只保留 `POSITION/NORMAL/TEXCOORD_0`，未保留存在于源网格中的 tangent、其他 UV 或顶点色。后续恢复原着色器时，必须检查其实际需要的顶点属性。

原地图完整包名见 JSON 的 `pakGameMapPaths`。城市部分包括 `/Game/-HeroGame/Maps/SubLevel/{Beach,Coast,CommercialArea,DownTown,FinancialDistrict,IndustrialArea,Park,ResidentialArea1,ResidentialArea2,ResidentialArea3,Slam}`；实际该加载哪些，仍需按 MainLevel 的流送与场景状态确定，不能把测试关卡混入。

## 2. 白建筑：原场景覆写丢失，默认材质也被简化

原场景实例并非只使用网格默认材质。确证例子：

- 文件：`research/exports/city-decoded/ResidentialArea1.json`。
- 对象：`ResidentialArea1/PersistentLevel/SM_MERGED_Apartment_AA_190`，组件导出索引 360。
- 原属性：`/Exports/359/Data/2`，名称 `OverrideMaterials`。
- 槽 0 → `/Game/UrbanCity/Materials/Tileable/brick_01_Inst`；槽 1 → `brick_02_TintA_Inst`；槽 9 → `Tilable_concreteWall03_Inst`；槽 10 → `Window_Inst`；槽 15 → `/Game/-HeroGame/Materials/MaterialInstance/MI_RoofTop`。精确每槽 pointer 在 JSON 的 `mapMaterialOverrides` 中。

`research/evidence/city-layout-material-overrides.json` 已明确写出这些覆写没有应用。`publish_mesh()` 使用网格默认材质，`src/game/World.ts` 复用对应 glTF 材质，没有为实例应用上述覆写。因此原砖墙、窗户、屋顶可能显示为默认墙面等材质。

另一个独立原因是白墙着色器本身被删减。`/Game/ModularStreetPack/Materials/PlasteredWall_MAT` 原缓存 `/Exports/0/Data/5` 引用了 `T_Plastered_Wall_NRM`、`T_Mildew_Map`、`T_Mildew_GradientMap`；其实例 `PlasteredWall_MAT_Inst` 的 Color 确实是白色。当前 glTF 的同名材质只保留白色常量，没有法线与霉斑混合。**白色常量本身不证明漏了颜色贴图：这里确认丢失的是实例覆写、法线/霉斑着色与尚未核实的原光照效果。**

砖墙原实例也不是一张颜色图：`brick_01_Inst` `/Exports/0/Data/3` 指向 `brick_01_d`、`brick_01_n`、`Brick_01_C`、`Brick_01_h`、`Detail_Concrete_N`；`/Exports/0/Data/2` 包含 Detail Normal Scale≈5.81925、Detail Normal Strength≈0.366972、Normal Strength≈0.783849、Roughness≈1.079113、Height≈0.353660。不能把这些标量直接当 glTF 的同名因子：需要恢复其父材质计算。

注意：原 UE 槽号、UModel primitive/material 序号、经过 `compact_mesh()` 合并后的 glTF 材质索引不一定相同。应先保留原 LOD section→material slot 映射，再应用覆写，最后合批；不能直接把 glTF 第 10 个材质替换成原槽 10。

## 3. 道路的粗糙、积水和凹凸通道被移除

`/Game/Downtown/Materials/RoadMain_A_Inst`：

| 原属性 | 源 pointer | 已确认的内容 |
|---|---|---|
| Parent | `/Exports/0/Data/1` | `/Game/Downtown/Materials/-Pavement__Mat` |
| ScalarParameterValues | `/Exports/0/Data/2` | Strength≈2.713732；Wetness Darkness≈0.338532；Wetness Roughness≈0.061864；Wetness Cloud Scale≈1.519576；Wetness Clouds Falloff≈1.040089 |
| TextureParameterValues | `/Exports/0/Data/3` | BaseColor=RoadMain_A；Compact=RoadMain_C；Height=RoadMain_H；Normal=RoadMain_N |

父材质 `/Exports/0/Data/11` 的缓存还引用 `Material_Blend`、Clouds/Grunge/Snow/ShoePrints 等纹理和 `/Game/Downtown/Materials/GlobalParameters/Environmental`。该集合静态默认值为 Rainfall≈0.68427、Snowfall=1、DayNight=0、Grunge=1，**这不是原游戏运行时实际天气的证据**。

现材质只连接 RoadMain_A，统一粗糙度 0.8、金属度 0。原 `RoadMain_C` 与 `Brick_01_C` 元数据明确 `SRGB=false`，原法线明确 `TC_Normalmap`、`SRGB=false`，但 Compact 的 RGB 各存什么尚未恢复。不得看 `_C` 名称就假定它是 glTF ORM，更不能直接当颜色图。

## 4. “玻璃”不能用同一套透明设置修复

| 原材质 | 原文件证据 | 当前损失 |
|---|---|---|
| `/Game/ModularStreetPack/Materials/WindowGlass_Mat` | `/Exports/0/Data/2` 为 `BLEND_Masked`；缓存 Glass_Color≈(0.11,0.11,0.11)，引用 T_VerticalNoise、T_WindowGrime | 城市导出器按名字设蓝灰常量、metallic=.15、roughness=.25，并把除 RoadDecals 外的材质设成 OPAQUE |
| `/Game/UrbanCity/Materials/Tileable/Window_Inst` | 原场景槽覆写引用它；Parent=`-Window_mat`；参数 EmissiveAmount=0、Param≈(.018625,.022553,.025,0)，引用 clouds/mask_grunge_tileable | 原实例覆写未应用，不能用上一种 WindowGlass 材质代替 |
| `/Game/Action_Male/Materials/M_GlassLens_master` | `/Exports/0/Data/3` 明确 `BLEND_Translucent`；Black 实例 Opacity≈.9、Refraction=1、TwoSided=true | 主角墨镜发布材质没有 alphaMode（glTF 默认 OPAQUE），采用统一假定颜色与粗糙度 |
| `/Game/-WorkSpace/Hyodo/VehicleSystem/Vehicle/Sedan/Materials/M_Vehicle_Sedan_Inst_Glass` | roughness≈.1；Base color≈(.05475,.073398,.075,1) | 被统一玻璃颜色与粗糙度替换；没有读到支持其原本半透明的序列化 blend 覆写，不能擅自改成透明 |

## 5. 主角用了原外形，但材质效果没有复原

`M_Body_master` `/Exports/0/Data/3` 是 `MSM_Subsurface`，另有身体普通/平滑法线与颜色混合、SSS、胡须/头皮/ID/Eye/Power mask 等依赖。当前 `MI_Body_asian` 只使用颜色贴图和 `[.743119,.743119,.743119]` 常量；原实例的 Skin hue shift、Skin saturation、Skin oil intensity、Muscle intensity 等计算都未重建。

`MI_Clothes_Contemporary_AllBlack` `/Exports/0/Data/3` 明确六种纹理：`T_Contemporary_{AO,D,ID,M,N_Ydown,R}`；`/Exports/0/Data/2` 的四个 Color Region 为黑色。现仅保留 D 并乘 `.045` 灰色，未按 ID 进行区域染色，也没有金属、粗糙度、AO、法线。父材质还有 Masked、DitherTemporalAA、MF_GetDitherDistance 等逻辑；glTF 普通材质不能自动表达这些逻辑。

`MI_Hair_Black` 参数包含 Hair Desaturation=1、Hair Value=0、Opacity=1，以及 Hair AO/base/normal/transp。当前连接 T_Hair1_color 并乘 .025。这里有必须继续核实的问题：该实例的 TextureParameterValues 指向 Hair1，CachedReferencedTextures 却列出 Hair_001 系列；父材质缓存也列出 Hair_001。仅凭前者不能证明最终编译后绑定，不能把目前的头发贴图宣称为已完全匹配。报告保留了两组证据，没有强行选一组当事实。

抽查 `T_Contemporary_N_Ydown` 的 `/Exports/0/Data/3,5` 确认 normalmap 压缩与非 sRGB；接入时还需处理 UE 与目标渲染器的法线切线/Y 约定，不能仅把文件改名。

## 6. 车辆的问题主要是参数被替换，不能宣称“原车没有材质”

UModel 日志的 `Ignoring ... due to empty parameters` 只说明该工具没有输出可用参数。UAssetAPI 解码 `/Game/-WorkSpace/Hyodo/VehicleSystem/Vehicle/Sedan/Materials/M_Vehicle_Sedan` 的 `/Exports/0/Data/5` 实际读到：Roughness=.5、Metallic=0、Base color≈(0,.68,.94,1)。当前 `publish_original.py:88` 使用(.11,.27,.36,1)、metallic=.45、roughness=.32，是人工指定值。玻璃、轮胎、轮毂、车灯等子材质的原参数也已保留在 JSON。

此 Sedan 材质家族的导入依赖没有 Texture2D，现无贴图并不能证明漏导了车身纹理。应优先恢复真实参数和原车辆蓝图装配，再检查反射与灯光。不要用“补贴图”掩盖选错车辆资源或忽略蓝图覆盖的可能性；完整车辆蓝图与运行时随机配色不在本审计确证范围内。

## 7. 下一步完整导出与重建的依赖顺序

1. **确认活动世界闭包。** 从 MainLevel 实际流送/剧情状态确定子关卡，提取全部静态与实例网格、Landscape 高度/权重、样条、Foliage、Decal、可破坏物体和车辆蓝图装配。JSON 的 41 地图清单只是 Pak 清单，330 个地图资源包只是四张地图的已查依赖，不是已闭合的完整城市清单。
2. **保留原 section/slot 身份。** 还原组件 OverrideMaterials、蓝图动态材质与参数更新；解析父链、启用的 BasePropertyOverrides、静态开关、运行时参数。应用正确实例材质之后再合批。
3. **按依赖导出完整纹理。** 先覆盖本次 164 个引用，再扩展其余关卡；记录像素/mip、SRGB、压缩、采样器、UV 与色彩空间。先确认 Compact 通道打包，再转换 glTF 金属/粗糙/AO。源纹理数据和材质名字并不等于着色器恢复。
4. **重建有证据的材质家族。** 身体 SSS 与 mask、服装 ID 染色、建筑砖/霉斑/细节法线、路面混合与天气、头发遮罩、各类玻璃分别处理。复杂 UE 材质需要目标引擎着色器或经过验证的烘焙；本次缓存数据尚不足以还原所有数学表达式。源 Extras 中仍有未解释的编译数据，不把它称为已反编译 HLSL。
5. **恢复环境与对照验证。** 当前 `src/game/Game.ts:48-59` 的雾密度 .0018、半球光 1.1、方向光 2.3 等来自 Web 实现选择；原 Lighting、天空、后处理、反射探针和烘焙数据尚未接入。本审计没有原环境数值。需要同地点、同朝向、同时间/天气的原游戏与 Web 对照，才能判断具体误差；若启用 REA 原生工作流，保留独立 session/evidence 引用，不能给本审计工具结果补贴 REA 标签。

以上均是后续工作依赖，本次没有修改场景或材质来制造“已恢复”的结果。完整着色器、完整活动地图、动态参数与原运行时视觉验证仍未完成。
