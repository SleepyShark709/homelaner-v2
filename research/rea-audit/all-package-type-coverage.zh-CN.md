# 全游戏包类型覆盖

已完整解析原 `UNDEFEATED/AssetRegistry.bin` 的资产记录，并与 Pak 中所有 `.uasset/.umap` 文件进行精确包名匹配。**全部 5310 个包均由注册表 AssetClass 直接分类，unknown=0**，没有依赖文件名猜测类别，也没有逐包重新解码。

## 分母与覆盖

| 范围 | 包数 | 已分类 | unknown |
|---|---:|---:|---:|
| 项目 `.uasset` | 4792 | 4792 | 0 |
| 项目地图 `.umap` | 41 | 41 | 0 |
| Engine Content | 271 | 271 | 0 |
| Engine 插件 Content | 206 | 206 | 0 |
| 合计 | 5310 | 5310 | 0 |

项目总计是 4833 包，不能把“4792 个资源文件”和“包含地图的全项目包数”混为同一分母。原 35 地图资源闭包未修改；这里的清单覆盖全 Pak 的包类型，而非仅主世界可达范围。

注册表有 5606 条资产记录、5310 个唯一包。部分 Blueprint 包同时登记 Blueprint 和 BlueprintGeneratedClass，所以资产记录数大于包数，类型行数也不应直接相加当作独立包总数。插件包按其 Content 挂载路径生成候选包名后，逐一与注册表完整 PackageName 匹配；所有候选均精确匹配，没有只凭目录判断类型。

## 结构与证据

- 原文件：`registry-source/UNDEFEATED/AssetRegistry.bin`，2,873,860 字节。
- SHA-256：`3e72f579561f80d279a855188abb4a1f848a8280b4e26d88f6482d50173304fe`。
- GUID：717F9EE7-E9B0493A-88B39132-1B388107；版本 8，FixedTags。
- 名称表：17122 条、785852 字节字符串数据。
- Tag Store 区间：957108–2624232；begin magic=0x12345679、end magic=0x87654321。
- 5606 个资产记录均有独立文件偏移与 AssetClass FName 偏移；每条 ObjectPath 与 PackageName.AssetName 一致。
- 完整读至 2873860 字节 EOF；注册表包名集合与 Pak 包名集合精确相等。
- 与已解码记录直接同类匹配的包有 2390 个。其余包的类型来源仍是注册表明确字段，并不表示已解码。

解析使用已有 repak 与 Python 标准库；没有安装大型工具。格式依据固定提交的 [CUE4Parse AssetRegistry 版本定义](https://github.com/FabianFG/CUE4Parse/blob/460fc477bad0f9db3cfc387365a6699ee246377e/CUE4Parse/UE4/Versions/FAssetRegistryVersion.cs)、[FAssetData 字段布局](https://github.com/FabianFG/CUE4Parse/blob/460fc477bad0f9db3cfc387365a6699ee246377e/CUE4Parse/UE4/AssetRegistry/Objects/FAssetData.cs)、[FixedTags 存储结构](https://github.com/FabianFG/CUE4Parse/blob/460fc477bad0f9db3cfc387365a6699ee246377e/CUE4Parse/UE4/AssetRegistry/Objects/FStore.cs)；全部布局参考链接保存在 JSON 的 registryStructure.layoutReferences。独立读通并校验的是本游戏的版本 8 文件，脚本会拒绝其他版本。

## 项目实际类型

以下按“含此 AssetClass 的项目包”去重统计。同一 Blueprint 包可能出现在多行。

| 注册表 AssetClass | 包数 |
|---|---:|
| AnimBlueprint | 18 |
| AnimBlueprintGeneratedClass | 18 |
| AnimMontage | 103 |
| AnimSequence | 292 |
| BehaviorTree | 3 |
| BlackboardData | 2 |
| BlendSpace | 12 |
| BlendSpace1D | 8 |
| Blueprint | 209 |
| BlueprintGeneratedClass | 239 |
| DataTable | 40 |
| FileMediaSource | 21 |
| Font | 4 |
| FontFace | 4 |
| ForceFeedbackEffect | 2 |
| LandscapeLayerInfoObject | 3 |
| LevelSequence | 28 |
| MapBuildDataRegistry | 32 |
| Material | 265 |
| MaterialFunction | 80 |
| MaterialInstanceConstant | 557 |
| MaterialParameterCollection | 3 |
| MediaPlayer | 5 |
| MediaTexture | 5 |
| NiagaraSystem | 10 |
| ObjectRedirector | 1 |
| PaperSprite | 10 |
| ParticleSystem | 218 |
| PhysicalMaterial | 11 |
| PhysicsAsset | 18 |
| SkeletalMesh | 47 |
| Skeleton | 24 |
| SoundAttenuation | 3 |
| SoundClass | 7 |
| SoundCue | 200 |
| SoundMix | 3 |
| SoundWave | 337 |
| StaticMesh | 525 |
| SubsurfaceProfile | 2 |
| Texture2D | 1562 |
| TextureCube | 3 |
| TextureRenderTarget2D | 2 |
| UserDefinedEnum | 52 |
| UserDefinedStruct | 28 |
| VectorFieldStatic | 1 |
| WidgetBlueprint | 34 |
| WidgetBlueprintGeneratedClass | 34 |
| World | 41 |

例如原项目实际含 292 份 AnimSequence、103 份 AnimMontage、218 份 ParticleSystem、10 份 NiagaraSystem、337 份 SoundWave、200 份 SoundCue；这些类别以前的 35 图网格/材质闭包没有全面覆盖，后续不能继续用城市资源闭包代表全游戏。

## 交付文件与边界

- `all-package-type-coverage.json`：每个原 Pak 包、真实 AssetClass、分类来源、注册表原始记录偏移、已解码交叉验证，以及原 Pak 身份记录。
- `all-package-types.csv`：方便筛选 Blueprint、动画、FX、音频等类型的全包表。
- `asset-registry-parsed.json`：完整资产记录、结构区间与解析验证信息。
- `classify-asset-registry.py`：可复现解析器。运行 `python research/rea-audit/classify-asset-registry.py`。

**这里完成的是类型覆盖，不是全游戏实现逆向。** 本注册表的 dependencySectionBytes=4、dependencyNodes=0，packageDataCount=0：它没有提供可用依赖图或逐包磁盘大小/MD5 表。后续仍需从真实 imports、蓝图字节码、动画/特效/音频结构和运行时证据恢复实现。Tag 存储区已按结构消费并验证，但标签值语义没有完整解释，不能声称全部标签或全部依赖已解析。

原始注册表和现有 Pak 身份有 SHA-256；未逐包读取的资源不会被宣称拥有本轮新增的内容 hash。本清单没有修改 Web 或原安装文件。此项是独立二进制注册表解析，**不是 REA retained Evidence**。
