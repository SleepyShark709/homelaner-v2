# 白色路面 / 公园铺装：pass3 证据与下一步

日期：2026-10-25。范围：默认启动城市与 Park 静态查看器；不是原游戏运行对照。

## 已定位的直接原因

Park 的 81 个 `Path_A` 实例（`Park:64:instance:*`）绑定 `/Game/UrbanCity/Materials/Tileable/Concrete_Tile_mat`。该材质记录：

- `blendMode=BLEND_Opaque`，`factors.baseColor=[1,1,1,1]`，`channels.baseColor=null`；
- `parameters.texture` 为空，因此 Web 当前只得到白色 PBR，不是贴图加载失败；
- 冻结 uniform 中有 3 个未命名纹理参数，默认对象依次为 `Concrete_Tile_N`、`Concrete_Tile_A`、`Concrete_Tile_C`；
- cooked 材质只序列化了 `Normal ← MaterialExpressionTextureSample_0` 和 `Metallic ← MaterialExpressionTextureSample_1`，没有序列化 `BaseColor` 输入；
- 解码 JSON 的 `CachedExpressionData.ReferencedTextures` 确实引用 N/A/C 三张纹理，但没有足够的表达式连接来证明哪一张进入 BaseColor。

因此“白色”是材质图/编译 shader 连接缺失，不是纹理未导出。仅凭 `_A`、`_N`、`_C` 文件名直接绑定属于猜测，本轮没有把它写进 `material-manifest.json`。

## 同一画面中的其他白色来源（不能混为一个原因）

- `/Game/Downtown/Materials/-Pavement__Mat`：580 个 section 引用，基色通道存在（如 `RoadMain_A`、`Sidewalk_A_A`），需要继续核对实例参数/UV/光照，不应重复当作“缺图”。
- `/Game/Downtown/Materials/-Standard_Shader_Mat`：4,733 个 section 引用，是最大的材质族；多数实例有基色贴图，白色建筑还需按实例逐项核查，不能仅凭截图归因。
- `/Game/InfinityBladeGrassLands/.../M_Env_Plains_Mountain01`：远景山体材质没有纹理，只有 `color=(0.4,0.4,0.4)` 矢量参数，且 Web 尚未接入该参数；它的大面积灰白主要是背景山体 + 预览光照/缺雾，不是公园铺装问题。
- 公园草地已由第二轮 `grass-parallax-macro` 恢复出原贴图颜色；`-Pavement__Mat` 的 `Path_D` 已绑定 `Soil_A_A`。

## 下一步（证据顺序）

1. 按 `Concrete_Tile_mat` 的 DXBC（`research/world-recovery/material-shader-recovery/Concrete_Tile_mat/`）解析纹理采样槽和通道写入，确认 BaseColor、Roughness、Metallic、AO 的实际来源。
2. 如果 BaseColor 使用 A 纹理，且 `Color` 参数参与乘法，再把连接写成可复现的 `shaderRecovery` 合同并重生成 manifest；同时保留未解出的 UV/宏参数缺口。
3. 对 `-Pavement__Mat` 与 `-Standard_Shader_Mat` 分别做实例级审计，不要用一个材质结论覆盖整族。
4. 浏览器截图验证使用 `scripts/capture-world.mjs`；截图只证明 Web 显示，不证明与原游戏像素等价。

证据：`public/assets/world/material-manifest.json`、`research/world-recovery/material-shader-recovery/Concrete_Tile_mat/{index.json,uniforms.json}`、`research/rea-audit/decoded-world-assets/UNDEFEATED/Content/UrbanCity/Materials/Tileable/Concrete_Tile_mat.json`、`research/screenshots/park-pick.jpg`。
