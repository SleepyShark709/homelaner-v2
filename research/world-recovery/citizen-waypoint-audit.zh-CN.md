# 原版市民 Waypoint 数据审计（未接入）

日期：2026-10-25。来源：`research/rea-audit/decoded-world/CitizenWayPoint.json`，UAssetAPI 解码的 cooked 地图，SHA-256 `F984545FB9127B94C8561202234748886568170AE64FF7BC631D14FE4D02F88F`，53,448,769 字节。不是 REA 原生反编译，也不是运行观察。

## 已确认的数据量

- 9,711 个 exports，34 个 imports。
- `BP_CharacterWayPoint`（含编号/派生名）85 个：spline 路径所有者，每个带 `ChildWaypointArray`、`CitizenSpawnerArray`。
- `BP_CharaSpawnPoint` 2,806 个：候选市民出生点；root `Box` 的 `RelativeLocation` 以 UE 厘米给出。
- `BP_CharaChildWaypoint` 559 个：spline 子路点；Billboard root 带相对位置。

`BP_CharaSpawnPoint` 的 root Box 位置按 `X/100, Y/100` 转换为 Web 世界米后，与 B1 出生点 `(50, 1.37)` 对齐良好：

- 100 m 内 897 个，30 m 内 174 个；
- 最近样本：`BP_CharaSpawnPoint_C_8928` `(50.18, 1.99)`、`BP_CharaSpawnPoint_C_9483` `(49.31, 1.98)`、`BP_CharaSpawnPoint_C_9288` `(51.45, 1.97)`；
- 样本 `Box` 的 Z 为 0，实际落地高度仍需用 Landscape 高度场/原 ground offset 修正。

这说明原版市民出生点网络在 Player 所在街区确实存在，且不是旧原型凭空布置的。

## 尚未闭合的坐标/父链问题

- 每个 spawn 的 `ParentWaypoint` 指向一个 actor/component 索引；但 `Spline` 组件的 `OuterIndex` 与引用它的 `BP_CharacterWayPoint` 索引并不总是一致，UAssetAPI 解码中存在 component/actor 索引偏移或 Outer 链语义未核清。
- 例如 `BP_CharacterWayPoint45` 的 `Spline` 指向 9658，而 9658 的 `OuterIndex` 是 6765（`BP_CharacterWayPoint47`）；直接按“父 actor 位置 + spline 局部点”会得到与 spawn 不一致的远端坐标。
- `Spline` 的 `RelativeLocation` 与局部点相加后也出现远端位置；因此在核对 actor/component outer 链和原点/世界偏移之前，不能把 spline 点发布为可运行路径。
- 2,806 个 spawn 不是同时存在的市民；原版 spawner 的生成节奏、数量、导航寻路和状态机尚未解释。

## 决定

本轮**不**把 waypoint/spawn 数据写入 `population-manifest.json`，也不把 preview 市民替换成这些位置；避免用未核清的坐标冒充原版路径。B3 下一步先解决：

1. UAssetAPI 导出中 actor/component Outer 链、`Spline` 与 `BP_CharacterWayPoint` 的准确对应；
2. spawn Box 的 world transform（父组件/Level transform）；
3. spline 点局部→世界转换与 Landscape 高度；
4. 只对玩家附近、父链可闭合的少量 spawn 做可视化/路径测试，再决定是否接入 Population。

现有 B2 仍使用旧原型 `population-manifest.json` 的预览位置/路线，已明确标注不是原版 AI。

证据：`research/rea-audit/decoded-world/CitizenWayPoint.json`；计数与最近点由 `research/rea-audit` 解码数据直接扫描得到，未写入原安装。
