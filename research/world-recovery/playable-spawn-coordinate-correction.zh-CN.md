# 可玩切片坐标修正：旧原型 originUE → 恢复世界

日期：2026-10-25。范围：B1/B2/B3 的出生点和预览人口，不是原游戏运行观察。

## 问题

旧原型 `public/assets/city/manifest.json` 与 `public/assets/population-manifest.json` 记录：

```json
"originUE": [-10000, -55000, 0]
```

这表示它们是**街区局部坐标**：恢复世界的 UE 原点与旧原型不同。B1 最初直接把旧 spawn `(50, 1.37)` 当作恢复世界坐标，结果落在 MainLevel 的一条空路上；预览市民/车辆也落在同一错误区域。

## 修正

UE 厘米到恢复世界的平面偏移是 `originUE[0]/100, originUE[1]/100 = (-100, -550)` 米：

- 旧 spawn `(50, 1.37)` → 恢复世界 `(-50.0, -548.63)`；
- `ResidentialArea1` 的几何 bounds 为 x `-286.7…126.0`、z `-664.7…-445.3`，修正后的点确实落在该街区内；
- 14 个预览 actor 的 spawn 和短 route 点同样平移 `(-100, -550)`；旧 `?view=prototype` 不传偏移，保持原行为。

代码位置：`src/play-original.ts` 读取 originUE 并计算偏移；`Population.load({worldOffset})` 只在该调用中平移 spawn/routes。

## 结果

修正后 `?view=play` 在 ResidentialArea1 的砖砌公寓、街道、行道树与围栏之间装配角色和预览人口；截图 `research/screenshots/play-b3.jpg`。重新跑 B1/B2 浏览器探针，移动、跳跃/飞行、E/Q、强力远程车辆命中仍然通过。

## 边界

- 这是**旧原型坐标的修正**，不是找到原版 `PlayerStart`；`BP_RespawnAndSpawnPoint` 的 y=170.9 仍是高位点，原版真实出生点未证明。
- 预览市民的 placement/routes 仍是旧原型的 Web 设计数据，只是现在对齐到了正确街区；原版 AI/交通/任务仍未恢复。
- 没有修改原安装或原存档。

证据：`public/assets/city/manifest.json`、`public/assets/population-manifest.json`、`src/play-original.ts`、`src/game/Population.ts`、`research/world-recovery/playable-b1-validation.json`、`playable-b2-validation.json`、`research/screenshots/play-b3.jpg`。
