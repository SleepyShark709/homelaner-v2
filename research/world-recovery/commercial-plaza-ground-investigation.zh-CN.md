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

## Terrain active 检查（2026-10-25）

> 修正：直接在 render 之外读 `isActiveMesh()` 会得到 stale false；在 `scene.render()` 后读取 `scene.getActiveMeshes()`，`landscape-5269` **确实 active**。因此“正确 terrain chunk 没有 active”的结论撤回。

- `landscape-5269` 的 bounding box x50..176/z76..202/y0..0，渲染后进入 active 列表；
- `landscape-5189` 也在 active 列表；
- 强制所有 `landscape-*` active（288 mesh）仍不改变前景。
- `CommercialArea:677/678` 楼板在 render 后同样 active。

调试辅助：play debug hook 增加 `pick(x,y)`，用 `Matrix.Identity()` 构造 picking ray。

## Active mesh 检查（2026-10-25）

> 修正：下方 `isActiveMesh=false` 是 render 外 stale 状态；render 后 floor 677/678 实际 active。保留该段仅说明强制 active 也没有改变画面。

- 默认情况下 `CommercialArea:676/677/678` 的 floor mesh `enabled=true`、`isVisible=true`，但 `isActiveMesh=false`，没有进入 `scene.getActiveMeshes()`。
- 设置 `alwaysSelectAsActiveMesh=true` 后，它们进入 active 列表（activeCount=892），但画面仍是草地。
- 同时设置 active + `backFaceCulling=false` + `flipFaces` + 关闭 depth write：仍不变。

因此问题不只是视锥剔除；floor mesh 即使进入 active 列表也没有覆盖前景地面。需要继续查实例几何/材质或其它遮挡 mesh。

## Ray 结果修正

进一步列出具体 terrain mesh 后：

- `landscape-5269` 可见实例 bounds 为 x `50..176`、z `76..202`、y `0..0`，**覆盖 (91,181)**；
- 因此候选点本地 Landscape 高度是 **0 m**，不是 -32 m；
- 之前的 `pickWithRay` 命中的 `landscape-5189/5187` 是远处 chunk，且 `createPickingRay(..., null, camera)` 的结果不可靠，不能作为前景地面高度证据。

当前可确认的是：本地地形在 0 m，楼板顶面 0.65 m，玩家约 0.67 m；**floor mesh 本身没有出现在前景**，而不是地形低了 30 m。高度错位结论撤回。

## 仅保留本地地形（2026-10-25）

把除 `landscape-5269` 外的所有 `landscape-*` mesh 禁用后，画面**仍是同一片草地**。因此前景草地就是覆盖候选点的本地 terrain chunk（y≈0），不是远处 5189/5187 的遮挡。

但 floor 677/678 在 render 后 active、顶面 0.65 m，仍没有覆盖这片草地；问题集中在 floor 实例的实际渲染/材质/深度，而不是 terrain 缺失。

## 实例矩阵 bake 实验（2026-10-25）

调试函数 `play.bakeFloors()` 把 floor mesh 的 thin-instance `matrixData` 直接 bake 进几何、把 `thinInstanceCount` 设为 0，再刷新包围体并强制 active。结果前景仍没有砖石地面。

这排除了“只是实例矩阵没有上传”的简单解释；floor mesh 的可见性问题仍在几何/材质/遮挡层。

## 结论

楼板几何/实例存在，但**玩家附近可见地面不是这些 floor mesh**，或它们被地形/另一块草地面遮住。当前无法据此把候选点认定为原版起点广场；下一步需要：

1. 找出 (91,181) 实际可见草地对应的 mesh/材质（地形 chunk、草地面或别的楼层）；
2. 对齐地形高度与楼板可见性；
3. 再比较原程序砖石铺装和起点广场相机。

证据：`public/assets/world/walkable-surfaces.json`、`public/assets/world/geometry-manifest.json`、`research/screenshots/play-plaza-redfloor.jpg`、`play-plaza-yaw0b.jpg`、`play-plaza-instances-raised2.jpg`。
