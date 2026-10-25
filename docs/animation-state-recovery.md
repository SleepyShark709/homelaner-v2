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

2026-10-25 已从 pak 导出以下 PSA/config，并通过 `scripts/append-locomotion-animations.py` 追加到原 93 骨骼 `public/assets/character/hero.gltf`（原有 18 段保留，后续再加入 ALS 方向/飞行/跳跃共 46 段）：

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

`src/game/Character.ts` 现在使用原 `hero.gltf` 的 46 段：

```text
idle  -> Hero_Idle
walk  -> Hero_Walk           # planar speed < 4 m/s
run   -> Hero_SprintRun      # 前向跑步；Hero_SprintSuper 在 >16.75 m/s 的高速度段按 MoveGround 样本参与混合
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

### 1D ground blend（2026-10-25）

`Character.setGroundBlend()` 按 `HeroABS_MoveGround` 的实际 SampleData 速度值混合 `Hero_Idle` / `Hero_Walk` / `Hero_SprintRun` / `Hero_SprintSuper`：

```text
0 .. 3 m/s       Idle -> Walk
3 .. 8.5         Walk -> SprintRun
8.5 .. 16.75     SprintRun 1.0
16.75 .. 25      SprintRun -> SprintSuper
>= 25            SprintSuper 1.0
```

MoveGround 的采样 Y 值：Walk 300、SprintRun 850、SprintSuper 1675/2225/2500 cm/s。

2026-10-25 又导入了六段原版方向样本，总动画数 46：

```text
ALS_N_Walk_B / FL / FR
ALS_N_Run_B / FL / FR
```

`setGroundBlend` 已扩展为 speed × direction 的 2D 权重结构；但当前 `OriginalPlayer` 始终让角色朝向速度方向，所以 local direction 恒为 forward，后退探针仍返回 `Hero_SprintRun`。方向样本已导入并验证，但方向轴要等相机相对 strafe/aim 控制恢复后才可见。

这是 `HeroABS_MoveGround` 的**速度/方向子集**；真正的双向 BlendSpace、精确轴值、过渡曲线和 AnimBP transition 时间仍未恢复。10 m/s 实测截图 `research/screenshots/play-directional-blend-run.jpg` 无畸形。

### 飞行方向样本（2026-10-25）

已从 pak 导出并追加 `Hero_FlyBack/Left/Right/Tame/TameFront`，总动画数 **46**。`Character.setFlyBlend()`：

```text
FlyUp / FlyDown / FlyFastDown 保留垂直优先级
水平方向按 local velocity 在 FlyForward(低)/FlyForwardLow/FlyLeft/FlyRight/FlyBack 之间加权
hover -> Hero_IdleFlying
```

真实输入验证：

```text
D（右移） -> Hero_FlyRight
S（后退） -> Hero_FlyBack, speed 40
```

前向样本按 `HeroABS_FlyingMoveAnim` 的速度轴近似选择：

```text
<=12 m/s   FlyTame
12..30     FlyForwardLow
30..55     FlyForward
>55        FlyFastSprint
```

24.5 m/s 实测返回 `Hero_FlyForwardLow`；42.3 m/s 返回 `Hero_FlyForward`；66.6 m/s 加速档返回 `Hero_FlyFastSprint`。

报告：[fly-directional-import.json](../research/world-recovery/fly-directional-import.json)

### ALS_N_Jump（2026-10-25）

已导入 `ALS_N_Jump`（总动画数 **46**）。起跳选择：

```text
standing / walk jump  -> ALS_N_Jump
running jump          -> Hero_JumpSpeed
```

真实 Space 输入返回 `clip=ALS_N_Jump`，随后仍按 `JumpFallFast -> JumpLand` 前进。报告：[jump-extra-import.json](../research/world-recovery/jump-extra-import.json)

下落样本现在按垂直速度选择：

```text
vertical >= -3 m/s -> Hero_JumpFall
vertical <  -3 m/s -> Hero_JumpFallFast
```

普通起跳的 ALS 起跳片段会覆盖到下落初期，因此通常直接进入 Fast；从边缘走落等低速下落会先用 `Hero_JumpFall`。

### Root motion 审计

`scripts/audit-root-motion.mjs` 检查全部 46 段动画的 root joint translation：

```text
animationCount   46
movingRootClips  []
```

所有转换后的 clip 都是 **in-place**（root 平移为 0），角色位移由外部 PlayerMotor 驱动；这些 clip 没有可提取的 root motion。原 AnimBP 的 root-motion/notify 逻辑仍未恢复，但当前素材本身不含 root 位移。

### AnimNotify 清单

`scripts/extract-animation-notifies.py` 从 28 份 UModel `.props.txt` 提取到：

```text
BodyMvmt_Cue
PlayFootStepL
PlayFootStepR
RunStop
```

`scripts/extract-animation-notifies.py` 从 28 份 UModel `.props.txt` 提取到名称清单；进一步用 UAssetGUI 解码全部 46 段 AnimSequence 后，`AnimNotifyEvent.LinkValue` 给出绝对时间：

```text
24 段有 notify
116 个 notify event
39 种 notify 名称
```

关键 locomotion notify：

```text
Hero_Stopping_Sprint  BodyMvmt_Cue 0.0986s  RunStop 0.1946s
                      PlayFootStepR 0.9479s  PlayFootStepL 1.2069s
