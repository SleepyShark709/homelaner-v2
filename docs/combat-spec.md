# 原版战斗最小行为规格

本规格用于后续 Babylon.js 实现，不表示战斗已在浏览器运行。来源是旧工作区 cooked Blueprint 的 Kismet、类/组件默认值、数据表，以及本项目已导出的实际 Montage/AnimSequence。没有启动原游戏。完整来源 SHA-256、JSON pointer、17项结论和14段动画位于 [combat-spec.json](../research/evidence/combat-spec.json)。动画来源见 [导出清单](../research/exports/combat-animations/manifest.json)。

## 实现顺序与证据等级

先完成原角色移动街区，再接入战斗层。保留原骨架/动作；祖国人换皮另行处理。recovered_control_flow 是已解析字节码路径，serialized_defaults 是可能被运行时覆盖的序列化值，推导播放时间属于 inference，自由破坏策略属于用户批准的新设计。未给出的伤害数值不可填成“原版参数”。

## 输入和动作选择

- 普通攻击：进入 Attacking(2)，四段 Hero_Attack1/2/3/4_Montage 循环；入口重置冲刺、选最近敌人并重置连招计数。
- 右键保留 FistCannon → LongRangeAttack：地面静止左右拳波交替；地面移动为 BackHandSlash → FlashKick → Smash；满足 SuperPunchCounter≥1 且 IsDeathblowEnable 时可转超级拳；空中左右踢，Direction∈[-20°,20°]且上述条件成立可转 AirSuperKick。命中反应状态是原阻断条件之一。
- 新增按住 E 热视线；需另行确定原 E 上升键替代。不要拿热视线覆盖原右键。

相关状态：6 FistCannon、11 ChainLongAttack、12 LongRangeAttacking、14 SuperLongAttackPunch、15 AirLongRangeAttacking、16 AirLongRangeAttackChain、17 AirSuperKicking。完整 Boss 连段不在本次最小规格范围。

## 实际动作与命中时间

下表是 **AnimSequence 源时间**，不是固定现实秒数。序列均使用 /Game/Action_Male/Meshes/SKEL_Male 骨架。全部 Montage 位于 /Game/-HeroGame/Player/Animations/。普通四拳的实际序列位于 /Game/Animations/，其余位于 /Game/-HeroGame/Player/Animations/。

| Montage（省略 Hero_ 与 _Montage） | 实际序列 | 主要通知与源时间（秒） | Montage 播放速率 |
|---|---|---|---|
| Attack1 | Hero_Attack1 | StopAttackMove 0.4250；FinishAction 0.9003 | AttackAnimRate |
| Attack2 | Hero_Attack2 | StopAttackMove 0.4500；FinishAction 0.8992 | AttackAnimRate |
| Attack3 | Hero_Attack3 | StopAttackMove 0.4354；FinishAction 0.9003 | AttackAnimRate |
| Attack4 | Hero_Attack4 | StopAttackMove 0.4313；FinishAction 0.9010 | AttackAnimRate |
| LongLAttack | Hero_LongFistForce_L | NormalLongAttack 0.4165；FinishLongAttack 1.1022 | AttackAnimRate × 等级倍率 |
| LongRAttack | Hero_LongFistForce_R | NormalLongAttack 0.4186；FinishLongAttack 1.0980 | AttackAnimRate × 等级倍率 |
| BackHandSlash | Hero_BackHandSlash_New | SpawnComboLongAttack 0.4354；ChainComboLongAttack 0.4565；FinishAction 1.0034 | AttackAnimRate |
| FlashKick | Hero_FlashKick | SpawnComboLongAttack 0.4994；ChainComboLongAttack 0.6528；FinishAction 1.1497 | AttackAnimRate × 1.2 |
| Smash | Hero_Smash_A | SpawnComboLongAttack 0.6711；ChainComboLongAttack 0.8666；FinishAction 1.3000 | AttackAnimRate |
| SuperPunch | Hero_SuperPunch | SpawnSuperLongAttack 0.8701；FinishAction 1.8973 | 0.75 |
| AirKick_L | Hero_AirKick_L | SpawnAirLongAttack 0.4319；ChainAirLongAttack 0.5026；FinishAction 1.1007 | AttackAnimRate × 等级倍率 |
| AirKick_R | Hero_AirKick_R | SpawnAirLongAttack 0.4989；ChainAirLongAttack 0.5536；FinishAction 1.1346 | AttackAnimRate × 等级倍率 |
| AirSuperKick | Hero_AirSuperKick | SpawnSuperLongAttack 0.6547；ChainAirLongAttack 0.9512；FinishAction 1.9016 | 1 |
| AirAttackStart | Hero_AirAttackStart | StartAirAttack 0.5224 | AttackAnimRate |

