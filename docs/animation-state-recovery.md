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

2026-10-25 已从 pak 导出以下 PSA/config，并通过 `scripts/append-locomotion-animations.py` 追加到原 93 骨骼 `public/assets/character/hero.gltf`（原有 18 段保留，共 28 段）：

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
```

每段 93 个模型关节全部映射，report 在 `research/world-recovery/locomotion-import.json`。

## 当前 Web 的映射

`src/game/Character.ts` 现在使用原 `hero.gltf` 的 28 段：

```text
idle  -> Hero_Idle
walk  -> Hero_Walk           # planar speed < 4 m/s
run   -> Hero_SprintRun      # 前向跑步；Hero_SprintSuper 已导入但实测姿态不是正常跑步，暂不用于默认 run
jump  -> Hero_JumpFall       # 下落循环
hover -> Hero_IdleFlying
fly   -> Hero_FlyFastSprint
```

已加的最小直接状态链（不是 AnimBP 的混合/条件曲线）：

```text
ground idle -> Hero_Walk / Hero_StartSprint -> Hero_SprintRun (loop)
walk/run -> Hero_Stopping_WalkRun (once) -> Hero_Idle (loop)
ground jump -> Hero_JumpSpeed (once) -> Hero_JumpFall (loop)
landing -> Hero_JumpLand (once) -> Hero_Idle / Hero_Walk / Hero_SprintRun (loop)
```

因此：

- 待机/飞行/攻击/跑步/跳跃下落素材已是原版；
- 跳跃/落地/冲刺起停已有直接片段顺序；
- **仍不是 `HeroABS_MoveGround` 的 BlendSpace**，没有原始速度/方向轴、过渡曲线、IK/通知/根运动；
- `ALS_N_Jump`、`HeroABS_Flying*` 和完整方向混合仍未导入；
- 直接状态链的时长取 `AnimationGroup.getLength()`，不是 AnimBP 的精确 transition/blend 时间。

## 结论

Gate 4 仍未完成，但核心缺失片段已进入原骨架，并已用真实 `W`/Space 输入验证 `run`/`jump` 片段可以播放（见 `research/screenshots/play-sprintrun.jpg`、`play-jumpfall.jpg`）。下一步是按 `HeroAnimBP` 的转移条件实现混合空间与状态机，而不是继续换片段。

## 证据

- 解码文件：`research/rea-audit/decoded/hero-anim/HeroAnimBP.json`、`HeroABS_MoveGround.json`
- 源包：`/-HeroGame/Player/Animations/HeroAnimBP`、`HeroABS_MoveGround` 等
