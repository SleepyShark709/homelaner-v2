# 建筑石材/砖材恢复记录（Gate 3）

## 起点建筑 material slots

`SM_MERGED_Building_2_01_9` 的可见槽位（从运行时 Babylon material 名称直接读取）：

```text
/Game/UrbanCity/Materials/Tileable/brick_02_TintB_Inst2
/Game/UrbanCity/Materials/Buildings/building_02_Inst
/Game/UrbanCity/Materials/-Window_mat
/Game/UrbanCity/Materials/Tileable/Tilable_metal_TintC_Inst
/Game/-HeroGame/Materials/MaterialInstance/MI_RoofTop
/Game/ModularStreetPack/Materials/L_Aircon_Mat
/Game/ModularStreetPack/Materials/Roof_Felt_Mat
/Game/ModularStreetPack/Materials/Galvanized_Steel_Mat
```

## 已解码参数

### building_02_Inst

```text
parent          /Game/UrbanCity/Materials/building_mat
Diffuse         building_02_d
Normal          building_02_n
Roughness       building_02_r
Contrast        0.43796
EmissiveAmount  1.74378
Emissive Colour (0.07746, 0.095, 0.061736)
TwoSided        true
OpacityMaskClip 0.3333
```

### brick_02_TintB_Inst2

```text
parent          /Game/UrbanCity/Materials/-Tilable_mat
Diffuse         brick_02_d
Normal          brick_02_n
Normal Strength 1
Roughness       1
Tint Colour     (0.06, 0.021616, 0.001713)
Tint Opacity    0.633027
```

### brick_02_TintA_Inst（檐口/trim 变体）```text
parent          /Game/UrbanCity/Materials/-Tilable_mat
Diffuse         brick_02_d
Normal          brick_02_n
Roughness       0.666245
Tint Opacity    0
Tint Colour     (1, 0.616354, 0.578100)
Grunge 1/2/3    Opacity 2.6000 / -0.8935 / 0.6259
Height          0.145475
```

TintA 的 `Tint Opacity=0`，所以 Web 不应用它的 Tint Colour，只应用恢复的 roughness .666245；Grunge/Height（parallax）层仍未恢复。

### Tilable_metal_TintC_Inst（窗框/金属）

```text
Diffuse        metal_01_d
Normal         metal_01_n
Detail Normal  metal detail normal
Tint Colour    (0.014291, 0.016776, 0.045000) linear
Tint Opacity   0.898036
Roughness      1.849306
Detail Normal Scale 0.599268
Detail Normal Strength 2.380776
```

Web 用 `scripts/derive-metal-tint.py` 生成 `metal_01_d_tintC.png`，按 Tint Colour × Tint Opacity 做线性混合；roughness clamp 到 1。窗框因此变为接近原版的深蓝黑，但 detail-normal/父 `-Tilable_mat` 图仍未恢复。

## 当前 Web 状态

- 纹理已经加载；
- `building_02_d` 的 alpha 是**窗格遮罩**（alpha 0/255 二进制；白色区域对应深色玻璃窗），而该 material 的子网格本身只覆盖窗格；
- 因此对 `building_02_Inst` 单独加了 `clouds.png` emissive 层，颜色使用恢复的 Emissive Colour `(0.07746, 0.095, 0.061736)`，tiling 0.05（0.2 时会在窗格上形成明显的重复蓝色横带）；完整颜色实际缩放到 **0.35**；
- `-Window_mat` 的 clouds emissive 从 `.08/.11/.17` 校准到 `.14/.19/.26`，同机位整体 mean luma 从 54.23 提到 **56.03 / std 30.42**（原版 55.73 / 31.34）；这是预览 emissive 校准，不是原版玻璃 shader；
- `building_02_Inst` 的 Contrast/EmissiveAmount 仍没有完整 shader math；
- `brick_02_TintB_Inst2` 现在使用派生纹理 `brick_02_d_tintB.png`：按恢复的 Tint Colour `(.06,.021616,.001713)`、Tint Opacity `.633` 做线性混合；
- 但完整 opacity 会让同机位 mean luma 降到 49.4（原版 55.8），说明父 `-Tilable_mat` 的 tint mask/layering 仍未恢复，所以实际使用 **.177 effective opacity（.633 × .28）**，并用纹理 alpha 作为每 texel 权重；
- 这是**派生/校准资产**，不是原版像素；生成脚本 `scripts/derive-brick-tint.py`，参数和 sha256 在 `research/world-recovery/brick-tint-derivation.json`；
- 同机位 mean luma 57.1 / std 30.7，接近原版 55.8 / 31.3，石墙从灰色回到暖棕灰；
- **没有把 Emissive Colour 直接加到整面墙**，避免未遮罩区域错误发绿光。
- 2026-10-25 的 `play.pick()` CSS→render 坐标修正后，同机位对窗格/石柱的射线仍穿过前景建筑，命中 `SM_SkyDome` / `SM_Env_Plains_Mountain_01` / landscape。进一步在 `thinInstanceSetBuffer` 之前设置 `isPickable`/`thinInstanceEnablePicking` 并 refresh 仍然无效；再用 thin-instance 世界矩阵做局部 AABB 回退也没有返回前景命中。说明不是“晚设置 picking”或简单 AABB 回退能解决的问题；逐材质屏幕采样工具暂不可用，这不是材质颜色结论。
- 起点店面对象是 `CommercialArea:703/SM_MERGED_Building_2_01_9`，5 个子网格材质已按 bounds 识别：base=`brick_02_TintA_Inst`、facade=`building_02_Inst`、trim=`brick_02_TintB_Inst2`、windows=`-Window_mat`、frames=`Tilable_metal_TintC_Inst`；bounds 和 vertices 在 [storefront-meshes.json](../research/world-recovery/storefront-meshes.json)。
- 2026-10-25 进一步试验：把 `brick_02_d_tintB` 的 tint scale 从 .28 降到 .08，或把 `building_02_Inst` 的 albedoColor 提到 1.15，同机位 mean luma 都保持 56.02–56.03，石柱视觉几乎不变。说明可见石柱不是由这两个字段单独控制（或 PBR/纹理/光照占主导）；这些实验已回退，不要重复。

同机位对照图：[comparison-gate3-materials.jpg](../research/runtime-observation/comparison-gate3-materials.jpg)；单边试验截图：`research/screenshots/building-metal-tint.jpg`、`building-emissive-tuned.jpg`、`building-trim-roughness.jpg`。页面纹理失败 0，B1 通过。

### 石材区域采样

左侧柱子石材（避开玻璃和深色框）：

```text
原版 RGB mean (63.3, 61.4, 61.5)
Web  RGB mean (70.0, 66.8, 63.0)
Web - 原版    (+6.7, +5.4, +1.5)
```

Web 石材仍比原版亮约 7 级，并且偏红（Web R-B=7.0，原版 R-B=1.8）。继续降低 TintB opacity 会减轻偏红，但会让已经偏亮的石材更亮；主要剩余差异是**烘焙阴影/lightmap + 缺失 grunge**，不是基础 tint 本身。采样清单：`research/world-recovery/material-color-samples.json`；可用 `python scripts/measure-material-color.py` 复现。

清单：[building-material-parameters.json](building-material-parameters.json)

## 下一步

1. 解码 `/Game/UrbanCity/Materials/building_mat` 与 `-Tilable_mat` 的 shader graph；
2. 找到 emissive mask/Contrast 的输入纹理；
3. 只对 mask 区域应用 Emissive Colour；
4. 对 brick tint 做纹理级乘色，而不是直接改材质自发光。

这是 Gate 3 石材/檐口明暗差距的直接原因。
