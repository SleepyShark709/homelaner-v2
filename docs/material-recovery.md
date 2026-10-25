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
- 但父材质 shader graph（Contrast、Emissive mask、Tint 叠加）没有恢复；
- `building_02_Inst` 仍是白色 albedo，石材偏中性灰；
- `brick_02_TintB_Inst2` 仍是白色 albedo，砖材偏灰；
- **没有把 Emissive Colour 直接加到整面墙**，因为 emissive mask 未恢复，整面加会错误发绿光。

清单：[building-material-parameters.json](building-material-parameters.json)

## 下一步

1. 解码 `/Game/UrbanCity/Materials/building_mat` 与 `-Tilable_mat` 的 shader graph；
2. 找到 emissive mask/Contrast 的输入纹理；
3. 只对 mask 区域应用 Emissive Colour；
4. 对 brick tint 做纹理级乘色，而不是直接改材质自发光。

这是 Gate 3 石材/檐口明暗差距的直接原因。
