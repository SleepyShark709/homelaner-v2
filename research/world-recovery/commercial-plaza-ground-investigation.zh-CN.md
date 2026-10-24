# CommercialArea 候选广场地面调查（未闭合）

日期：2026-10-25。范围：起点广场候选点 `CommercialArea (91,181)` 的草地/砖石地面差异。不是运行时观察，也不是同机位结论。

## 已知

- `SM_Floor12000x15000` 三块楼板在 CommercialArea：
  - x `-286..-68`、`-32..125`、`161..325`；
  - z `70..234`，顶面约 0.65 m；
  - 材质记录为 `MI_GroundBrick`/`MI_FloorBrick1`。
- geometry manifest 的 object 与 thin-instance matrix 平移一致（例：677 在 `(-32,0.65,234)`）。
- 可走面 AABB 正确包含 `(91,181)`，玩家被支撑在约 0.67 m。
- 全屏截图仍是草地；原程序起点广场是砖石铺装。

## 已尝试

- 把 floor mesh `position.y` 抬高，并 `unfreezeWorldMatrix`/`computeWorldMatrix`：地面不变（thin instance matrix 不受 mesh position 影响）。
- 直接修改 thin-instance `matrixData` 的 Y 平移 +0.2：场景地面仍不变。
- `backFaceCulling=false`、`zOffset=-8`：前景地面仍不变。
- 把 floor mesh 材质 emissive/albedo 临时设红：红色楼板只出现在远处边缘，玩家脚下仍是草地。

`?debug=floors` 可直接复现红色楼板标记。

## 追加实验（2026-10-25）

- `?debug=floors` 把 `SM_Floor12000x15000` 楼板染红：红色楼板只出现在远处边缘，玩家脚下仍是草地。
- 把材质名包含 `FloorBrick` 的 **29 个 mesh** 全部染红：前景仍不变，红色只在远处边缘。
- 修改 floor thin-instance `matrixData` 的 Y 平移 +0.2、`zOffset=-8`、`backFaceCulling=false`、`disableDepthWrite=true/depthFunction=519/renderingGroupId=1`：前景均不变。
- 直接读取 `landscape-5269` 高度场在 `(91,181)` 的 u16：`32768`，按 manifest 计算高度 **0 m**；楼板顶面 **0.65 m**，玩家约 0.67 m。
- 因此当前可见草地既不是高度场数值，也不是这些 floor mesh 的可见顶面；需要继续定位实际 foreground mesh/材质。

结论不变：候选点仍未证明，不能把红色楼板或草地当作原版起点广场。

证据截图：`play-plaza-redfloor2.jpg`、`play-plaza-all-red.jpg`、`play-plaza-nodepth.jpg`、`play-plaza-instances-raised2.jpg`。

## Raycast 结果（2026-10-25）

> 修正：本次 `createPickingRay(..., null, camera)` 的命中点不可靠，后续用具体 mesh bounds 否定了“地形低 30 m”的解释；见下文“Ray 结果修正”。

开启 `@babylonjs/core/Culling/ray` 后，用 `scene.createPickingRay`/`pickWithRay` 对画面地面点取射线：

- 屏幕 `(640,620)` 命中 `landscape-5189`，世界点 y ≈ **-41.9 m**；
- 屏幕 `(800,600)` 命中 `landscape-5189`，y ≈ **-32.2 m**；
- 屏幕 `(640,500)` 命中 `landscape-5187`，y ≈ **-26.4 m**。

也就是说，画面里看到的“草地”是 **静态 CommercialArea 下方约 26–42 m 的 Landscape**；玩家/楼板在 y≈0.65，静态街区整体悬浮在地形上方。这比“楼板材质错了”更根本：**CommercialArea 静态层与 Landscape 的垂直/世界对齐尚未闭合**。

`(91,181)` 仍是候选点；下一步应先确认子关卡/地形的高度对齐，再谈起点广场同机位。

## Ray 结果修正

进一步列出具体 terrain mesh 后：

- `landscape-5269` 可见实例 bounds 为 x `50..176`、z `76..202`、y `0..0`，**覆盖 (91,181)**；
- 因此候选点本地 Landscape 高度是 **0 m**，不是 -32 m；
- 之前的 `pickWithRay` 命中的 `landscape-5189/5187` 是远处 chunk，且 `createPickingRay(..., null, camera)` 的结果不可靠，不能作为前景地面高度证据。

当前可确认的是：本地地形在 0 m，楼板顶面 0.65 m，玩家约 0.67 m；**floor mesh 本身没有出现在前景**，而不是地形低了 30 m。高度错位结论撤回。

## 结论

楼板几何/实例存在，但**玩家附近可见地面不是这些 floor mesh**，或它们被地形/另一块草地面遮住。当前无法据此把候选点认定为原版起点广场；下一步需要：

1. 找出 (91,181) 实际可见草地对应的 mesh/材质（地形 chunk、草地面或别的楼层）；
2. 对齐地形高度与楼板可见性；
3. 再比较原程序砖石铺装和起点广场相机。

证据：`public/assets/world/walkable-surfaces.json`、`public/assets/world/geometry-manifest.json`、`research/screenshots/play-plaza-redfloor.jpg`、`play-plaza-yaw0b.jpg`、`play-plaza-instances-raised2.jpg`。
