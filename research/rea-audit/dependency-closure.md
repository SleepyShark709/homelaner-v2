# 项目逻辑依赖闭包静态解析

已从原审计中的78个未解析Blueprint依赖及36份既有核心解码出发，沿**序列化typed imports**递归展开。闭包收敛到306包、966条依赖边；全部边均已定位到解码节点并核验import pointer。复用36包，新增解析270包，整包失败0。

这是UAssetAPI的UE cooked资产静态解析，**不是REA证据、不是原逻辑已全部解释，更不是Web已实现**。没有修改Web代码，没有启动或修改原安装。

| 精确序列化资产类型 | 包数 |
|---|---:|
| BlueprintGeneratedClass | 140 |
| AnimBlueprintGeneratedClass | 13 |
| WidgetBlueprintGeneratedClass | 33 |
| DataTable | 39 |
| UserDefinedEnum | 49 |
| UserDefinedStruct | 28 |
| BehaviorTree | 2 |
| BlackboardData | 2 |

共186个ClassExport，1996个含ScriptBytecode的函数（含编译器包装/生成函数）。281包没有RawExport回退；另外25包保留352个RawExport，主要是UI MovieScene动画段。**0整包失败不代表所有字段已解析。** 每个包都有原uasset/uexp SHA-256、JSON SHA-256、准确类/父类身份、函数清单、原始回退和失败字段。

## 交付物

- dependency-closure.json：完整节点、typed import边、精确来源pointer、验证与局限。
- closure-seeds.json：起点精确包清单、原Pak身份、复用来源、解码工具哈希。
- closure-summary.json：类型统计、RawExport回退清单。
- decoded/：新增解析JSON，保留包相对目录避免同名覆盖。
- extracted/：仅本工作区提取副本；原Pak只读。
- native-import-anchors.json：所有306包中实际引用的 /Script/UNDEFEATED 原生身份及Exports引用位置。
- expand-logic-closure.py：可复核的提取/解析程序。

## 给REA原生分析的准确锚点

原生类：ActivitySystemLibrary、GameActivitySubsystem、UndefeatedGameInstance。函数：ActivitySystemLibrary.StartActivity、FinishActivity、GetActivityID、SetEnableActivity。另有OnActivityRequested__DelegateSignature和Default__UndefeatedGameInstance。都由Imports的Outer链确认属于 /Script/UNDEFEATED；没有把BlueprintGeneratedClass误当C++类。

StartActivity实际调用出现在BP_StoryManager /Exports/0/ScriptBytecode/124、126、131；GetActivityID位于HeroGameInstance /Exports/0/ScriptBytecode/82/AssignmentExpression；FinishActivity和SetEnableActivity的全部调用位置见JSON。仅凭这些引用不能断言Windows实现或函数作用，需REA继续找注册名、地址和xref。

## 未包含的边界

本次完成的是**项目typed hard-import闭包**，没有扫描无关联Engine资源。没有把材质/网格/贴图当逻辑依赖批量解码；soft-only/字符串动态加载、关卡LevelScript及未关联包不能因此宣称覆盖。当前导出的SoftPackageReferenceList为空，也不能证明不存在软路径或运行时字符串加载。全Pak准确类分母和完整行为解释仍需另外推进。

原逻辑审计中的“78缺口”已在此闭包层面补齐；源码近似的结论并未改变，新增JSON不会自动改善Web实现。后续应先为Player/GameMode/City/Anim每个关键行为建立CFG、调用链与数据表语义，再设计运行对照。
