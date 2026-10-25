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

76 张已全部导出为 1024×1024 PNG，清单在 `research/world-recovery/lightmap-export-inventory.json`。

试过用建筑 TEXCOORD_2/TEXCOORD_3 的 UV 掩码与 lightmap 非黑内容做 precision/coverage 打分，但所有候选结果几乎相同：这些 atlas 是全图内容，不是简单的“空白背景+UV 岛”布局，无法靠覆盖率唯一识别。还需要正确的 HDR/Lightmass 解码和组件 LightMapIndex 映射。

进一步改用 UV 岛内/外的梯度细节比排序，最高 HQ 候选是：

```text
HQ_Lightmap0_138
UV = TEXCOORD_2
flipV = true
gradient ratio ≈ 1.72
```

排名与限制记录在 `research/world-recovery/lightmap-candidate-analysis.json`。给建筑 PBR 材质挂 `HQ_Lightmap0_138` + TEXCOORD_2 的试验没有产生可验证的视觉变化，已回退；因此这只是候选排序，不是已应用的 lightmap。

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

进一步用外部 `ReadProcessMemory` 读取 `LODData:GetArrayDataAddress()` 的前 4096 字节，与 3436 个已加载 `LightMapTexture2D` 地址扫描比较：**0 命中**。该内存内容主要是浮点/网格数据，不是平铺的 lightmap 指针数组。因此不能把 `LODData` 当 lightmap 容器直接解；需要 SDK/`FLightMap2D` 内部布局或另一个组件字段。

## UV 通道

起始建筑 glTF 有 4 个 UV 通道：

```text
TEXCOORD_0  tiled，不是 lightmap UV
TEXCOORD_1  常量 (0,1)，不可用
TEXCOORD_2  packed，全部在 [0,1] 内   -> lightmap UV 候选
TEXCOORD_3  packed，全部在 [0,1] 内   -> lightmap UV 候选
```

所以 mesh 端至少已经有可用的 lightmap UV 候选；仍未确认原版 `LightMapCoordinateIndex` 指向 2 还是 3。

## Window 玻璃云层

`-Window_mat` 的解码 imports 明确包含：

```text
/Game/UrbanCity/Textures/Tileable/clouds
/Game/UrbanCity/Textures/Tileable/mask_grunge_tileable
Clouds Mask Tiling 0.2
Contrast 0.0159
Greunge Amount 4.94
EmissiveAmount 0.15
```

Web 现在使用原版 `clouds.png` 作为玻璃 emissive 层，`uScale=vScale=0.2`，emissive 颜色 `(0.08, 0.11, 0.17)`。

同机位 luma：原版 55.8/31.3，加入云层后 Web 57.8/31.0。玻璃已不再是纯黑，但 `mask_grunge_tileable`、Contrast/Greunge 数学仍未复刻，不能称为完整 shader 还原。

## 已排除的捷径

- **静态建筑加入实时 ShadowGenerator**：把 `SM_MERGED_Building_2_01_*` 加进方向光阴影 caster 后，同机位 mean/std 仍为 57.8/31.0，雨棚上沿没有变暗；原版这里是烘焙光/lightmap，不是简单动态阴影。
- **`mask_grunge_tileable` 作为 PBR detailMap**：会导致场景材质加载超时/暗屏，已回退。
- **直接把候选 lightmap 挂到 PBRMaterial.lightmapTexture**：无可验证变化，已回退。
- **LODData 直接扫描 lightmap 纹理指针**：0 命中。

这些路径都不能替代真正的组件 LightMapIndex/`FLightMap2D` 绑定。

## 下一步

1. 用 UE4SS C++ mod/SDK 读取 `FLODData::LightMap` 的内部 LightMapIndex/LightMapCoordinateIndex/UVBias。
2. 匹配到 `HQ_Lightmap0_*` 具体对象。
3. 确认 lightmap UV 是 TEXCOORD_2 还是 TEXCOORD_3，并确认 UV scale/bias。
4. 在 Web 材质中采样原版 lightmap。

## 相关证据

- `research/world-recovery/lightmap-inventory.json`
- `research/runtime-observation/original-live-audit.zh-CN.md`（LightingTest/PostProcessVolume 参数）
- `research/runtime-observation/comparison-live-gameplay-start-final.jpg`
