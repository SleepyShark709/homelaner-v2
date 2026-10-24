# 原版住宅街区恢复

已从本机发行包恢复 `MainLevel` 与其 `ResidentialArea1` 子关卡的一片真实街区。入口是 `public/assets/city/manifest.json`。建筑、地台、道路都来自原资产和原组件数据，没有按想象排列方块城市，也没有启动或修改原游戏。

当前包含 19 栋公寓（A–F 六种原建筑）、11 处原地台/铺装、11 个路口/人行道静态对象，以及 211 个原道路/人行道样条组件。样条烘焙为一个可加载道路对象，因此 manifest 共 42 个对象、17 个需要加载的资产。原始公寓和道路资产仍分别保留，建筑可以单独隐藏或进入破坏流程。

## 来源与转换

`MainLevel.umap` 中存在指向 `ResidentialArea1.ResidentialArea1` 的 `LevelStreamingKismet_38`，不是仅根据文件名选择的展示地图。两份 map 由项目内 repak 提取、UAssetGUI/UAssetAPI 的 `VER_UE4_27` 解析。组件的 `StaticMesh`、`RelativeLocation`、`RelativeRotation`、`RelativeScale3D` 和 `AttachParent` 均有来源记录。

`ResidentialArea1` 解出 327 个 StaticMeshComponent。本轮只发布公寓、原地台与邻近道路，其他组件没有假装已经恢复。MainLevel 道路位于 Landscape 的样条组件中：父级含 `(-70600,-80600,0)` 厘米偏移、100 倍地形缩放与 0.01 倍样条缩放。脚本递归组合父链，不能将道路的相对坐标直接当世界坐标。

源文件、工具及 Oodle DLL 的 SHA-256 见 `research/evidence/city-layout-validation.json`。静态解码是第三方 UAssetAPI 的证据，不冒充 REA 原生反编译结果或原游戏运行观察。

## 坐标协议

场景使用 Babylon `scene.useRightHandedSystem = true`，manifest 的 `coordinateSystem` 固定为 `gltf-rh-y-up-meters`。

- `originUE = [-10000,-55000,0]`，单位厘米，仅用于让浏览器数值靠近零点。
- 原地图位置转为 `[(x-originX), (z-originZ), (y-originY)] / 100`。
- 原 UE 四元数换基为 `[-qx,-qz,-qy,qw]`；缩放为 `[sx,sz,sy]`。
- `rotation` 始终是 `[x,y,z,w]` 四元数，不能当欧拉角。

