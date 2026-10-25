# 原版角色动画状态机恢复（Gate 4）

日期：2026-10-25。来源是 shipped pak 的 cooked AnimBlueprint，而不是运行时猜测。

## 已恢复的资产

```text
/Game/-HeroGame/Player/Animations/HeroAnimBP
/Game/-HeroGame/Player/Animations/HeroABS_MoveGround
/Game/-HeroGame/Player/Animations/HeroABS_FlyingMoveAnim
/Game/-HeroGame/Player/Animations/HeroABS_FlyingUpDonwAnim
/Game/-HeroGame/Player/Animations/HeroABS_JumpFallLoop
/Game/-HeroGame/Player/Animations/HeroABS_AirAttack
```

`HeroAnimBP` 的动画图引用：

- 待机：`Hero_Idle`
- 飞行待机/移动：`Hero_IdleFlying`、`Hero_CrossArmsFlying`、`HeroABS_FlyingMoveAnim`、`HeroABS_FlyingUpDonwAnim`
- 地面移动：`HeroABS_MoveGround`（内部引用 `Hero_Walk`、`Hero_SprintRun`、`Hero_SprintSuper` 和 ALS 走/跑样本）
- 跳跃/落地：`ALS_N_Jump`、`Hero_JumpSpeed`、`Hero_JumpLand`、`ALS_N_Jump`
- 冲刺起停：`Hero_StartSprint`、`Hero_Stopping_Sprint`、`Hero_Stopping_WalkRun`
- 攻击：`Hero_Attack1..4_Montage`、`Hero_LongFistForce_*`、`Hero_AirKick_*` 等

`HeroABS_MoveGround` 还引用了：

```text
ALS_N_Walk_B / FL / FR
ALS_N_Run_B / FL / FR
Hero_Walk / Hero_SprintRun / Hero_SprintSuper
```

## 已导入的原版 locomotion 片段

2026-10-25 已从 pak 导出以下 PSA/config，并通过 `scripts/append-locomotion-animations.py` 追加到原 93 骨骼 `public/assets/character/hero.gltf`（原有 18 段保留，共 34 段）：

```text
Hero_Walk             31f @31.0
Hero_SprintRun        36f @61.714
Hero_SprintSuper      28f
Hero_JumpSpeed        21f @63.0
Hero_JumpLand         13f @65.0
Hero_JumpFall         61f
Hero_JumpFallFast     91f
Hero_StartSprint      61f @42.7
Hero_Stopping_Sprint  76f @60.8
Hero_Stopping_WalkRun 31f @31.0
Hero_FlyForward
Hero_FlyForwardLow
Hero_FlyFastForward1
Hero_FlyDown
Hero_FlyFastDown
Hero_FlyUp
```

每段 93 个模型关节全部映射；部分 PSA config 主动删除了头发/配饰的旋转轨道（68 个旋转通道），report 在 `research/world-recovery/locomotion-import.json`。

## 当前 Web 的映射

`src/game/Character.ts` 现在使用原 `hero.gltf` 的 34 段：

```text
idle  -> Hero_Idle
walk  -> Hero_Walk           # planar speed < 4 m/s
run   -> Hero_SprintRun      # 前向跑步；Hero_SprintSuper 已导入但实测姿态不是正常跑步，暂不用于默认 run
jump  -> Hero_JumpFallFast   # 下落循环；对应 HeroABS_JumpFallLoop 的 Speed~1250/SpeedZ~-5000 样本
hover -> Hero_IdleFlying
fly   -> Hero_FlyForward

垂直优先：
  velY > 1.5   -> Hero_FlyUp
  velY < -6    -> Hero_FlyFastDown
  velY < -1.5  -> Hero_FlyDown
  否则前飞 >7  -> Hero_FlyForward
  前飞 1..7    -> Hero_FlyForwardLow
  悬停         -> Hero_IdleFlying
```

已加的最小直接状态链（不是 AnimBP 的混合/条件曲线）：

```text
normal ground run -> Hero_SprintRun (direct)
Shift sprint -> Hero_StartSprint (once) -> Hero_SprintRun (loop)
SprintRun + newly pressed Shift -> Hero_StartSprint again
SprintRun -> wasSprinting ? Hero_Stopping_Sprint : Hero_Stopping_WalkRun -> next (once)
Hero_Walk -> Hero_Stopping_WalkRun (once) -> Hero_Idle (loop)
ground jump -> Hero_JumpSpeed (once; hold last frame while velY>0.2) -> Hero_JumpFallFast (loop)
landing -> Hero_JumpLand (once) -> Hero_Idle / Hero_Walk / Hero_SprintRun (loop)
```

