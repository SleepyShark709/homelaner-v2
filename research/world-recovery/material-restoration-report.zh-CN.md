# 原材质恢复：实际交付与缺口

独立入口：`public/assets/world/material-manifest.json`，schemaVersion=1。没有修改几何 glTF 或游戏 src；原安装只读。

## 已交付

- 材质描述 4221 个，采用完整 UE 包名作键，保留实例父链、源参数、BasePropertyOverrides、blend/two-sided/alpha clip。
- 场景几何与组件覆写共引用 3940 种材质包；缺失描述 0。
- 原像素 PNG 1155 张，另保留原 HDR 3 张；按 Game/Engine 完整包路径发布，避免同名冲突。纹理合计 814.1 MiB。
- 317 张法线通过原 BC5 独立解码与 PNG R/G 对照，且反向绿通道假设被数据排除；17 张仍为 unknown。材质中可直接使用的 normal 绑定为 235 个。
- ORM 78 份，R=AO、G=roughness、B=metallic，linear；scalarFactorsAlreadyApplied=true，运行时乘数为 1。
- 1860 个原组件覆写记录另存于 instanceOverrides。运行时应使用 geometry-manifest 各对象完整 slot 覆写，并优先使用 gltfMaterials.sourceMaterial 的原 native section/slot 证据；不能把 glTF materialIndex 当 UE slotIndex，也不能按同名材质猜测。

| 绑定通道 | 材质数 |
|---|---:|
| baseColor | 855 |
| normal | 268 |
| roughness | 36 |
| metallic | 31 |
| occlusion | 50 |
| emissive | 647 |
| opacity | 18 |

## 使用约定

materials 为 package→descriptor。channels 的每个值是 null 或包含 texturePackage/url/colorSpace/channel/texCoord/sourceParameter/evidence 的对象；channel 明确是 rgb 或 r，未猜测 Compact 或 MR 包装图各通道用途。normalConvention=directx 的纹理保留原 UE 压缩像素的绿通道；根据 root 已验证的 Babylon RH/glTF 切线约定，运行时对应 invertY=false。unknown 不作已正确处理。

每张 verified normal 独立读取原 .ubulk 的 BC5 压缩块，覆盖多个分散位置，与 PNG 的 R/G 比较（≤1/255 压缩取整误差），并要求 255-G 假设不能同样匹配。小纹理内嵌数据、没有可验证 ubulk、或近乎平坦绿通道无法区分方向者保持 unknown。该证明确认导出未翻绿通道，不是整套网格法线着色的原游戏截图等价证明。

roughness/metal/AO/opacity 仅从明确单一语义的原参数挑选；当 RGB 分量相差≤8/255 时，允许把它作为 BC1 RGB565 量化后的近灰度标量图取 R，记录 scalarProjection。此为有界 PBR 投影，不声称恢复了原 shader 的所有数学运算。ORM 会按源 SRGB 状态线性化输入并烘入显式标量，必要时双线性调整尺寸。未知通道使用的 AO=1/roughness=1/metal=0 中性常量列入 fallbackChannels，**不计为原效果恢复**。

## 尚未恢复

status=partial-pbr-projection 的材质 2123 个，表示可利用部分原数据；partial-dxbc-recovery 的材质 25 个，附有从原 DXBC 验证的 shaderRecovery 运算契约；shader-unmapped 的材质 2073 个，没有足够证据绑定其主要着色输入。没有任何状态声称完整 UE 渲染效果已重建。

源参数可证明纹理的作者语义，但完整编译 shader 的连接和表达式仍未还原。固定 ReferencedTextures 没有明确角色的材料不会按纹理文件名或旧 UModel Diffuse 猜接。原 Compact/MR 通道、地形 Grass/Sand/Ground 权重混合、SSS、服装 ID 区域染色、风摆/顶点偏移、detail normal、world-aligned UV、积水/雪层、透明折射和自定义玻璃均保留缺口。普通纹理绑定使用 mesh UV0 投影，原 shader UV 计算未证明的部分有 uvMappingStatus 标记。

HDR 原数据已保留，但未强制转为普通颜色 PNG 绑定。材质父链中没有的运行时 DynamicMaterial 参数变化也未模拟。颜色与系数来自原参数，未沿用旧脚本按材料文件名填色的策略。

## 验证与复现

`material-validation.json` 记录全部文件/hash/尺寸、1970 个源指针、原几何材质引用和 ORM 契约核查；当前错误 0。未执行原游戏与 Web 同机位视觉等价测试。本项是独立原资产处理，不是 REA retained Evidence。

使用已提供的带 Pillow 的 Python 运行：

```powershell
python tools/asset-pipeline/supplement-world-materials.py
python tools/asset-pipeline/restore-world-materials.py
python tools/asset-pipeline/restore-embedded-materials.py
python tools/asset-pipeline/restore-evidenced-shaders.py
python tools/asset-pipeline/restore-evidenced-shaders-round2.py
python tools/asset-pipeline/validate-evidenced-shaders.py
python tools/asset-pipeline/validate-evidenced-shaders-round2.py
python tools/asset-pipeline/validate-world-materials.py
```

若仅更新绑定规则，可加 `--skip-export --reuse-texture-cache` 复用刚验证过且解码源 hash 不变的纹理缓存。完整恢复的源提取、工具日志与新增材料依赖均保存在 `research/world-recovery/material*`。
