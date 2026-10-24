# Player 状态与移动验收合同

本轮只读恢复 PlayerBP → HeroComponent → HeroAnimBP 关键链。证据是 cooked UE 包的 UAssetAPI/Kismet 静态解析，不是 REA 原生反编译证据，也未启动游戏。逐条 statement、SHA256、完整指针见 [player-state-contract.json](./player-state-contract.json)。

源别名 P=PlayerBP、H=HeroComponent、A=HeroAnimBP；下列指针相对于同名源 JSON。

| 默认操作 | 按键 |
|---|---|
|前后/左右|W/S、A/D|
|跳跃/空中开关飞行|Space|
|升降/地面蓄升|E/Q；按住 E|
|冲刺|LeftShift|
|慢行|LeftAlt|
|互动|F|

HeroPlayerState 与 MovementMode 正交，普通飞行仍可处于 CanMove0。原状态如下；仅列标签的状态不代表其全部行为已恢复。

| 值 | 原显示名 |
|---|---|
|0|CanMove|
|1|CantMove|
|2|Attacking|
|3|AirAttacking|
|4|AirAttackingStrong|
|5|DashAttacking|
|6|FistCannon|
|7|Action|
|8|AirAttackCharge|
|9|ChainAttack|
|10|Sliding|
|11|ChainLongAttack|
|12|LongRangeAttacking|
|13|LongAttackSmashDown|
|14|SuperLongAttackPunch|
|15|AirLongRangeAttacking|
|16|AirLongRangeAttackChain|
|17|AirSuperKicking|
|18|NewDashAttacking|
|19|DashAttackCharge|
|20|BossAttacking|
|21|BossAttackChain|
|22|BossBlowingAttack|
|23|BossBlowingAttackSecond|
|24|BossBlowingAttackChain|
|25|SmashBossHeavyAttack|
|26|ChainSmashBossHeavyAttack|
|27|Lose|
|28|sentinel|

枚举依据 E_HeroPlayerState /Exports/0/Enum/Names 和 /Exports/0/Data/0。FallingSpeedType：0=None、1=LowSpeed、2=HighSpeed、3=UltraSpeed、4=哨兵；同样位置的原枚举证据见 JSON。

## P01 原按键与FKey入口

默认W/S前后、A/D左右、E/Q升降、Space Jump、LeftShift Sprint、LeftAlt WalkMode；F为Interact。PlayerBP输入wrapper保存FKey参数后转发相应事件，移动调用不按该Key再分支。存档改键不在本证据内。

验收：原版还原模式的F不能直接切飞行。按键配置与事件转发分别验收。

证据：P /Exports/18/ScriptBytecode/0；P /Exports/18/ScriptBytecode/1；P /Exports/0/ScriptBytecode/397；P /Exports/0/ScriptBytecode/398。完整逐条证据见 JSON 同 ID。

## P02 状态和物理模式正交

SetHeroPlayerState只赋值，不自动调SetMovementParam或换MovementMode。普通飞行用MovementMode5，HeroPlayerState仍可为0。IsSprint、SprintBtnPressed、IsSprinted、WalkMode也是独立量。

验收：不能把Flying写成一个替代CanMove的HeroPlayerState。

证据：H /Exports/168/ScriptBytecode/0；H /Exports/2/ScriptBytecode/2717；H /Exports/2/ScriptBytecode/3064；H /Exports/2/ScriptBytecode/3065。完整逐条证据见 JSON 同 ID。

## P03 水平移动门控与方向

HeroMovementInputEvent保存轴后只允许HPS {0,15,16,19} 继续输入。Mode5且PlayerAttackMoveType!=0时前向用完整控制旋转（含pitch），右向仍只取yaw；其他模式/类型0走yaw-only前向。最后AddMovementInput后还调用MovementInputDisable。

验收：CantMove1不能普通移动；飞行抬头W有垂直分量，地面W不随pitch上升。

证据：H /Exports/2/ScriptBytecode/3158；H /Exports/2/ScriptBytecode/3159；H /Exports/2/ScriptBytecode/2976；H /Exports/2/ScriptBytecode/2977。完整逐条证据见 JSON 同 ID。

## P04 Space起跳/开飞/退飞

JumpAndFlyEvent先拒绝受击反应。HPS0：Mode1调用Character.Jump并清蓄升计时/重置动作蒙太奇；Mode3跳到开飞分支；Mode5仅在!UnderOcean且Hero_FlyFastUp_Montage没播放时重置落地速度等级并切Mode3。Space Released调用StopJumping。

验收：地面Space跳；下落再Space开飞；普通飞行Space退飞，水下和快速上升蒙太奇期间不能走退飞路径。

