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

## 结论

楼板几何/实例存在，但**玩家附近可见地面不是这些 floor mesh**，或它们被地形/另一块草地面遮住。当前无法据此把候选点认定为原版起点广场；下一步需要：

1. 找出 (91,181) 实际可见草地对应的 mesh/材质（地形 chunk、草地面或别的楼层）；
2. 对齐地形高度与楼板可见性；
3. 再比较原程序砖石铺装和起点广场相机。

证据：`public/assets/world/walkable-surfaces.json`、`public/assets/world/geometry-manifest.json`、`research/screenshots/play-plaza-redfloor.jpg`、`play-plaza-yaw0b.jpg`、`play-plaza-instances-raised2.jpg`。
