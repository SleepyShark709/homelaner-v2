# MainLevel 光照/烘焙贴图恢复记录

日期：2026-10-25。目标是把 Gate 3 从“用预览 SSAO 调亮”推进到使用原版数据。

## 已确认

`MainLevel_BuiltData` 的 cooked 包内包含：

```text
LightMapTexture2D   464 个（HQ_Lightmap0_* / LQ_Lightmap_1_*）
ShadowMapTexture2D  198 个
```

清单：`research/world-recovery/lightmap-inventory.json`。

关键发现：起始建筑在 `CommercialArea` 子关卡，而它自己的 `CommercialArea_BuiltData` 还有：

```text
LightMapTexture2D   76 个
ShadowMapTexture2D  25 个
```

因此起始建筑的候选 lightmap 集合应先从这 76 个里找，而不是 MainLevel 的 464 个。

单个 `HQ_Lightmap0_16` 已用 UModel 成功导出为 4096×4096 PNG，证明这些不是残留引用，而是真实烘焙数据。

导出命令（从 `-HeroGame/Maps` 目录执行）：

```powershell
umodel -export -png -game=ue4.27 -path=. -out=<dir> `
  MainLevel_BuiltData HQ_Lightmap0_16 LightMapTexture2D
```

注意：UModel 的动画导出没有 `-psa` 参数；这里是 LightMapTexture2D 对象导出。

## 当前未完成

- 没有从 MainLevel 的 StaticMeshComponent 提取每个建筑的 **LightMapIndex / LightMapCoordinateIndex / UV scale-bias**；
- 当前 glTF 几何没有可用的 **lightmap UV1** 绑定；
- 不知道起始建筑使用哪一个 `HQ_Lightmap0_*`；
- 原版 Mobile/Preview 采样、Lightmass 编码（HDR RGBE/BC6H）和 UE 的 Lightmap 解码仍未复刻。

## CommercialArea 起始建筑

在 `CommercialArea.umap` 中：

```text
actor SM_MERGED_Building_2_01_9
StaticMeshComponent export index 703
StaticMesh import -184
OverrideMaterials [-47, -39, -45]
```

UAssetGUI 序列化出的组件属性里**没有** `LightMap` / `LightMapCoordinateIndex` / `LightMapUVBias`；这些字段在 cooked 包或运行时 component 上，不能从现有 JSON 直接拿。

新增 UE4SS probe：`tools/runtime/ue4ss/LightmapProbe`。菜单/标题场景中 `FindAllOf("StaticMeshComponent")` 未找到该 building（`components=0`）。在 `GameStartEvent()` + 一次 `InputDone()` 后的 gameplay 状态，probe 已找到：

```text
CommercialArea...SM_MERGED_Building_2_01_9.StaticMeshComponent0
LightMap                UObject pointer
LightMapCoordinateIndex UObject pointer
LightMapUVBias          UObject pointer
LightMapResourceCluster UObject pointer
LightmapType            0
```

说明运行时确实有 lightmap 绑定；但当前 UE4SS Lua 对这些属性返回的是包装指针，`:Get()`/`:GetFullName()` 不能直接解出索引。继续检查发现：

```text
LODData: TArray，长度 1
LODData[0].LightMap / ShadowMap / LightMapUVBias / LightMapCoordinateIndex
  -> Lua 看到的是 UScriptStruct 类型对象，不是可读数值
```

原因是 `FLODData` / `FLightMapRef` 内部的 lightmap 引用不是反射 UPROPERTY，Lua 反射层拿不到内部字段。进一步尝试：

```text
LODData[0] / LODData[1] 返回 UScriptStruct
GetStructAddress() 返回数值地址
但 .LightMap/.ShadowMap/.LightMapIndex/.LightMapUVBias 全部为 nil
```

即 Lua 拿到的只是 struct 类型/地址，不是可字段读取的实例；下一步必须用原生 C++/UE4SS SDK 或内存偏移读取。

另外比较了 `comp.LightMap` 的 UObject 地址与当前加载的 510/900 个 `LightMapTexture2D` 对象地址，**没有匹配**。说明 `comp.LightMap` 指向的是 `FLightMap`/`FLightMapRef` 包装对象，不是可直接命名/采样的 `LightMapTexture2D`；真正的纹理在 `FLightMap2D::Textures[]` 内部，仍需原生读取。

## UV 通道

起始建筑 glTF 有 4 个 UV 通道：

```text
TEXCOORD_0  tiled，不是 lightmap UV
TEXCOORD_1  常量 (0,1)，不可用
TEXCOORD_2  packed，全部在 [0,1] 内   -> lightmap UV 候选
TEXCOORD_3  packed，全部在 [0,1] 内   -> lightmap UV 候选
```

所以 mesh 端至少已经有可用的 lightmap UV 候选；仍未确认原版 `LightMapCoordinateIndex` 指向 2 还是 3。

## 下一步

1. 用 UE4SS C++ mod/SDK 读取 `FLODData::LightMap` 的内部 LightMapIndex/LightMapCoordinateIndex/UVBias。
2. 匹配到 `HQ_Lightmap0_*` 具体对象。
3. 确认 lightmap UV 是 TEXCOORD_2 还是 TEXCOORD_3，并确认 UV scale/bias。
4. 在 Web 材质中采样原版 lightmap。

## 相关证据

- `research/world-recovery/lightmap-inventory.json`
- `research/runtime-observation/original-live-audit.zh-CN.md`（LightingTest/PostProcessVolume 参数）
- `research/runtime-observation/comparison-live-gameplay-start-final.jpg`
