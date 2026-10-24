# 白色路面 / 公园铺装：pass3 证据与已接入修复

日期：2026-10-25。范围：默认启动城市与 Park 静态查看器；不是原游戏运行对照。

## 已定位并接入的直接原因

Park 的 81 个 `Path_A` 实例（`Park:64:instance:*`）绑定 `/Game/UrbanCity/Materials/Tileable/Concrete_Tile_mat`。修复前该材质记录：

- `blendMode=BLEND_Opaque`，`factors.baseColor=[1,1,1,1]`，`channels.baseColor=null`；
- `parameters.texture` 为空，因此 Web 只得到白色 PBR，不是贴图加载失败；
- 冻结 uniform 中有 3 个未命名纹理参数，默认对象为 `Concrete_Tile_N`、`Concrete_Tile_A`、`Concrete_Tile_C`；
- cooked 材质只序列化了 `Normal ← MaterialExpressionTextureSample_0` 和 `Metallic ← MaterialExpressionTextureSample_1`，没有序列化 `BaseColor` 输入。

## 原 DXBC 证据

`Concrete_Tile_mat` 的 shader map 中 `shader-0-ps_5_0.asm` 的资源表与 PS 指令可以闭合角色：

- `t8` 绑定 `Concrete_Tile_N`；PS 对它做 XY→Z 法线解码；
- `t9` 绑定 `Concrete_Tile_A`；PS 采样后乘 `cb3[3].xyz`（材质 `Color`），`mul_sat` 后写入 `o2`（base color 目标）；
- `t10` 绑定 `Concrete_Tile_C`；原始 PS 也采样它，但其通道打包（R/G/B 对应什么）尚未建立。

因此 `Concrete_Tile_A` 作为基色、`Concrete_Tile_N` 作为法线是 DXBC 绑定与采样用途证据，不是按文件名猜接。`Concrete_Tile_C` 仍未绑定为 ORM。

可复现脚本：

```powershell
python tools/asset-pipeline/restore-texture-sample-materials.py
```

脚本会重新核对 `index.json` 的纹理绑定、`uniforms.json` 的默认纹理、`shader-0-ps_5_0.asm` 的采样/写入指令和已发布 PNG 是否存在，然后只给该材质补 `channels.baseColor` / `channels.normal`，并把证据写入 `research/world-recovery/material-shader-recovery/texture-sample-recovery.json`。它必须在 `restore-world-materials` / `restore-evidenced-shaders` 之后运行，避免下次重建时丢失。

浏览器结果：Park 的白色 Path_A 已显示混凝土贴图与法线；截图 `research/screenshots/park-texture-recovery.jpg`，计数 4,105 个对象、144 块地形、0 资源/纹理失败。该结果只证明 Web 显示改善，不是与原游戏像素等价。

## 同一画面中的其他白色来源（不能混为一个原因）

- `/Game/Downtown/Materials/-Pavement__Mat`：580 个 section 引用，基色通道存在（如 `RoadMain_A`、`Sidewalk_A_A`），需要继续核对实例参数/UV/光照，不应重复当作“缺图”。
- `/Game/Downtown/Materials/-Standard_Shader_Mat`：4,733 个 section 引用，是最大的材质族；多数实例有基色贴图，白色建筑还需按实例逐项核查，不能仅凭截图归因。
- `/Game/InfinityBladeGrassLands/.../M_Env_Plains_Mountain01`：远景山体材质没有纹理，只有 `color=(0.4,0.4,0.4)` 矢量参数，且 Web 尚未接入该参数；它的大面积灰白主要是背景山体 + 预览光照/缺雾，不是公园铺装问题。
- 公园草地已由第二轮 `grass-parallax-macro` 恢复出原贴图颜色；`-Pavement__Mat` 的 `Path_D` 已绑定 `Soil_A_A`。

## 下一步（证据顺序）

1. 对 `-Pavement__Mat` 与 `-Standard_Shader_Mat` 分别做实例级审计和 DXBC 角色恢复，不要用一个材质结论覆盖整族。
2. 解析 `Concrete_Tile_C` 的通道用途；有证据后再把 compact 接入 ORM，当前保持缺口。
3. 背景山体需要先决定是否属于本次原版城市画面范围；若保留，需接入其 `color` 参数与原始雾/光照，而不是用白色默认材质。
4. 浏览器截图验证使用 `scripts/capture-world.mjs`；截图只证明 Web 显示，不证明与原游戏像素等价。

证据：`public/assets/world/material-manifest.json`、`research/world-recovery/material-shader-recovery/Concrete_Tile_mat/{index.json,uniforms.json,shader-0-ps_5_0.asm}`、`research/rea-audit/decoded-world-assets/UNDEFEATED/Content/UrbanCity/Materials/Tileable/Concrete_Tile_mat.json`、`research/world-recovery/material-shader-recovery/texture-sample-recovery.json`、`research/screenshots/park-texture-recovery.jpg`。