Hero_Walk             PlayFootStepR 0.332s   PlayFootStepL 0.826s
Hero_SprintRun        PlayFootStepR 0.264s   PlayFootStepL 0.556s
Hero_SprintSuper      PlayFootStepR 0.263s   PlayFootStepL 0.550s
Hero_JumpLand         PlayFootStepL 0.067s
Hero_JumpSpeed        PlayFootStepL 0.107s
Hero_IdleFlying       SpawnFlyDustEffect 2.393s
```

`Hero_StartSprint` 没有 notify。完整报告：[notify-times.json](../research/world-recovery/notify-times.json)。攻击序列的 notify 时间本来就已经在 `combat-timings.json` 中，这一轮补齐的是 locomotion/fly 序列。

### 原版脚步声音（2026-10-25）

`Footstep01..09` 是 cooked `SoundWave`，音频以 Ogg 形式嵌在 `.uexp` 偏移 `0x87` 之后。`scripts/extract-footstep-sounds.py` 提取出 8 个 `.ogg`（pak 中没有 `Footstep05`），SHA/size 清单在 [footstep-sound-manifest.json](../research/world-recovery/footstep-sound-manifest.json)。

`Character.onFootstep` 在主导 clip 的原始 notify 时间触发；`src/game/Footsteps.ts` 用 Web Audio 随机播放这些原版采样。已实测普通 W 前进 1.4 秒触发：

```text
Hero_Walk, Hero_SprintRun, Hero_SprintRun
```

`?audio=0` 可关闭。音频文件保持本地、Git 忽略；未恢复表面材质对应的 footstep 变体选择。Chrome 实测 `footstep01.ogg` 解码为 `0.3669 s / 48000 Hz / mono`，与 SoundWave 的 0.3695 s 元数据一致。

攻击挥击音也已提取：`Punch_Swish01..04`（[combat-sound-manifest.json](../research/world-recovery/combat-sound-manifest.json)）。`Combat.begin()` 通过 `onSound('swing')` 播放原版 swish；真实 J 输入触发 1 次。`punch_swish01.ogg` Chrome 解码为 `0.505 s / 48000 Hz / stereo`。超能力/爆炸等专用音效尚未接线。

命中/破坏音使用原版 `chain_D_impacts_0201/0601`（[impact-sound-manifest.json](../research/world-recovery/impact-sound-manifest.json)）：命中时截取前 0.22 s，破坏时播放完整约 1.44 s 片段。`strike()` 在非 heat 攻击且结果非 ignored 时触发 `impact`/`destruction`。

超能力/冲刺音从 `Cue_AirSuperKick` / `Cue_DashAttackStart` 的 SoundWave imports 还原（[ability-sound-manifest.json](../research/world-recovery/ability-sound-manifest.json)）：

```text
CannonExplode01..05_Stereo   strong punch/kick -> heavy
Sweetener_WhooshF01..04     AirAttackStart -> whoosh
```

真实输入：

```text
Shift+K -> Hero_SuperPunch, sounds=[heavy], action=强力拳波
Space→Space→J -> Hero_AirAttackStart, sounds=[whoosh]
```

Chrome 解码：`cannonexplode01_stereo.ogg` 2.4271 s / 48 kHz / stereo；`sweetener_whooshf01.ogg` 0.8623 s / 48 kHz / stereo。Cue 图本身包含 `SoundNodeDelay`、`Mixer`（输入音量 1/1/.65）、`Random` 和 `Modulator`；当前实现只是按 Cue 的素材清单做分层近似（heavy = swish + cannon，whoosh = swish + whoosh），未逐节点复现随机/延迟/包络。

飞行风噪来自 `Cue_FlyingWindNoise` 的 `SoundNodeWavePlayer` → `/Game/Assets/Audio/Whooshes/Flourish03`（[flight-wind-manifest.json](../research/world-recovery/flight-wind-manifest.json)）。实际播放为 1.2× pitch、cue volume .35、循环，并按水平/垂直速度调节增益；真实双跳进入飞行后 `flightWindActive=false -> true`。Chrome 解码 3.4507 s / 48 kHz / stereo。

空中首次攻击（近战 J 或远程 K）现在进入 `HeroAnimBP` 的 AirAttack 状态入口 `Hero_AirAttackStart`（包含 `StartAirAttack` notify），后续空中攻击切 `Hero_AirKick_L/R`，落地后复位。真实 Space→Space→J/K 均返回 `clip=Hero_AirAttackStart`；连续两次 K 的结果记录在 `research/world-recovery/air-attack-chain.json`。


`HeroABS_MoveGround` 的样本速度轴以 850 cm/s（8.5 m/s）为 run 基准；Web 的 `Hero_SprintRun` 播放速率改为 `planarSpeed / 8.5`（0.7..2.2），`Hero_Walk` 改为 `planarSpeed / 3`（0.6..1.5），不再使用固定的 6/1.5 基准。10 m/s 普通跑步截图 `research/screenshots/play-run-ratio.jpg` 无畸形。

`Hero_SprintSuper` 在 30 m/s 的 Shift 冲刺下已实际渲染检查（`research/screenshots/play-sprint-super-high.jpg`）：单段姿态仍偏直立、没有明显前倾摆腿。但 `HeroABS_MoveGround` 的实际 SampleData 在 1675/2225/2500 cm/s 明确使用 `Hero_SprintSuper`，因此高速度段（>16.75 m/s）现在按样本权重使用它；30 m/s 时 clip 回到 `Hero_SprintSuper`。若后续逐帧对照证明导入片段姿态有误，应修正转换/骨骼轨道，而不是继续忽略该原版样本。


`npm run verify:locomotion` 会检查整个 `hero.gltf` 的 46 段动画：

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
