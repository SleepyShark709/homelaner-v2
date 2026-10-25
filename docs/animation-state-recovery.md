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

## 当前 Web 的映射

`src/game/Character.ts` 目前只使用原 `hero.gltf` 里的 18 段：

```text
idle  -> Hero_Idle
run   -> A_ThirdPersonRun      # ALS 跑步，不是 HeroABS_MoveGround 的完整混合
jump  -> Hero_IdleFlying       # 临时回退
hover -> Hero_IdleFlying
fly   -> Hero_FlyFastSprint
```

因此：

- 待机/飞行/攻击素材是原版；
- **地面移动/跳跃/落地/冲刺起停仍是回退映射**，不是 AnimBP 的完整状态机；
- 还没有实现原版状态转移、混合空间、IK/物理次级运动、通知和根运动消费。

## 结论

Gate 4 仍未完成，但已拿到原版 AnimBP/BlendSpace 的真实资产与状态名称。下一步必须先把缺失的 `Hero_Walk`、`Hero_SprintRun`、`Hero_StartSprint`、`Hero_Stopping_*`、`Hero_JumpSpeed`、`Hero_JumpLand` 等 PSA 导入原骨架，再按 AnimBP 的转移条件实现，不能继续用名字相近的片段冒充。

## 证据

- 解码文件：`research/rea-audit/decoded/hero-anim/HeroAnimBP.json`、`HeroABS_MoveGround.json`
- 源包：`/-HeroGame/Player/Animations/HeroAnimBP`、`HeroABS_MoveGround` 等