证据：H /Exports/2/ScriptBytecode/3158；H /Exports/2/ScriptBytecode/3159；P /Exports/0/ScriptBytecode/391；P /Exports/0/ScriptBytecode/392。完整逐条证据见 JSON 同 ID。

## P05 开飞能力和朝向

开飞共用分支检查IsFlying?，其默认true是允许开飞开关，不是当前MovementMode。通过后重置音爆/蓄升/下落等级，bUseControllerRotationYaw=true，bOrientRotationToMovement=false，再SetMovementMode5。退飞非FPS支路反转两项。

验收：关闭能力不能开飞；第三人称退飞恢复移动朝向。

证据：H /Exports/2/ScriptBytecode/2717；H /Exports/2/ScriptBytecode/2718；H /Exports/2/ScriptBytecode/1327；H /Exports/196/Data/24。完整逐条证据见 JSON 同 ID。

## P06 升降与地面蓄升

升降先拒绝受击反应。HPS0的Mode5、HPS15/16可达分支AddMovementInput(actorUp,axis,false)。HPS0 Mode1且IsFlying?、axis>=1时累加dt；严格>0.5秒开始充能效果，>1秒且仍HPS0时IsSuperFlyUp=true、开飞、效果、清计时；无移动输入时播Hero_FlyFastUp_Montage(rate3)。axis<1清计时与IsFlyUpKeyPressed。

验收：1秒精确边界不触发；超过1秒开飞；释放E中断蓄升；不要地面Q向下穿地。后续升力脉冲未知。

证据：H /Exports/2/ScriptBytecode/2982；H /Exports/2/ScriptBytecode/2983；H /Exports/2/ScriptBytecode/3049；H /Exports/2/ScriptBytecode/3050。完整逐条证据见 JSON 同 ID。

## P07 按冲刺/开始冲刺/释放分开

SprintInputEvent只在!GetIsHitReaction且HPS0接受，强制关闭WalkMode，再置SprintBtnPressed。水平移动路径仅SprintBtnPressed&&IsMovementInput时StartSprintEvent；启动支路置StartSprint=true，随后IsSprint=true、重配MovementParam、重置速度DoOnce、生成冲刺碰撞。SprintBtnReleased仅清SprintBtnPressed。

验收：站立按Shift不能直接清/设实际速度；松Shift不应立即StopMovementImmediately。

证据：H /Exports/2/ScriptBytecode/1283；H /Exports/2/ScriptBytecode/1284；H /Exports/2/ScriptBytecode/2806；H /Exports/2/ScriptBytecode/2807。完整逐条证据见 JSON 同 ID。

## P08 冲刺重置

ResetSprint列举状态包含HPS0；执行IsSprint=false、SetMovementParam、ResetSonicBoomEffectDoOnce、DestroySprintCollision、ResetStartSprint。另一受控分支在CharacterSpeed低于阈值时进入ResetSprint：非Flash Walking850/Flying2000，Flash Walking/Flying均2000；IsSuperFlyUp分支另以1200阈值销毁飞行碰撞。完整上游调度本轮未证。

验收：重置必须同步参数和碰撞；阈值是三维速度模长，不能当作减速率。

证据：H /Exports/2/ScriptBytecode/2863；H /Exports/2/ScriptBytecode/2864；H /Exports/2/ScriptBytecode/2927；H /Exports/2/ScriptBytecode/2928。完整逐条证据见 JSON 同 ID。

## P09 慢行门控

WalkModeInputEvent允许Mode1/2/3/5且HPS0。关闭时SetMovementParam；开启时SetMovementParam然后ResetSprint。WalkMode&&HPS!=8/13的覆盖支路优先。

验收：Alt可打断普通冲刺并进入慢行；不能仅把动画减速。

证据：H /Exports/2/ScriptBytecode/2696；H /Exports/2/ScriptBytecode/2697；H /Exports/163/ScriptBytecode/10；H /Exports/163/ScriptBytecode/11。完整逐条证据见 JSON 同 ID。

## P10 基础参数覆盖

HPS0、!WalkMode、!IsSprint：Mode1/2/3设MaxWalkSpeed=DefaultWalkSpeed(默认1000)、MaxFlySpeed4000、MaxAcceleration2048、BrakingFrictionFactor32、GravityScale5、yaw720。Mode5设同样速度上限、加速度4096、制动32、重力参数5；该支路未写RotationRate。飞行GravityScale5不证明实际施加重力。

验收：地面1000/2048，巡航4000/4096；飞行支路未写字段不能擅自当重置。

证据：H /Exports/163/ScriptBytecode/32；H /Exports/163/ScriptBytecode/33；H /Exports/163/ScriptBytecode/271；H /Exports/196/Data/31。完整逐条证据见 JSON 同 ID。

