# 原版世界恢复执行记录

项目：`E:/undefeated-web`。默认入口：`http://127.0.0.1:5178/`。

用户要求完整 REA 逆向与原版还原。本次把默认入口从小范围玩法原型切换为原世界恢复检查，先解决原资产没有完整进入 Web 的问题。此文记录已完成的资产管线与浏览器接入，不代表整个游戏移植完成。

## 原资产如何进入 Web

- 地图：解码 41 份地图，区分 35 份主世界依赖与 6 份补充地图。主世界“全部区域”只是静态检查组合，不等同于原游戏运行时同时加载这些区域。
- 网格：沿关卡直接引用和蓝图 TemplateIndex/Archetype 原引用恢复模型、变换、可见性和材质槽。模板默认值不代表已经执行 Construction Script 或 BeginPlay。
- 道路：按原 SplineMesh 参数烘焙，保留来源组件；同模型、同材质的道路按空间范围合批。实例组件按原实例矩阵恢复，不能用组件数代替实例数。
- 材质：原纹理按完整 UE 包路径保存，区分 sRGB/线性、原网格材质槽和地图内嵌动态实例。可证实的 PBR 通道才接入；未知 shader 参数保留，不凭名称猜测。原 DirectX 法线绿色通道与源 BC5 块核对，透明度 R 通道派生为 Alpha 后使用。
- 地形：144 块原 Landscape，高度来自原高度图 RG 16 位数据。保留完整高度场，默认每 4 格采样、高清每 2 格采样；原顶点样本准确，采样间的三角面仍有近似误差。完整高度数据不是原 PhysX 碰撞的重建。
- 地表：草地、泥地、沙地的贴图、色彩因子、权重与 UV 公式由原实例、冻结 uniform 表、DXBC 和序列化布局共同核对。Web 使用已证实的颜色与法线混合，并从原高度图 BA 重建地形切线基；照明单独标为预览。

## 实现与证据边界

当前静态管线计数：476 个源网格导出为 688 份运行几何（含道路烘焙批次），共 9,861 条渲染对象记录。41 图中已识别的 11,359 个源 mesh 组件全部表示；46 个骨骼附件已按原 socket、父骨骼和参考姿态矩阵补齐。此计数不包含尚未解出的 TestLevel 原生 foliage 载荷，也不代表所有运行时生成对象。实例展开和道路合批会改变运行对象数量，因此这些分母不能混用。

4,221 个材质描述中包含 3,616 个地图内嵌实例；1,155 张 PNG 和 3 张 HDR 已导出。引用闭合不等于效果完全还原：2,078 个描述（含继承的 MID）仍标为 shader-unmapped。本轮解出 5 个 SkeletalMesh 的 42 个原生渲染分段材质索引，消除 29 处骨骼槽歧义及 42 处 component-section 覆写冲突。原 6,684 个 override 槽已逐槽核查，含 4,546 个非空引用，没有压缩槽号或丢弃正向导出索引。

新增 20 份有原编译 shader 依据的材质计算：17 份世界坐标三向投影、2 份植被顶点遮罩、1 份长椅 PBR。恢复原负向世界平铺尺度、颜色/法线混合、粗糙度通道及色彩空间；725 组独立数值检查通过。植被原网格和组件载荷没有顶点色覆写，默认白色有源证据。当前照明仍是 Babylon 预览；植被双面次表面散射、风动、原 LOD 抖动及完整原后处理未实现。数值合同通过不等于 Web 最终画面与 UE 像素等价。

根据原 Kismet 跳转地址、latent 回调及关卡标志，默认入口改为 17 份启动城市关卡的静态组合：MainLevel、4 份 AlwaysLoaded、12 次启动请求。挑战、剧情和 Boss 条件关卡不混入基线；实际运行时开关和触发器执行尚未接入。静态材质合批仅共享渲染定义完全一致且没有自有参数/未知属性的空 MID，3,454 条实例可归并，源身份保留。后续动态改参必须独立实例化。

静态检查中的骨骼模型使用源参考姿态，软件蒙皮一次后合批；源骨骼和动画资产不变。这是查看器的性能处理，不是原动画状态机重建。

REA/Ghidra 对原 Shipping EXE 的函数、交叉引用和反编译结果位于 `research/rea-audit/native-*`。UAssetAPI/UModel 的包解码、几何/纹理导出以及 DXBC 分析是独立证据来源，不冒称 REA 反编译成果。Web 代码是依据这些证据编写的转换与渲染实现。

