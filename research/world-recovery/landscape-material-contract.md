# 原 Landscape 材质合同

原地形的纹理、权重、颜色因子和 UV 计算已静态恢复，可加载清单为 `public/assets/world/terrain-material-manifest.json`。原游戏光照、视图覆盖参数和实际画面对照仍未完成。证据来自 UAssetAPI、原 cooked DXBC、冻结参数表、D3D11 资源表和微软反汇编器，不是 REA 原生证据。

## 可直接实现的合同

`layers.Grass/Ground/Sand` 提供原 albedo/normal URL、SHA、颜色空间和线性 tint；`objects` 与 terrain-manifest 的 id 一一对应，共 144 块。GLB POSITION.xz 每块均为 0..126，不含 SectionBase，不可再减 SectionBase。材质 UV = (POSITION.xz + sectionBaseUE) × 0.20000000298023224；本场景一格为一米，因此每五米重复一次。不要直接用世界 XZ 乘 0.2，这会改变原相位。

| 层 | 原颜色纹理 | 原法线纹理 | 线性 tint |
|---|---|---|---|
| Grass | Grass_A | Grass_N | (0.1166670024, 0.1400000006, 0.09333299845) |
| Ground | Ground_MuddyGrass_2k_alb | Ground_MuddyGrass_2k_n | (1,1,1) |
| Sand | T_SandDunes_D | T_SandDunes_N | (0.53644800186, 0.56999999285, 0.48014900088) |

这不是按名称猜测的配方：三层原 shader 的 t7..t12 与冻结纹理列表、资源成员索引、实例覆盖逐项对应；t8/t11 的 Ground 参数覆盖父材质 DirtBrownTan 为 MuddyGrass。各原参数和 import/export pointer 见 JSON。

颜色 = saturate(sum(sRGBToLinear(albedo层) × tint层 × 原权重层))。权重从该块 `weightmap.channels` 指定的原通道采样，不存在层为零，不额外归一化。完整检查 2,359,296 个组件像素：分配通道和为 255..256，其中 72 个为 256，无全零像素。原公式保留这些量化结果。

粗糙度=1、金属度=0、UE Specular 参数=0.12807300687。Specular 不是 Babylon 的 specularPower。颜色混合和这些材质输入不等于恢复原 deferred 光照。

## 权重与法线坐标

对组件局部网格坐标 g，s=min(floor(g/63),1)，权重 UV=(g+s+0.5)/128。原组件 WeightmapSubsectionOffset=0.5，144 块均验证。不要将 heightmap atlas 偏移用于权重图。原 PNG 行对应 UE 局部 Y 增长；GPU 上传/采样必须保持这个方向。

原 heightmap 法线位于 PNG 的 B、A 通道，heightUV=(atlasOriginPixels+g+s+0.5)/atlasSize。各块 atlasOriginPixels、宽高和原 PNG URL 已提供。纹理线性采样，不做 sRGB 转换。

法线贴图使用原 RG，X/Y=2×RG−1，Z=sqrt(max(1−X²−Y²,0))；逐层按原权重相加后归一化得到 n。高度图 BA 同式重建 UE 方向 N。原 tangent basis 为 T=normalize((N.z,0,−N.x))、B=cross(N,T)。最终 UE 法线=normalize(n.x×T+n.y×B+n.z×N)；本场景无旋转，换到 Web 为 outUE.xzy。使用此显式基时不要再反转 PNG 绿色通道。若先只实现原混合 albedo，加几何法线预览光照，应明确尚未使用这条原逐像素法线链。

## 证明链与验证

父链 MainLevel Landscape → M_LandScape_Inst → M_LandScape 已确认。主材质仅保留一个 Material export，未保留完整 MaterialExpression 图，但 cooked shader 与冻结参数表仍在。四种排列（Grass；Grass+Sand；Grass+Ground；三层）各恢复 24 个合法 DXBC，共 96 个。93 个 shader 前缀可按完整 D3D11 资源表读取到 DXBC 边界；另 3 个非选定前缀的候选解压起点仍不完整，已单独记录。四个选定材质 shader 的完整资源表都通过。

冻结 FName patches、preshader 指令 3/4/35，以及 vector-first/scalar-packed 布局证实 cb3[1..3] 为三层掩码，cb3[6]/[8] 为 GrassColor.rgb / SandColor.rgb，cb3[9].x 为 Texture Scale。原 VS 对 SectionBase 的加法与 UE 源码生成的 Landscape uniform 布局吻合；JSON 保留原 shader 行号、字节位置、SHA 和外部源码引用。引用的 UE4.26 源码镜像仅作为结构核对，未当作原游戏完整源码。

144 块实例的 LayerMask one-hot、Weightmap0/Heightmap 引用、父链全部交叉核验；6 张已有原 PNG 的 SHA 再次校验。复现脚本为 `tools/asset-pipeline/package-terrain-material.py`，上游冻结表解析为 `research/world-recovery/terrain-uniform-binding-check.py`。

## 仍未证明的范围

原视图 normal/roughness override、mip bias、实时材质改参、纹理 LOD/各向异性、光照/阴影/lightmap、曝光和色调映射没有原运行时取证。此清单的正常预览采用 identity normal override，不宣称已捕获原帧的全局值。最终显示必须把恢复的材质计算与预览光照区分，完成原游戏实际画面对照后才能声称视觉一致。本次没有修改 src、原安装或其他代理的 material-manifest。
