# 城区、公园灰白材质：三类原着色器恢复

本轮恢复的是原资源中的材质输入与计算，未改游戏 src。证据来源为原 cooked 材质 Extras、冻结 uniform 数据、D3D11 资源表、DXBC 与微软反汇编；这不是 REA retained Evidence。UE 4.26 源码镜像仅用于核对布局与运算语义，不声称持有游戏原工程。

## 为什么已有原贴图仍然灰白

此前转换器只能识别明确命名参数并投影到通用 PBR。WorldTilingMaster 的颜色要按世界坐标三向采样，不能直接套 UV0；Foliage_Mat 和 prp_bench_Mat 使用固定纹理引用，纹理角色没有出现在命名参数表里。为避免猜测，这些路径此前没有接入颜色。因此“部分 PBR 参数已映射”的状态也不能代表已有 baseColor。

`material-shader-impact.json` 按实际 section→UE slot→组件覆写→父材质解析，并采用运行时的显式隐藏规则。以下是原 35 图范围中的静态场景引用数，不是同时加载数，也不是截图像素覆盖率。

| 原基材 | 地图数 | 受影响对象引用 | section 引用 | 重点区域 |
|---|---:|---:|---:|---|
| WorldTilingMaster | 14 | 948 | 2,147 | DownTown 172 对象、214 section；Park 29 对象；道路、广场、地面及使用这些槽的建筑 |
| Foliage_Mat | 9 | 679 | 974 | DownTown 166 对象、211 section；Park 28 对象；树叶与组合花坛 |
| prp_bench_Mat | 8 | 426 | 868 | DownTown 70 对象、144 section；Park 28 对象、56 section；长椅及含长椅的合并网格 |

完整排序也保留了交通灯、墙面、蕨类、树皮等尚未恢复的族。高对象数不等于占画面面积大。本轮没有把所有灰白现象归因于这三类。

## 已恢复的资源契约

`public/assets/world/material-manifest.json` 新增 20 个 `shaderRecovery`：17 个 `world-triplanar`、2 个 `foliage-vertex-mask`、1 个 `standard-pbr-evidenced`。状态为 `partial-dxbc-recovery`，完整原灯光、烘焙光照、贴花、雾和后处理均不包含在此状态内。

WorldTilingMaster 的三向采样位置来自最终绝对世界坐标。Web RH 米坐标先 `.xzy * 100` 回 UE 厘米，再除以 `-abs(Albedo/Normal World Scale)`，负号来自原 preshader，必须保留。原 PS 从 translated world position 减去 PreViewTranslation；Web 已有绝对位置时不能再减相机位置。颜色权重为 `clamp(3*abs(N.x/z)-1)`，法线混合权重则是 `clamp(abs(N.x/z))`，两者不能混用。粗糙度真实采样的是 R，并乘原 RoughnessBrightness。完整位置、颜色、法线和强度公式均在 `material-shader-contract.sample.json`，不能改成三个权重归一化的另一种三向算法。

Foliage 的颜色是 `clamp(3*albedoRGB*clamp(vertexR*Occlusion,0,1),0,1)`；透明度是 albedo A，阈值 0.3333；粗糙度是原 R × Roughness。26 种相关原网格的 LOD0 ColorVertexBuffer 都为空，688 个组件与 31 个精确模板均无颜色覆写，故这批的 vertexR=1 是有原数据支持的默认值。证据见 `geometry-vertex-color-audit.json`。叶片 SSS、风摆和实例 LOD 抖动仍未由普通 PBR 还原。

Bench 的原 UV0 颜色、法线、金属、粗糙度和 AO 已进入普通 channels。金属取 R，粗糙度取 R × Param，AO 取 R；更新的 ORM 已含乘数。派生 ORM 在源 SRGB 解码后一次量化到 8-bit，避免额外中间取整；离线打包仍可能把 clamp 提前到纹理过滤之前，原计算公式继续保留。

## TBN 与坐标细节

原静态网格 VS 去掉世界矩阵各轴的正长度，保留负轴方向；对 T 和 N 使用同一去 scale 矩阵，并不使用 inverse-transpose。原量化 T 先经两次 cross 修正，再变换；T/N 输出不再次 normalize。PS 收到线性 centroid 插值后的 T、N，直接重建 `B=cross(N,T)*hand`。不得先 normalize 这些插值向量，也不能一般化为只依赖 N 的近似式。

`vertex-frame.json` 记录原 shader-22 的 hash/指令、源码镜像行号与实例符号限制。UModel 导出交换 Y/Z、分别 normalize T/N 的 XYZ、保留原 tangent.w 符号；因此原量化向量长度已经略有损失。当前契约恢复了原运算，但不声称当前 glTF 的每一位输入等同原 GPU 顶点缓冲。

## 验证与可复现性

三个原材质共 150 段 DXBC 均成功抽取，资源表前缀完整解析且经 D3DDisassemble 验收，没有未解析 DXBC literal。冻结表中的标量、向量、纹理索引与 preshader 均与原实例参数合并，结果保存在 `bindings.json`。

独立小型 DXBC 运算解释器运行了 425 组 WorldTilingMaster 数值用例，涵盖原 17 实例参数、负位置、不同 PreViewTranslation、非单位插值 TBN 与正负 handedness；另运行 300 组 Foliage/Bench 用例，采用不同 RGBA 值验证源通道。全部通过，最大 Float64 公式差异约 9.8e-14。该测试验证代数与通道，不代替 GPU 精度、纹理过滤或浏览器截图比较。检查过程中纠正了 `dest.w + source.yzwx` 实际选 R 的指令掩码细节。

本轮复用全部原图片，不全量重导。复现增量步骤：

```powershell
python tools/asset-pipeline/inspect-material-shaders.py
python tools/asset-pipeline/restore-evidenced-shaders.py
python tools/asset-pipeline/validate-evidenced-shaders.py
python tools/asset-pipeline/validate-world-materials.py
```

若先运行 base/MID 重建，必须随后运行 `restore-evidenced-shaders.py` 重新应用这些运算描述。浏览器接入由主代理完成，当前资源报告不宣称已实现同机位原游戏视觉等价。