位置换基依据 [Gildor UEViewer ExportGLTF.cpp](https://github.com/gildor2/UEViewer/blob/a0bfb468d42be831b126632fd8a0ae6b3614f981/Exporters/ExportGLTF.cpp) 的 `TransformPosition`：交换 Y/Z 并乘 0.01。地图没有经过 ActorX 的 Y 镜像，不能直接套用 PSA 动画的 `(x,z,-y)` 公式。世界旋转通过同一反射基 `C R C^-1` 变换；已检查 UE yaw=90° 的局部 X 在 glTF 中指向 +Z。

manifest 的 `assets` 含 `id/url/kind`，`objects` 含 `id/assetId/position/rotation/scale/sourceActor`。静态对象附有源组件名和 export index；合并道路保留全部 `sourceComponents`，每一段的原属性见证据文件。

## 道路、出生与碰撞

211 个道路组件使用原 `StartPos/EndPos/StartTangent/EndTangent` 做三次 Hermite 插值，并按存储的横截面 scale、roll、offset 变形原网格；保留原 UV。再应用组件世界变换并换坐标。当前样本都使用默认 X 前向轴、Z up；出现显式其他轴或 spline boundary 时脚本会拒绝，防止静默错误。

道路合并后为 29,424 三角、4 个材质组。原 `RoadDecals_Inst` 明确是 `BLEND_Masked`，转换使用 glTF `MASK` 与 0.3333 cutoff。此烘焙不是运行 UE spline shader；没有恢复样条运行时编辑、完整 UE shader、地形高度场或原碰撞烹制数据。

出生点是距离选定原点最近的原 Road 样条中点上方 1.2 米，约 `[50,1.7112,1.3708]`，**不是原 PlayerStart**。其原道路表面高度为 `groundY ≈ 0.5112m`。`spawnEvidence` 指明来源组件。

11 个原地台的世界 AABB 放在 `collisionBoxes`，带 `sourceActor`。底层 floor 顶面约 0.65 米，部分原庭院铺装顶面为 2.65 米。它们应作为表面/台阶使用，不能把所有道路和地台的整体包围盒当作高墙。建筑的碰撞代理仍需由浏览器加载实际 mesh 后计算；这些 AABB 不是原 UE 精确碰撞。

`bounds` 的 X/Z 为已发布静态网格与道路几何的并集，约 X `[-227,270]`、Z `[-146,149]` 米；Y 上限 140 米是此原型的飞行活动空间。`restoredStaticBounds` 另外记录静态几何真实高度范围。

## 材质与性能边界

已关联原 PNG 颜色贴图。为适应当前 Babylon loader，图片采用各 mesh 目录内的 `textures/name.png`，不用 `../`、站点根 URI 或固定 localhost 地址；道路使用 city 根目录的同名 textures 子目录。磁盘存在少量重复纹理，之后可在打包阶段优化。

当前材质是简化 PBR；原光照、反射、自定义 shader、法线方向处理及分层混合尚未完整恢复。另有 21 个 actor 的 `OverrideMaterials` 尚未应用，包括部分砖墙、屋顶及地台。因此几何和布局来自原场景，配色不能称为完整原样还原。全部覆写引用已保留在 `city-layout-material-overrides.json`，下一轮可以按 actor 生成材质变体。

场景总计 604,147 三角。仅合并每个 mesh 内完全相同材质的 primitive，不跨建筑合并；理论材质段数由 1,960 降至 481。21 种源静态 mesh 的逐三角 POSITION+UV 哈希在合并前后全部一致。道路另按原 spline 数据变形，不纳入这个“形状不变”检查。实际帧率、遮挡剔除、LOD、移动端性能仍需浏览器测试。

## 重新生成与证据

```powershell
python tools/asset-pipeline/export-city.py
```

脚本使用标准库。需要项目内 `bin/repak.exe`、`bin/oo2core_9_win64.dll`、`umodel.exe` 和 `uasset-net472/UAssetGUI.exe`，以及本机只读游戏 pak。缺少已解码 map 时会提取并解码 MainLevel、ResidentialArea1；mesh 依赖按 UModel 报出的包引用逐层补齐。不需要 Unreal Editor、GUI 导出或系统软件安装。

主要证据：

- `research/evidence/city-layout-source.json`：每个静态对象、道路段的原包引用、父链结果和属性。
- `research/evidence/city-layout-spline-bake.json`：合并道路的源组件列表、几何统计及样条中点。
- `research/evidence/city-layout-validation.json`：输入哈希、所有发布资源引用检查及最近一次逐三角验证。
- `research/evidence/city-layout-material-overrides.json`：尚未应用的逐 actor 材质覆写。
- `research/evidence/city-layout-export-*.log`：原资源解码/导出日志。

此阶段不包含完整地图、所有街具/植被、原 AI 路径、物理破坏、蓝图逻辑、天气、照明和任务系统。

## 人车路径准备数据

`python tools/asset-pipeline/export-routes.py` 生成独立的 `public/assets/city/routes.json`，不会修改 manifest 或网格。数组中每条都有 `id/kind/points/sourceComponent/closed`，当前为三条 road、三条 sidewalk，各 17 个点、`closed:false`。

每条仅使用一个原道路组件的 Hermite 参数，采样原参数的 0.025–0.975 区间；不连接不同组件、不虚构路口连线，也不称其为原 AI 行走路线。Sidewalk 采用原网格横截面宽度中点，并在每个纵向采样位置对原三角面求最高表面高度，再应用原样条与组件父链变换；没有人为增加脚底抬升。偏移、源表面高度和长度在 `city-layout-routes.json` 中记录。

筛选使用实际街区 bounds 与建筑世界包围盒外扩 0.5 米，逐段加密检测。三条 road 距 spawn 约 0–11 米；三条通过保守包围盒检测的 sidewalk 最近约 122 米。更近的人行道中心被当前合并楼体包围盒覆盖，可能涉及挑檐等非实体占地；此阶段宁可排除，后续细化建筑碰撞后才能扩展近处行人区域。