普通四拳的 **StopAttackMove 就是命中触发**：AnimNotify_StopAttackMove → StopAttackMoveEvent → SpawnAttackCollisionEvent → BP_AttackCollirionNormal。不能只寻找 SpawnNormalAttackCollision 同名通知。StartAttackMove 控制前移；通知与命中独立于输入按下时刻。

AttackAnimRate 默认1。站立拳波/空中左右踢的等级倍率为 [1,1.12,1.14,1.16,1.18,1.20,1.22]。FlashKick 另乘1.2，SuperPunch固定0.75。超级拳源命中0.8701秒，按0.75播放约1.1602秒；这属于播放时间推导，仍需验证中断/混合/队列效果。

**避免二次加速**：普通四拳原 AnimSequence 长1.8333秒、RateScale≈1.1，而导出的 PSA nominal≈1.6667秒已经体现该加速。若按 PSA 时间播放，通知时间先除1.1；不要再次把整个 PSA 乘1.1。四拳对应推导命中约0.3864/0.4091/0.3958/0.3920秒。其他片段未序列化 RateScale 时按引擎默认1处理是明确假设。完整通知（含移动/脚步/衔接）保存在 JSON。

## 判定和目标响应

| 层 | 已恢复参数/行为 | 实现边界 |
|---|---|---|
| 普通近战 | AttackLocation 模板相对(95,0,30) UE单位；生成位置碰撞体；寿命0.1秒；弱 ImpactForce | 补证已确认主Sphere静态继承半径256、spawn scale1；SphereRadius变量160未见读取，RadialForce255另属物理冲量 |
| 普通近战物理 | RadialForce ImpulseStrength=400 | 不是伤害值，也不能当作米/秒直接拷贝 |
| 普通拳波 | BP_NormalLongAttackCollirion 从 AttackLocation 世界变换生成；通知后转衔接状态 | 补证：速度15000 UE/s，寿命4s，主Sphere256；范围仅可推导无遮挡上界，见下文 |
| 超级拳/踢 | BP_SuperPunch / BP_SuperKick；空中普通远攻 BP_AirLongAttack_Kick | 补证见下文；镜头抖动、下方450单位地表trace不是攻击范围 |
| 热视线 | 单条 LineTraceSingle；通道字节7；非complex；忽略玩家；摄像机位置+forward×20000为瞄准端点 | 两只眼睛是两条视觉 beam，共享一次判定；20000不是严格眼部最大射程 |
| 热视线锁定 | Boss位置+up×60 | 保留目标偏移，再决定是否扩大到自由破坏目标 |
| 热视线连续Pawn | HitInterval=0.1秒；新目标进入命中路径，连续同目标按delta计数 | 原非Pawn分支没有此节流；不可宣称全类型统一10Hz |
| 车辆 | IsStrong=false仅火花/音效；true且未摧毁→爆炸/隐藏→1秒后从车辆池移除 | 原近战弱接口/热视线弱接口不能直接等同车辆破坏；自由模式需新规则 |
| 市民 | BPI_Citizen状态、寻路/逃跑；默认忽略Hero/Bullet/OpticRay，未见该类HP或PlayerImpact_BPI | 热视线虽尝试SetCitizenState(4)，并不证明原版能命中或杀死；状态4语义未恢复 |
| 普通敌人 | ImpactForce.IsStrong传给HitAttack.IsAirAttack；存在ragdoll和LaunchCharacter | 某击飞分支XY=玩家forward×2048×随机[1,2]，Z加1280；不等于通用伤害或Boss伤害 |

