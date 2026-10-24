# 当前逻辑覆盖审计

**当前实现是“用了部分原资产、复用了部分原版参数的浏览器原型”，不是完整原版移植。** 用户感觉玩法与表现仍不像原版，有明确代码原因：控制器、AI、碰撞、镜头、特效仍大量自写。

## 资产确实被调用，但逻辑覆盖有限

| 模块 | 当前确实来自原游戏的部分 | 仍是近似或新增的部分 |
|---|---|---|
| 角色/城市/人车 | 实际加载原角色、动作、人车与原街区几何清单 | 这不等于原地图系统、材质/粒子、物理与AI已还原 |
| 移动 | walk/fly/jump/boost等少量数值对应默认或最低等级 | 5状态控制器、统一重力、线性加速度、F切飞行、台阶检测；未恢复原HeroComponent状态分支 |
| 动画 | 原片段和14段攻击的hit/finish通知时间 | HeroAnimBP状态机/BlendSpace/IK没移植；攻击前移、追敌、chain通知未执行 |
| 动作选择 | 原四拳、站立拳波、移动连招、空中踢动作被使用 | Shift直接强攻，共用连招索引；缺少原蓄冲条件和HeroPlayerState允许状态；提前输入只等finish |
| 判定 | 原普通拳半径、弹速150m/s、半径、3.5秒视觉截止、4秒寿命 | AABB近似；漏附加capsule；移动三连招共用同类弹体；统一去重与12弹上限是自写 |
| 热视线 | 200m瞄准端点、双视觉束、0.1秒间隔 | head手写眼点、统一全目标tick、E绑定、直接取消动作；无原Boss锁定/特殊动作流程 |
| 市民/车辆 | 原模型和走跑片段；道路几何来自原样条 | 6条几何路线不是原AI路线；固定速度往返、直线逃跑、无原对象池/导航/交通/车轮动力学 |
| 受击 | baseline局部市民保护/强攻击毁车有证据 | HP与伤害是明确新增设计；手写抛物线倒地、立即隐藏车辆，不是原物理/回收流程 |
| 特效/声音 | 仅概念对应 | 当前青色球拳波、圆柱激光、金色球火花是程序占位；原粒子/Cue/震屏未接入 |
| 敌人/Boss/任务/排名/存档 | 部分基础Blueprint已解码 | src没有完整对应系统；baseline也不是完整原版模式 |

每项都有代码路径、行号、快照SHA-256与对应静态证据，见 [logic-coverage.json](logic-coverage.json)。自由破坏的新增生命/伤害规则是用户批准的玩法变更，应保留“新设计”标记，不能混入原版恢复比例。

## 解析覆盖的真实分母

- Pak清单：13071条文件；项目内容中4792个uasset、41个umap。
- 现有核心逻辑解码：36份JSON，其中26个ClassExport、777个非空ScriptBytecode函数、18135个顶层AST节点。**函数数含事件包装和编译器生成函数，不代表777个行为均已理解、实现或验证。**
- 仅命名规则已找出189个逻辑候选包，25个有类解码、164个未解码。该规则会漏掉BaseEnemy等无BP命名资产，也可能误纳非Blueprint；不能作为全游戏完成率。
- 更可靠的缺口：现有解码的imports明确引用101个项目BlueprintGeneratedClass/AnimBlueprintGeneratedClass包，其中**78个尚无核心类解码**。这仍只是已知依赖图，不是全包总数。
- 全Pak准确Blueprint总量尚缺AssetRegistry或export类型全量分类；因此本报告没有编造“完成百分之多少”。全部候选、依赖来源pointer及缺失列表均在JSON。

## 下一步必须补齐的逻辑

1. 先把PlayerBP、HeroComponent、HeroAnimBP按输入→状态→动作→通知→恢复链完整核实，再替换自写控制流程，不能只搬几个速度。
2. 补移动三连招各自的BP_LongAttack_BackHandSlash/FlashKick/Smash，以及冲刺、重击、冲击波等判定类；当前共用拳波不够。
3. 补市民/车辆对象池、spawn/waypoint、EscapePoint、FuncLib_CitizenSystem、SplineHelper、SYS_CollisionLibrary，恢复实际AI与交通。
4. 补Gang_AIController、敌方攻击和Boss子类；补HeroGameState、BaseQuest_BP、BPFL_HeroPoint、BPFL_Story、存档、教程/HUD。
5. 全包准确分类后建立每个系统“已解码→已解释→已实现→原版运行对照”的独立状态，不能用导出数量代替逻辑覆盖。

## REA边界

本审计复用的是 **UAssetGUI/UAssetAPI对cooked Blueprint的静态解码**，以及源码阅读；不属于REA原生反编译证据，未产出REA工具调用ID。REA原生工具连接由父代理单独核实。没有启动原游戏，也没有原版运行时行为验证；浏览器能跑、测试通过、原资产已导入，都不能证明与原游戏等价。


后续静态解析更新：原78个依赖解码缺口已递归补齐至306包/186类/966条typed边，详见[依赖闭包报告](dependency-closure.md)。以上36包/26类统计保留为初始审计快照。Web未改，逻辑实现近似与未验证运行时的结论不变。
