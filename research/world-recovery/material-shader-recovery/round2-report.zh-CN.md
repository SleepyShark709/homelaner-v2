# 第二轮：公园铺装与建筑材质

新增五份原着色器计算契约，原先二十份逐项保持不变，总数为二十五。没有重新批量导出纹理，没有修改 Web src 或原安装。

## 优先目标与实际范围

通过最新几何 section、原材质槽和组件覆写重新统计缺失 baseColor 的引用，选择三类实际使用的基材。以下是原 35 地图中按显式可见性过滤后的静态引用数，不是某张截图的可见像素面积或同时加载数量。

| 基材 | 对象引用 | section 引用 | 实际改善范围 |
|---|---:|---:|---|
| Concrete_Mat | 163 | 811 | 住宅区为主的混凝土建筑面；另有两个原参数实例 |
| cobbleStone_01_Mat | 427 | 467 | 市中心石铺、组合花坛；公园 28 个对象 |
| Ground_GrassThickGreen | 49 | 49 | 公园原 Path_A 网格 |

调查还解出了 Crosswalk_Mat，但原固定引用与几何证明它用于行人信号灯，不能因名字将它归类为道路铺装。本轮没有接入或计入该候选。已经恢复的世界坐标道路材质保留；不能把仍然发白的每一块道路都解释成“原图缺失”。

## 可消费接口

完整实例记录在 `material-shader-round2-contract.sample.json`，已同步到 `material-manifest.json` 的 shaderRecovery。

**concrete-mildew，三份。** 全部采 UV0。颜色混合权重是 gradientMask.R × 原 Mildew Gradient Amount，加 mildewMask.R × 原 Mildew Amount；权重本身不先 clamp，最终将原 albedo 与 Mildew Color 混合后 clamp。插件只替换最终 baseColor。原法线、粗糙度 R 已通过普通 channels/ORM 提供。

**standard-pbr-evidenced，一份。** CobbleStone 的原固定颜色、法线、粗糙度 R 已直接接入。金属度 0，原 specular 字面量约 0.389381。不是从贴图文件名推断用途。

**grass-parallax-macro，一份。** 公园 Path_A 的输入不是简单的草地颜色图：先在 UV0 × 2 采高度 R，计算单步视差偏移；偏移只乘相机向量在原 T/B 上的投影，不除以 view.z。颜色、法线和 gloss 使用偏移后的 UV；三个频率的宏观遮罩仍使用原 UV0。原颜色还包含固定线性色调与六次方视角混合。粗糙度由 gloss R、宏观遮罩与原 Macro_roughnessContrast 反向计算。所有常数、正负号、RGB 颜色空间及完整公式均在合同，不用通用 ORM 取代该动态计算。原法线 Z × 0.8 后单位化，并用已核证的原插值 TBN 转到世界空间。

## 原证据与验证

三个采用的基材共解出 68 段合法 DXBC；另一个未采用的信号灯候选为 9 段。冻结 uniform、完整 D3D11 资源表、固定纹理索引、原实例参数均保存于 `round2-bindings.json`。两份 Concrete 实例没有独立静态 permutation，按其原参数求值继承 shader；未把新的静态排列误当作父 shader。

独立指令解释器完成 800 组差分测试：混凝土 480、石铺 160、公园 Path_A 160。覆盖变化的 UV、不同纹理通道值、相机方向、非单位插值 TBN 和原实例值。公园粗糙度包含 35 个 clamp 到零及 125 个区间内结果；最大 Float64 公式差异约 3.8e-16。原 DXBC float32 字面量也已保留，包括反汇编同样显示为 0.400000、实际位值不同的宏观混合系数与颜色幂指数。

这些证据属于原 UAsset/DXBC 资产分析与自编验证，不是 REA retained Evidence。数学验证不代替浏览器 GPU、原光照、材质过滤或同机位截图验证。

## Specular 与 F0

原三种 PS 均能追踪到非金属 `F0=0.08×UE specular`。当前本地 Babylon 在 IOR=1.5 且反射颜色为白时，默认 F0=.04，因此 `metallicF0Factor=2×specular` 可匹配这一项。该 Babylon 版本同时将此因子用于 F90 等项，不能由此声称整条 UE Fresnel/能量模型等价。原指令、当前 Babylon 源文件行号/hash 与适用条件保存在 `specular-f0-mapping.json`。

## 复现

复用本轮已保存的 shader 抽取结果时运行：

```powershell
python tools/asset-pipeline/restore-evidenced-shaders-round2.py
python tools/asset-pipeline/validate-evidenced-shaders-round2.py
python tools/asset-pipeline/validate-world-materials.py
```

完整重建顺序仍为基础材质 → 内嵌 MID → 第一轮 shader → 第二轮 shader。本轮恢复保留原图像，按需重打少量 ORM。还未恢复的材质、天空、原静态灯光和所有游戏渲染效果不能计入本轮完成范围。
