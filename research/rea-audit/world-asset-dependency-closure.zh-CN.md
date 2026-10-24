# 原世界资源依赖闭包

本清单从 `world-coverage.json` 确认的 35 个地图包出发，沿其真实 Imports 引用递归检查网格、材质/实例、父材质、MaterialFunction、MaterialParameterCollection、Texture 类及 SubsurfaceProfile/RuntimeVirtualTexture 材质配置资源。**队列已收束**：当前记录 2084 个资源包，成功解析引用/属性 2084 个，失败 0 个，待处理 0 个。

这是独立 UAssetAPI 静态分析，**不是 REA retained Evidence**。Imports/属性成功解析不代表几何、纹理像素、着色器或运行行为已经恢复；没有修改 Web，没有批量导出 glTF 或图像。

## 精确种子与范围

35 地图合计包含 399 个网格对象引用、133 个材质对象引用。399 个网格均已匹配种子；133 个材质引用中 132 个是资源包，另一个 `/Script/Engine/Default__MaterialInstanceDynamic` 是原生默认对象，不能当成缺失 `.uasset`。

同时纳入地图直接引用的 Texture2D/TextureCube，避免只看网格材质而漏掉直接纹理。最终独立包种子为 640 个。每个种子都有原地图 JSON `/Imports/N` 指针；没有用文件名相似度猜测，没有把任意 Pak 素材加入闭包。

递归时仅跟随资源类型的硬引用。Blueprint、Skeleton、PhysicsAsset、PhysicalMaterial、原生 `/Script` 等非本次资源类型的 Imports 边会保留，但不继续解析。蓝图创建/动态修改的材质、仅软引用/字符串拼出的资源、运行时可见性仍不属于此闭包；这不是“所有游戏内容已逆向”的声明。

## 数量与数据文件

| 包被引用的类型 | 包数 |
|---|---:|
| Material | 173 |
| MaterialFunction | 120 |
| MaterialInstanceConstant | 339 |
| MaterialParameterCollection | 2 |
| SkeletalMesh | 11 |
| StaticMesh | 388 |
| SubsurfaceProfile | 2 |
| Texture2D | 1044 |
| TextureCube | 5 |

类型统计按每包 incomingTypes 去重，一个包若有多个入边类型可能计入多行。总包数以 processedPackages 为准。现有材质审计缓存中，仅实际从种子可达的 139 个包被复用；未把其余缓存当新种子。

- `world-asset-dependency-closure.json`：每包类型、原 uasset/uexp 的路径与 SHA-256、已有本地 ubulk 的 SHA-256、解码文件 SHA-256、各 Export 类型/原指针、RawExport、opaque Extras 大小、全部 Imports 边、失败和待处理项。
- `world-asset-dependency-seeds.json`：35 地图源文件 hash、地图→资源根边、399/133 清单交叉检查，以及地图内部资源 Export 清单。
- `world-asset-dependency-summary.json`：类型统计、失败项和引用闭包完整性校验结果。
- `world-asset-dependency-progress.json`：处理进度。每 32 个包写入检查点。
- `decoded-world-assets/` 与 `extracted-world-assets/`：本次新增解码和原包副本；既有材质缓存直接复用，记录其真实路径。

当前记录 11641 条资源包 Imports 边，其中 5741 条按本次规则递归；地图根边独立保存在 seeds 中。闭包一致性校验错误：0。

## 地图内嵌资产与未解释内容

地图内部还记录 MaterialInstanceDynamic=3299、LandscapeMaterialInstanceConstant=148、Texture2D=66 个 Export。这些对象属于地图包，不能再按它们的对象名寻找独立 `.uasset`。父材质等跨包依赖由地图 Imports 进入队列；内部地形权重/高度纹理像素仍未导出。

本次 RawExport=2，涉及 1 个包。另有 1687 个包保留超出简单尾字段的 opaque Extras。**即使 RawExport 为 0，NormalExport 仍可能只解析了头部/属性，把网格缓冲、shader 编译数据或纹理主体保留为未解释尾数据。** 本次从未将这些状态标成“几何恢复”或“shader 恢复”。

- `/Game/Character/Trooper/Mesh/Trooper_Lead`：Trooper_Lead_Clothing_2 (`/Exports/2`, ClothingAssetCommon), Trooper_Lead_Clothing_3 (`/Exports/3`, ClothingAssetCommon)

只为引用/属性分析提取 uasset 和 uexp。未专门提取 ubulk 像素/几何载荷；若已有本地 ubulk 则记录 hash，否则记录 presentInPak 和未读取原因。这种情况下不能声称拿到了该包全部像素或计算了所有载荷 hash。

## 续跑

```powershell
python research/rea-audit/trace-world-assets.py
python research/rea-audit/write-world-assets-report.py
```

支持 `--max-new-packages 128` 控制单次新增处理数，`--retry-failed` 重新排队失败项。已成功包直接读取检查点；世界清单 hash 变化时脚本拒绝混用旧闭包，需要先归档旧结果再重建。该脚本不对发布资源做写入。

下一步应结合另一条蓝图逻辑闭包检查动态资源引用，并单独恢复 mesh section/slot、纹理通道、材质着色计算、Lighting 与运行时状态；这份清单仅为这些工作建立精确可追踪的资源边界。

## 另存的六地图范围

`remaining-map-asset-seeds.json` 根据 `all-map-inventory.json` 保存了六个补充地图的精确 Imports 种子，共 205 个资源包，其中 169 个已在本轮闭包内，36 个尚未纳入。该文件包含各地图源 hash 与引用证据指针，**本轮没有从这六图继续递归，没有改变上述 35 图分母**。部分 Test 命名地图有实际玩法字节码引用，因此未将它们判为无用。后续应单独输出六图增量，区分重叠包与新包。