以上空间参数保留 UE 原值；在本项目的坐标尺度确认后统一转换。物理冲量不能只用100:1长度换算，应按目标物理实现校准。接口以标志驱动，并未发现可直接复制的通用“拳=多少HP、热视线=多少DPS”。

## 原限制及自由模式差异

连招超时不是攻击冷却：AttackIndexInterval默认1.5会被运行分支改成一般1秒、空中远攻0.5秒，然后将AttackIndex/LongAttackComboIndex/AirLongAttackIndex归零。是否在具体动画/状态窗口累计，还需按完整入口调度验证。

原OpticRay特殊动作数据表为cool=5秒、usable=600秒、loop=true。使用时ActionCoolTime累加到上限后EndActiveOpticRayEvent，非使用时以默认倍率1衰减；ActionUsableTime另按delta递减到负值结束特殊动作。默认10秒字段是触发区域累计条件，不能写成“每次热视线蓄力10秒”。原版车辆摧毁且非敌方攻击调用SendHeroPoint；表有Vehicle=-2000，但本次没解码helper来闭合行选择链。

用户批准的自由破坏模式应新建统一受击能力，使市民、车辆、指定道具都能响应；取消玩家伤害、负分、降级、被迫失控、技能资源限制和强制失败。**这些是新设计，不是原版恢复结果。** 可保留原动作起手、通知、衔接门来还原手感。若对所有目标采用0.1秒热视线tick，也需明确它是新的统一策略。

## 可验收的最小实现

1. 14段动作与原骨架播放，源通知按缩放后的时间派发，避免PSA重复加速。
2. 每次有效命中事件为每个目标只派发一次近战效果，碰撞体按寿命回收；跨帧重复overlap不会重复摧毁。
3. 右键动作分支与按住E独立工作，松开E立即停止判定；墙体挡住射线，双眼beam汇聚同一命中点。
4. 原版限制与自由模式配置分离；自由模式市民/车辆确实可受击且不扣分、不降级、不强制失败。
5. 车辆爆炸只触发一次并安全退出交通/对象池；目标已回收时不继续派发命中。

尚待补证：Normal/SuperPunch原生Capsule尺寸、市民状态4枚举语义、Boss血量伤害，以及原版运行时视觉/时序比较。远程类速度/寿命/强弱标志和普通近战静态继承半径现已补齐；仍不能宣称完整战斗数值与物理已实测还原。


## 远程判定补证（2026-10-24）

来源：[combat-projectile-supplement.json](../research/evidence/combat-projectile-supplement.json)，包含源哈希、逐项JSON pointer和中断契约。四类解码原文保留在 research/evidence/combat-decoded/，安装目录未写入、未启动。

四类ProjectileMovement都继承 InitialSpeed=MaxSpeed=15000 UE单位/秒、ProjectileGravityScale=0、InitialLifeSpan=4秒。按本项目确认的100 UE单位=1米换算时为150米/秒。bIsHomingProjectile=true、HomingAccelerationMagnitude=1虽已序列化，但四类未见HomingTargetComponent赋值；不能据此新增自动追踪。SetInitialVelocity把局部X强制15000、保留输入Y/Z，再受MaxSpeed约束。

| 判定类 | 主Sphere半径UE | 附加Capsule半高/半径UE | IsStrong / IsSlash / IsLongRange | 前向环境检测半径UE |
|---|---:|---|---|---:|
| BP_NormalLongAttackCollirion | 256 | 原生默认未证实 | false / false / true | 100 |
| BP_SuperPunch | 1500 | 原生默认未证实 | true / false / true | 100 |
| BP_SuperKick | 500 | 2000 / 350，Roll100° | true / true / true | 100 |
| BP_AirLongAttack_Kick | 256 | 500 / 97.1515，Roll约-90° | false / true / true | 64 |