原引擎运行逻辑不能由“导出成功”推出。当前仍缺：完整角色/动画状态机与碰撞、原 AI/敌人/Boss、任务事件及流程、原运行时关卡开关与构造脚本、原天空/光照/后处理、复杂水面和部分材质、动画驱动的附件跟随，以及与原程序同机位/同操作的对照。原程序已实测启动菜单和进入城市，见 runtime-observation；这仍不是行为等价验收。

旧原型 `/?view=prototype` 中的近似控制、热视线和自由破坏继续保留为历史工作，不混入当前原版还原验收。角色/动画检查在 `/?view=assets`。祖国人换模仍后置。

## 可复现文件

| 内容 | 位置 |
|---|---|
| 默认页面与场景装配 | `src/world.ts`, `src/world/OriginalWorld.ts` |
| 原材质通道接入 | `src/world/OriginalMaterials.ts` |
| 原编译材质计算 / 静态材质共享 | `src/world/RecoveredShaderPlugin.ts`, `src/world/material-identity.ts` |
| shader 恢复与数值证据 | `tools/asset-pipeline/restore-evidenced-shaders.py`, `research/world-recovery/material-shader-recovery/report.zh-CN.md` |
| 原启动与条件流送证据 | `research/streaming-contract.md`, `public/assets/world/streaming-manifest.json` |
| 挂点 / 骨骼材质分段 | `research/world-recovery/geometry-socket-resolution.json`, `geometry-override-validation.json` |
| 原程序运行观察 | `research/runtime-observation/report.zh-CN.txt` |
| 地表原混合计算与预览照明 | `src/world/terrain-material.ts` |
| 几何导出 | `tools/asset-pipeline/export-world.py` |
| 材质恢复与验证 | `tools/asset-pipeline/restore-world-materials.py`, `validate-world-materials.py` |
| 地形恢复 | `tools/asset-pipeline/restore-world-terrain.py` |
| 原地图/模型/材质/地形合同 | `public/assets/world/*manifest.json` |
| 几何覆盖与明确缺口 | `research/world-recovery/geometry-summary.json`, `geometry-gaps.json` |
| 逐资源来源和转换核查 | `research/world-recovery/geometry-validation.json`, `material-validation.json`, `terrain-validation.json` |
| 地形 shader 证据 | `research/world-recovery/landscape-material-contract.json` |
| Web 集成检查 | `research/world-recovery/runtime-asset-validation.json` |

原/派生二进制资产保留在本机并排除 Git。原游戏安装保持只读，未发布或上传原资源。

## 验证方式

`npm run test:world` 检查 UE 材质槽与 glTF 材质索引的映射、空覆写继承、重复槽歧义、内嵌 MID 标识和源对象计数。`npm run verify:world` 检查已发布的本地资源闭合、GLB/glTF buffer、变换、材质引用和原点合同。`npm run build` 检查 TypeScript 并生成生产构建。

浏览器需实际切换城区与全城、检查地形精度切换和资源错误；结果另记于 `research/world-recovery/browser-validation.json`。这些检查证明当前资源能装配和渲染，不证明原版行为或画面完全等价。


## 首轮浏览器结果（历史，未包含本轮修复）

市中心加主世界道路装配 4,268 个可见源对象；公园加主世界装配 4,099 个，均有144块地形，模型/纹理加载失败为0。公园高清地形开/关成功，原地表颜色与法线shader正常编译。

全部35主世界地图静态合并实际装配11,003个可见源对象，资源加载失败0，主世界28处骨骼材质槽冲突按预期灰色提示。全城观测约4 FPS，市中心/公园观测约12–36 FPS（含高清），均为本机单点读数，不是稳定帧率承诺；全城模式尚不具备可玩游戏的性能。已增加加载期间暂停渲染和分批卸载，接下来需要按原运行逻辑恢复流送、可见性和LOD。

以上是首轮记录，不覆盖随后修复的挂点和材质槽。本轮验证另见 `research/world-recovery/browser-validation-pass2.json`：在 1280×720 视口下检查启动城市、公园高清地形与 Boss 场景，以及区域切换。不同视口、场景组合和相机位置的 FPS 不能直接比较，也不是稳定帧率承诺。当前启动城市全景约 15 FPS，仍需优化。

后续重点：继续复杂材质、原天空/光照与同机位画面对照；把已解释的关卡加载链、角色状态和动画接入运行时，再处理 AI/事件。祖国人外观及新增玩法仍后置。

材质重建顺序：supplement → restore-world-materials → restore-embedded → restore-evidenced-shaders → validate。最后一步 shader 恢复不可省略，避免旧通道覆盖本轮证据结果。
