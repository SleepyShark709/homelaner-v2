# 地图内嵌材质与透明度补项

本次修复使用原地图的已解码属性和引用，不重新导出原纹理，不修改原安装或几何 glTF。独立资源处理结果不称为 REA retained Evidence。

## 缺口原因

原 35 图的 4,352 个非空 OverrideMaterials 槽中，3,306 个属于 1,208 个没有显式 Mesh 属性的组件，其中 3,298 个引用地图内嵌 MID。之前几何导出遗漏的是整个需要 Blueprint/TemplateIndex 默认网格的组件，并非把已导出组件的正引用材质转成 null。几何恢复由独立管线处理；新增材质描述本身不会使缺失组件出现。

## 实际输出

`material-manifest.json` 的 materials 字典包括 605 个跨包材质（原 537 个，加模板组件新增网格、挂点组件及其父材质依赖），以及 3,616 个地图内嵌材质实例：3,468 个 MaterialInstanceDynamic、148 个 LandscapeMaterialInstanceConstant，总计 4,221 个描述。所有 Parent 均有描述，没有未解析父材质。

稳定键为 `mapPackage#export:UE_1_based_export_index`。source 保存地图路径、SHA256、原 export 指针；embeddedInstance 保留 objectPath、parentReferenceIndex、resolvedParent、全部局部参数及其原关联信息、剩余序列化属性。完整原槽位保存在 instanceOverrides，正索引不再只有无法直接消费的短名称。

范围分开计数：原 35 图有 4,352 个非空槽，其中内嵌 3,298；新增 6 图有 194 个非空槽，其中内嵌 168。41 图总共 4,546 个非空槽、3,466 个内嵌槽，全部有材质描述。补图不代表运行时一定加载，不能把该计数当作主世界同时可见数量。

保留 554 条原实例局部参数，每条均给出 source pointer、projectionUses 和 status。7 条进入当前明确的 PBR 投影（Color 5、EmissiveColor 2）；547 条列为 retained-not-mapped。其中 491 条是地形 LayerMask/Weightmap/Heightmap，56 条是水面或天空特殊参数。这些数据没有被删除或假装是普通 PBR 参数。大多数 MID 仅继承 Parent，没有额外局部参数。

## 透明度约定

16 个已有明确 opacity 单通道绑定的材质新增 packedOpacity，共复用 4 张派生 PNG。RGB 固定为白色，Alpha 是原选择通道 R；若原 RGB 图为 SRGB，先按 SRGB 传递函数线性化，再按最近整数写入 8-bit Alpha。没有使用 RGB 亮度近似替代原 R，源纹理与 channels.opacity 身份不变。

packedOpacity 字段为 colorSpace=linear、channel=a、scalarFactorsAlreadyApplied=false；因此运行时仍应用 factors.opacity。证据包含源通道描述、源图片 SHA256、转换操作与量化误差上界 0.5/255。ORM 的 scalarFactorsAlreadyApplied=true 保持不变，两个派生数据约定不要混淆。

验证脚本检查派生 Alpha 每个像素与源采样转换完全一致，同时验证 RGB 为白色、文件/hash/尺寸和来源指针。此验证不等价于原游戏 shader 或同机位截图完全匹配。

## 复现

使用带 Pillow 的 Python，按顺序运行：

```powershell
python tools/asset-pipeline/supplement-world-materials.py
python tools/asset-pipeline/restore-world-materials.py --skip-export --reuse-texture-cache
python tools/asset-pipeline/restore-embedded-materials.py
python tools/asset-pipeline/validate-world-materials.py
```

若引入新纹理，第二步应去掉 --skip-export。只重建 base 材质的脚本会重新写 manifest，必须继续运行内嵌实例步骤。补充依赖脚本排除 #export 内嵌键，并要求精确 Pak 路径存在，防止把内嵌标识当作独立包提取。

`material-embedded-instances.json` 保存逐地图统计与每个原实例；`material-validation.json` 保存针对当时 geometry-manifest 的最终核验。序列化参数快照不代表运行时参数变化已模拟，地形混合、水、天空和自定义 shader 的缺口仍保留。
