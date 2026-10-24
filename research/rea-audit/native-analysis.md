# REA 原生分析实证

本报告对应真实 REA 6.7.0 MCP 调用和 Ghidra 12.1.4 返回结果，不使用 UAssetAPI/UModel 输出冒充 REA Evidence。原EXE SHA-256 为 `0790a47508668dafb64f097c855745abd91a8ff027c8c6b5b0766db2d01669ef`。

## 成功范围与限制

默认自动分析在30分钟期限后返回 `provider_timeout`。随后使用8G堆、60分钟期限，并关闭 `Function ID`、`Windows x86 PE RTTI Analyzer`、`Stack`、`x86 Constant Reference Analyzer` 四项分析器，完成初始查询。这个限定配置必须随证据保留，不能描述成完整默认分析。

REA inventory列出158,215个函数条目、85,121个已定义字符串、11个内存段。它只覆盖当前Ghidra发现的条目，不证明所有函数均已识别，更不证明它们已被理解。原PDB没有成功加载证据；类型和函数名仍大量缺失。

完整函数汇编、伪代码、直接调用和间接调用缺口见 [native-analysis.json](native-analysis.json)、[native-functions](native-functions/) 与 [REA Evidence bundle](native-evidence-expanded.json)。该bundle导出返回的 `unknowns=0` 是证据存储记录统计，绝不是游戏没有未知行为。

当前实际逐函数分析10个地址：四个Activity接口包装、四个对应实现、GameActivitySubsystem类查询和StartActivity子系统分派。其他清单函数不计为已分析完成。

## 已连通的蓝图到原生路径

UE专用解析在 `BP_StoryManager` 中定位到 `ActivitySystemLibrary.StartActivity` 调用；原生注册表内存区 `0x1438e8b30` 的64字节由REA `read_bytes` 实际读取。将其与原文件字符串对照，得到如下函数入口配对：

| 接口 | 原生包装入口 |
|---|---|
| FinishActivity | `0x140ea9b00` |
| GetActivityID | `0x140ea9bc0` |
| SetEnableActivity | `0x140ea9cc0` |
| StartActivity | `0x140ea9d80` |

这是一条静态调用关系，不是实际运行轨迹：

1. `StartActivity` 包装入口读取调用参数，调用 `0x140ea82c0`。
2. `0x140ea82c0` 包含多个上下文/对象为空即返回的分支；获取 `GameActivitySubsystem` 类并尝试查找子系统后，调用活动ID映射函数 `0x140ea7680`，成功时调用 `0x140ea9220`。
3. `0x140eaa020` 的反编译中明确出现 `/Script/UNDEFEATED` 与 `GameActivitySubsystem`，将类查询地址与游戏自定义类联系起来。
4. `0x140ea9220` 引用 `OnlineSubsystem` 并经若干虚函数指针分派。最终后端、实际调用结果及失败时机仍需运行时证据，当前不能替其补写猜测行为。

`GetActivityID` 包装入口调用同一 `0x140ea7680`，将结果写回。该函数的静态反编译及汇编支持以下字节值到字符串的映射：

| 值 | 字符串 |
|---|---|
| 0 | `UNDEFEATED_SubTask1` |
| 1 | `UNDEFEATED_SubTask2` |
| 2 | `UNDEFEATED_SubTask3` |
| 3 | `UNDEFEATED_SubTask4` |
| 4 | `UNDEFEATED_MainActivity` |

查找未命中返回0，命中复制对应字符串并返回1。这是从反编译推导的语义，尚未执行验证。不能据此把四个SubTask直接命名为某个具体战斗/剧情任务，也不能将这个接口当成热视线或角色移动逻辑。

`FinishActivity` 包装调用 `0x140ea7580`，同样检查上下文并使用ID映射，之后转到 `0x140ea8710`；这个后续分派地址尚未单独解释。`SetEnableActivity` 包装调用 `0x140ea7da0`，构建同一组五个活动ID并遍历调用 `0x140ea8fc0`，传递启用标志；其后端实现也尚未核实。这两项保留为明确的后续缺口。

## 尚未完成

- EXE其他项目函数及引擎函数尚未全面解释；当前函数样本和证据ID逐项列在JSON中。
- 蓝图2489份非空函数AST可读，不等于全部状态/事件链已经解释。
- 原版游戏未启动，本轮没有原版运行画面、输入序列或虚调用目标观察。
- Web没有接入本轮新增分析结果；旧网页的近似控制、场景和材质缺口仍存在。
- 伪代码是分析器推导结果，不是原开发者源码；原开发工程没有恢复。

当前REA会话保留供后续针对性核查，状态见 `session-focused/status.json`。Windows P0的数据库是临时的；关闭会话会删除数据库，已导出的Evidence与汇编/伪代码文件仍保留。
