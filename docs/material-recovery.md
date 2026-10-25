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
```

## 当前 Web 状态

- 纹理已经加载；
- `building_02_d` 的 alpha 是**窗格遮罩**（alpha 0/255 二进制；白色区域对应深色玻璃窗），而该 material 的子网格本身只覆盖窗格；
- 因此对 `building_02_Inst` 单独加了 `clouds.png` emissive 层，颜色使用恢复的 Emissive Colour `(0.07746, 0.095, 0.061736)`，tiling 0.2；
- `building_02_Inst` 的 Contrast/EmissiveAmount 仍没有完整 shader math；
- `brick_02_TintB_Inst2` 现在使用派生纹理 `brick_02_d_tintB.png`：按恢复的 Tint Colour `(.06,.021616,.001713)`、Tint Opacity `.633` 做线性混合；
- 但完整 opacity 会让同机位 mean luma 降到 49.4（原版 55.8），说明父 `-Tilable_mat` 的 tint mask/layering 仍未恢复，所以实际使用 **.177 effective opacity（.633 × .28）**，并用纹理 alpha 作为每 texel 权重；
- 这是**派生/校准资产**，不是原版像素；生成脚本 `scripts/derive-brick-tint.py`，参数和 sha256 在 `research/world-recovery/brick-tint-derivation.json`；
- 同机位 mean luma 57.1 / std 30.7，接近原版 55.8 / 31.3，石墙从灰色回到暖棕灰；
- **没有把 Emissive Colour 直接加到整面墙**，避免未遮罩区域错误发绿光。

同机位试验截图：`research/screenshots/building-brick-tint-calibrated.jpg`；`building-emissive.jpg` 是加 tint 前的窗格自发光试验。页面纹理失败 0，B1 通过。

清单：[building-material-parameters.json](building-material-parameters.json)

## 下一步

1. 解码 `/Game/UrbanCity/Materials/building_mat` 与 `-Tilable_mat` 的 shader graph；
2. 找到 emissive mask/Contrast 的输入纹理；
3. 只对 mask 区域应用 Emissive Colour；
4. 对 brick tint 做纹理级乘色，而不是直接改材质自发光。

这是 Gate 3 石材/檐口明暗差距的直接原因。