## P11 慢行与Sliding覆盖

WalkMode优先支路walk250/fly4000、accel2048、brake32、gravity5、yaw360。HPS10 Sliding支路walk2500/fly4000、accel2048、brake32、gravity5、yaw360。不证明松Shift必进入Sliding。

验收：慢行250和Sliding2500分别验收，不能合并。

证据：H /Exports/163/ScriptBytecode/0；H /Exports/163/ScriptBytecode/1；H /Exports/163/ScriptBytecode/218；H /Exports/163/ScriptBytecode/219。完整逐条证据见 JSON 同 ID。

## P12 冲刺/Flash参数

HPS0、IsSprint：非Flash walk=MaxSprintWalkSpeed、fly=MaxCharacterSpeed、accel=MaxAccelerationVal；Flash walk/fly均MaxCharacterSpeed、accel加倍。FallingSpeedType0/1：非Flash Mode1/3制动因子0.6、Flash为0.75，Mode5均20；FallingSpeedType2/3为32。HPS0 gravity5、yaw720。

验收：覆盖地面冲刺、空中冲刺、Flash、重落地等级，不使用统一阻尼常量。

证据：H /Exports/163/ScriptBytecode/83；H /Exports/163/ScriptBytecode/84；H /Exports/163/ScriptBytecode/194；H /Exports/163/ScriptBytecode/195。完整逐条证据见 JSON 同 ID。

## P13 等级覆盖速度上限

HeroRank0..6：MaxCharacterSpeed=[7000,7500,8000,8500,9000,9500,10000]；MaxSprintWalkSpeed=[3000,3100,3200,3400,3600,3800,4000]；MaxAccelerationVal=[15000,15000,20000,20000,20000,25000,25000]。HeroPoint<0有6500/2500/10000分支。

验收：等级0、等级6、负英雄点分开验收。这些是上限/加速度赋值，不是实测速度。

证据：H /Exports/2/ScriptBytecode/5927；H /Exports/2/ScriptBytecode/5928；H /Exports/2/ScriptBytecode/5964；H /Exports/2/ScriptBytecode/5965。完整逐条证据见 JSON 同 ID。

## P14 下落速度分级

仅Mode3更新FallingSpeedType：z<-12000为Ultra3，否则z<-6000为High2，否则z<-1500为Low1，否则None0，全部严格小于。

验收：-6000仍Low，稍低于-6000才High；不能用坠落高度代替速度分级。

证据：H /Exports/2/ScriptBytecode/537；H /Exports/2/ScriptBytecode/538；H /Exports/2/ScriptBytecode/557；H /Exports/2/ScriptBytecode/558。完整逐条证据见 JSON 同 ID。

## P15 落地流程

PlayerBP.OnLanded转发LandingEvent；先SetMovementParam，再HPS0/1/14按FallingSpeedType分流，HPS3/4直接强落地。High支路设HPS3播Hero_SuperHeroLanding_B_Montage(rate1)；Ultra设HPS4播Hero_SuperLanding_Montage(rate0.75)。IsHeroLanding防重入；强落地销毁飞行碰撞、ForceLandingCamera、ForceResetSprint，并可结束热视线。

验收：高速坠落临时改变HPS并中断冲刺；低速不能无条件播超人落地。恢复CanMove的完整通知时序未知。

证据：P /Exports/15/ScriptBytecode/0；P /Exports/15/ScriptBytecode/1；H /Exports/2/ScriptBytecode/4367；H /Exports/2/ScriptBytecode/4368。完整逐条证据见 JSON 同 ID。

## P16 动画速度来自Pawn

SetVariablesFromPawn复制MovementMode/Velocity和HeroComponent状态。更新要求Pawn有效且dt!=0。MovementInput由vector!=0(容差0.001)，Moving由velocity!=0(容差0.01)。动画Speed=XY模长、SpeedZ=z；Direction=CalculateDirection(velocity,actorRotation)。HeroComponent.CharacterSpeed为XYZ模长。

验收：无输入有惯性时MovementInput=false而Moving仍true；禁止把动画Speed等同三维总速。

证据：A /Exports/98/ScriptBytecode/2；A /Exports/98/ScriptBytecode/3；H /Exports/164/ScriptBytecode/11；H /Exports/164/ScriptBytecode/12。完整逐条证据见 JSON 同 ID。

## P17 动画停止分流

StopConduit→StopSprint为!MovementInput&&IsSprinted&&Speed>1500；→StopWalkRun为!MovementInput&&!IsSprinted&&Speed<1500。Speed=1500两条都不满足。两种Stop在相应剩余时间<0.1秒时回Idle，恢复输入可回Moving。