因此：

- 待机/飞行/攻击/跑步/跳跃下落素材已是原版；
- 跳跃/落地/冲刺起停已有直接片段顺序；
- **仍不是 `HeroABS_MoveGround` 的 BlendSpace**，没有原始速度/方向轴、过渡曲线、IK/通知/根运动；
- `ALS_N_Jump`、`HeroABS_Flying*` 和完整方向混合仍未导入；
- 直接状态链的时长取 `AnimationGroup.getLength()`，不是 AnimBP 的精确 transition/blend 时间。

## AnimBP baked state machines

从 `HeroAnimBP_C.BakedStateMachines` 直接读出的状态名（清单：[hero-animbp-states.json](research/world-recovery/hero-animbp-states.json)）：

```text
DefaultStateMachine:
  Ground / MovementModeConduit / Falling / Flying / Landing
  BossAttackingMoveLoop / BossBlowingMoveSecondLoop /
  BossBlowingMoveLoop / BossHeavyAttackSmashingLoop

Ground State:
  Idle / Moving / StopSprint / StopConduit / StopWalkRun

Jump/Falling State:
  JumpStart / FallingLoop / AirAttack

Flying State:
  Flying
```

这确认了当前基础链的拆分方向：
`StopSprint` 和 `StopWalkRun` 是两个独立状态，`JumpStart`/`FallingLoop` 也是两个状态。
目前只拿到了状态名和 transition index，**target state 与 crossfade 时间仍未解析**。

## 动画数据校验

空中首次远程攻击现在进入 `HeroAnimBP` 的 AirAttack 状态入口 `Hero_AirAttackStart`（包含 `StartAirAttack` notify），后续空中攻击切 `Hero_AirKick_L/R`，落地后复位。真实 Space→Space→K 验证返回 `clip=Hero_AirAttackStart`。


`HeroABS_MoveGround` 的样本速度轴以 850 cm/s（8.5 m/s）为 run 基准；Web 的 `Hero_SprintRun` 播放速率改为 `planarSpeed / 8.5`（0.7..2.2），`Hero_Walk` 改为 `planarSpeed / 3`（0.6..1.5），不再使用固定的 6/1.5 基准。10 m/s 普通跑步截图 `research/screenshots/play-run-ratio.jpg` 无畸形。

`Hero_SprintSuper` 在 30 m/s 的 Shift 冲刺下已实际渲染检查（`research/screenshots/play-sprint-super.jpg`）：角色呈直立/步行姿态，没有原版冲刺应有的前倾和摆腿。因此当前 Shift 冲刺继续使用 `Hero_SprintRun`，不把 `Hero_SprintSuper` 当作普通冲刺片段；仍保留该导入片段供后续 BlendSpace 验证。


`npm run verify:locomotion` 会检查整个 `hero.gltf` 的 34 段动画：

- 每段旋转通道关节数：基础/多数原版片段 93；部分 PSA config 主动删除了头发/配饰骨骼的旋转轨道，因此为 68；
- 四元数范数误差 < 5e-8；
- 无 NaN/Inf；
- 记录每段时长、帧数、首尾旋转差。

报告：`research/world-recovery/locomotion-frame-validation.json`。这只证明关键帧数据结构/数值健康，**不等于**与原程序逐帧骨骼对照。

## 结论

Gate 4 仍未完成，但核心缺失片段已进入原骨架，并已用真实 `W`/Space 输入验证 `run`/`jump` 片段可以播放（见 `research/screenshots/play-sprintrun.jpg`、`play-jumpfallfast.jpg`）。`HeroABS_JumpFallLoop` 解码后确认其低空下落样本是 `Hero_JumpFallFast`，因此 jump 下落循环已切换到该片段。下一步是按 `HeroAnimBP` 的转移条件实现完整混合空间与状态机，而不是继续换片段。

## 证据

- 解码文件：`research/rea-audit/decoded/hero-anim/HeroAnimBP.json`、`HeroABS_MoveGround.json`
- 源包：`/-HeroGame/Player/Animations/HeroAnimBP`、`HeroABS_MoveGround` 等