SuperPunch/SuperKick虽CDO写IsLongRange=false，BeginPlay的Initialize又明确设为true；必须使用初始化后的值。普通类IsStrong/IsSlash未序列化，false来自零初始化默认的静态推导。子类Sphere1虽另有半径覆盖，却继承bGenerateOverlapEvents=false，不要额外作为独立伤害球。

生命周期细节：

- BeginPlay延迟3.5秒只设IsHit并关闭MainEffect，**没有停止运动/关闭碰撞**；OverlapFunc也不检查IsHit。因此3.5秒不是已证明的硬伤害TTL。
- 4秒actor寿命与15000速度给出60000 UE的无遮挡理论路程上界。3.5秒视觉截止约52500 UE。二者都不是实测命中距离，障碍物会提前停止。225000000平方距离检查限制的是地面裂纹贴花。
- 前向环境SphereTrace长度300 UE、通道0，识别water/ocean或floor/building后停止ProjectileMovement、设IsHit、关闭Sphere/Sphere1/Capsule并关闭特效。
- 普通目标overlap只派发ImpactForce，不自动吃掉整个弹体；不要实现成“命中任意敌人立即销毁”后称其原样移植。
- Sphere父回调使用OverlapActors去重；Capsule仅比较上一个OverlapActor。统一Set去重属于合理的新实现简化，但原代码允许Capsule A→B→A重复A。

普通近战半径现可静态确认256 UE：BP_AttackCollirionNormal只覆盖Sphere1/Box/RadialForce，前两者NoCollision；主Sphere继承父类256，两个类均无ConstructionScript或SetSphereRadius，Hero生成时scale=(1,1,1)。160是未见读取的actor变量。此结论仍是静态恢复，没有运行实测。

## 可直接实现的最小选择与中断规范

右键入口先检查GetIsHitReaction。非Boss最小状态选择：

| 当前HeroPlayerState | 接受行为 |
|---|---|
| 0 CanMove | MovementMode1/2：无移动输入→普通左右拳波；有移动输入且counter≥1→超级拳（deathblow未开回落移动连招）；否则移动三连招。Mode5→空中远攻 |
| 9 ChainAttack | Mode1→移动连招；Mode5→空中远攻 |
| 10 Sliding | IsDeathblowEnable时超级拳 |
| 11 ChainLongAttack | 普通左右拳波 |
| 16 AirLongRangeAttackChain | 空中远攻 |
| 其他非Boss状态 | 此入口返回，不应每次点击重启当前起手动作 |

原21/24/26还有Boss特定路径，不应简单当idle。此表是已恢复控制流的非Boss子集，不是完整战斗状态机。

以下是供浏览器实现的**最小中断契约**，未冒充已完整恢复原中断矩阵：

1. 每次动作拥有generation/token；被合法新动作、场景释放或显式取消替换时，取消旧动作尚未触发的命中/移动/衔接事件。已发射弹体沿自己的寿命继续。
2. 按动画时间跨过notify的瞬间触发一次；低帧率跨过多个notify按时间顺序补发，避免重复或漏发。不得在按键按下时立即代替notify命中。
3. 不在任意状态允许点击重开起手。仅在上表接受状态/恢复后的chain gate接受下一次动作；更早的输入缓存行为未证实。
4. FinishAction/FinishLongAttack负责恢复动作/移动状态，不能拿整段动画长度当统一攻击冷却。
5. 新增E热视线独立按住控制；释放E、窗口失焦、场景dispose立即停beam和hit tick。自由模式不引入受伤强制打断。
6. 原脚本存在0/0.15/0.2/0.25秒Montage_Stop，但本时限未恢复每个触发原因，不能推成统一取消窗口。上面的token清理是实现正确性的要求，不是原版可随时取消攻击的证据。
