# 原版市民 Waypoint 数据审计（未接入）

日期：2026-10-25。来源：`research/rea-audit/decoded-world/CitizenWayPoint.json`，UAssetAPI 解码的 cooked 地图，SHA-256 `F984545FB9127B94C8561202234748886568170AE64FF7BC631D14FE4D02F88F`，53,448,769 字节。不是 REA 原生反编译，也不是运行观察。

## 已确认的数据量

- 9,711 个 exports，34 个 imports。
- `BP_CharacterWayPoint`（含编号/派生名）85 个：spline 路径所有者，每个带 `ChildWaypointArray`、`CitizenSpawnerArray`。
- `BP_CharaSpawnPoint` 2,806 个：候选市民出生点；root `Box` 的 `RelativeLocation` 以 UE 厘米给出。
- `BP_CharaChildWaypoint` 559 个：spline 子路点；Billboard root 带相对位置。

`BP_CharaSpawnPoint` 的 root Box 位置按 `X/100, Y/100` 得到**旧原型街区局部帧**，与旧 spawn `(50, 1.37)` 对齐；恢复世界需加 `originUE/100 = (-100, -550)` 米，即修正后的 B1 spawn `(-50.0, -548.63)` 附近：

- 100 m 内 897 个，30 m 内 174 个（局部帧距离）；
- 最近样本：`BP_CharaSpawnPoint_C_8928` `(50.18, 1.99)`、`BP_CharaSpawnPoint_C_9483` `(49.31, 1.98)`、`BP_CharaSpawnPoint_C_9288` `(51.45, 1.97)`；
- 样本 `Box` 的 Z 为 0，实际落地高度仍需用 Landscape 高度场/原 ground offset 修正。

这说明原版市民出生点网络在 Player 所在街区确实存在，且不是旧原型凭空布置的；它和旧 city/population 清单一样是局部坐标。

## 组件 OuterIndex 观察

- 85 个 `BP_CharacterWayPoint` 的 `Spline` 组件 `OuterIndex` 一致表现为 `actor 索引 + 2`（例如 6730→6732、6731→6733）。spawn/child 的 root component 也出现同类偏移。
- 这更像 UAssetAPI 导出数组与原 package export index 的映射差异（两个导出未列入/索引偏移），不能把 JSON 数组下标当作直接 owner 索引。
- Child waypoint 的 Billboard `RelativeLocation` 是同一局部帧的小坐标（如 `(200,200)`、`(200,13967)`）；把它与 spline 组件的 `RelativeLocation=(-14514,-51279)` 相加会得到远端位置，因此当前不能直接发布为路径。
- 2,806 个 spawn 不是同时存在的市民；原版 spawner 的生成节奏、数量、导航寻路和状态机尚未解释。

## 决定与可选检查

默认**不**把 waypoint/spawn 数据替换进 `population-manifest.json`，因为：

- spawn Box 的 world transform/父组件链尚未闭合；
- 2,806 个 spawn 不是同时存在的市民；
- 12 个最近 spawn 点会挤在玩家附近（见 `play-original-citizens.jpg`），不能当默认人口。

新增一个**可选**检查模式 `?view=play&population=original`：

- `tools/asset-pipeline/export-citizen-spawns.mjs` 从解码数据取玩家附近 12 个 `BP_CharaSpawnPoint`；
- 按 `originUE/100=(-100,-550)` 转成恢复世界坐标，写 `public/assets/world/population-original-citizens.json`；
- 市民巡逻路线使用最近的原版 `BP_CharaChildWaypoint` 位置（同父优先），共 558 个 child 候选中选点；路线顺序、遍历和 citizen AI 仍是预览；
- 结果用于位置/密度/路径检查，不是默认游戏人口。

B3 下一步仍需解决：

1. UAssetAPI 导出中 actor/component Outer 链、`Spline` 与 `BP_CharacterWayPoint` 的准确对应；
2. spawn Box 的 world transform（父组件/Level transform）；
3. spline 点局部→世界转换与 Landscape 高度；
4. 原版 spawner 的生成节奏/数量/寻路状态机。

现有默认仍使用旧原型 `population-manifest.json` 的预览位置/路线，已明确标注不是原版 AI。

证据：`research/rea-audit/decoded-world/CitizenWayPoint.json`；`tools/asset-pipeline/export-citizen-spawns.mjs`；`research/world-recovery/citizen-spawns-selection.json`；`research/screenshots/play-original-citizens.jpg`。