验收：分别使用Hero_Stopping_Sprint与Hero_Stopping_WalkRun；1500边界运行行为待验，不擅改>=/<=。

证据：A /Exports/0/ScriptBytecode/232；A /Exports/0/ScriptBytecode/233；A /Exports/101/Data/5/Value/17；A /Exports/101/Data/5/Value/21。完整逐条证据见 JSON 同 ID。

## P18 动画主状态机

Ground离开：Mode不在{1,2}；Falling离开Mode!=3；Flying离开Mode!=5。Conduit按序Mode3→Falling、Mode1/2→Landing、Mode5→Flying、Mode1→Ground（最后一条被前面的条件覆盖，运行调度未测）。Landing→Ground：Mode1&&(剩余时间<0.1秒||StartSprint)；Landing→Conduit：Mode不在{1,2}。主要混合0.2秒，Conduit→Landing0.1秒，Landing→Ground0.25秒。

验收：起步冲刺允许提前结束落地动画；物理模式选择主状态，非仅HeroPlayerState。

证据：A /Exports/0/ScriptBytecode/35；A /Exports/0/ScriptBytecode/36；A /Exports/0/ScriptBytecode/310；A /Exports/101/Data/0。完整逐条证据见 JSON 同 ID。

## P19 跳跃动画时间

JumpStart→FallingLoop使用GetInstanceAssetPlayerTimeFromEndFraction(57)<0.1，是动画剩余比例，不是0.1秒或velocity.z<=0。该转换混合0.55秒，节点57对应ALS_N_Jump。

验收：不能只在到达抛物线顶点切下落循环；区分时间比例与秒数。

证据：A /Exports/0/ScriptBytecode/244；A /Exports/0/ScriptBytecode/245；A /Exports/101/Data/0；A /Exports/102/Data/71。完整逐条证据见 JSON 同 ID。

## P20 飞行动画驱动

BlendListByBool_3用!MovementInput&&SprintBtnPressed；BlendListByBool_4用(SpeedZ<-1500||SpeedZ>1000)&&(-95<Direction<95)。LeanRotMultiply在水平Speed>3000为2，否则1。飞行引用HeroABS_FlyingMoveAnim、HeroABS_FlyingUpDonwAnim、Hero_FlyTameFront、Hero_IdleFlying。未证明完整逐层混合优先级。

验收：高速升降姿态同时看垂直速度和方向；无输入按冲刺与普通悬停输入不同。

证据：A /Exports/0/ScriptBytecode/131；A /Exports/0/ScriptBytecode/132；A /Exports/102/Data/49；A /Exports/102/Data/50。完整逐条证据见 JSON 同 ID。

## 编译动画快速路径与资产

一部分条件没有Kismet赋值，而是PropertyAccessLibrary复制：CopyIndex16 Moving→TransitionResult_1；17 !MovementInput→TransitionResult_2；18 MovementInput→TransitionResult_3；19 MovementInput→TransitionResult_7。依据 A /Exports/101/Data/6 与 /Exports/101/Data/5/Value/{15,16,17,21}。这意味着Idle→Moving依据真实运动，Moving→停止Conduit依据无输入，停止中恢复输入可回Moving。

关键原资产包括HeroABS_MoveGround、Hero_Stopping_Sprint、Hero_Stopping_WalkRun、ALS_N_Jump、HeroABS_JumpFallLoop、HeroABS_FlyingMoveAnim、HeroABS_FlyingUpDonwAnim、Hero_IdleFlying、Hero_JumpLand。所有节点与Imports指针已保存于JSON animation_asset_references。

## 未确认运行行为

- 未启动原游戏，真实速度曲线、跳高、碰撞滑移、帧时序和操作体感均未验证。
- 本轮未完整追踪教程/GameInputState/暂停/剧情DisableInput；默认键可能被存档改写。
- MovementInputDisable、ResetSprint速度检查的全部上游调度/DoOnce重入及latent续体尚未完全证明，不能把Shift释放直接等同ResetSprint。
- 地面蓄升后的latent升力/速度脉冲未纳入已证合同。
- SetMovementParam赋值已证，但全部调用时序未证；未赋值字段可能保留前态值。
- 动画索引采用静态重建；完整混合优先级、Root Motion、动画通知与运行调度尚未验收。
- 强落地结束返回CanMove的精确时刻、输入重新解锁和攻击碰撞续体未知。
- FlashMode完整开关、UnderOcean切换、地面trace细节、所有攻击/Boss中断矩阵不在范围内。
- UE原参数转Web必须另做世界比例、轴向与物理积分标定，不能直接照抄保证一致。

验证：983 个 JSON 指针全部解析成功，20 条合同；未改 Web，未运行游戏。
