# MainLevel 光照/烘焙贴图恢复记录

日期：2026-10-25。目标是把 Gate 3 从“用预览 SSAO 调亮”推进到使用原版数据。

## 已确认

`MainLevel_BuiltData` 的 cooked 包内包含：

```text
LightMapTexture2D   464 个（HQ_Lightmap0_* / LQ_Lightmap_1_*）
ShadowMapTexture2D  198 个
```

清单：`research/world-recovery/lightmap-inventory.json`。

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

新增 UE4SS probe：`tools/runtime/ue4ss/LightmapProbe`。菜单/标题场景中 `FindAllOf("StaticMeshComponent")` 未找到该 building（`components=0`），需要在真正加载 CommercialArea 的 gameplay 状态下再跑一次，读取组件上的 LightMap 指针/索引。

## 下一步

1. 在 gameplay 状态运行 `LightmapProbe`，拿到起始建筑组件的 LightMap 指针/索引。
2. 匹配到 `HQ_Lightmap0_*` 具体对象。
3. 导出 mesh lightmap UV1 并确认 UV scale/bias。
4. 在 Web 材质中采样原版 lightmap。

## 相关证据

- `research/world-recovery/lightmap-inventory.json`
- `research/runtime-observation/original-live-audit.zh-CN.md`（LightingTest/PostProcessVolume 参数）
- `research/runtime-observation/comparison-live-gameplay-start-final.jpg`
