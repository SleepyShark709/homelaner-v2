# HeroComponent 相机契约（AST 证据）

日期：2026-10-25。来源：`research/player-flow-HeroComponent-view.json`（UAssetAPI 解码 `HeroComponent` 的 Kismet AST，项目内 SHA-256 见生成记录），不是运行时观察。

## 已确认值

`SetPlayerComponentReference` 结尾：

```text
DefaultSocketOffset = CameraBoom.SocketOffset
DefaultArmLength   = CameraBoom.TargetArmLength
```

因此运行时默认值来自 `PlayerBP` 的 CameraBoom：`TargetArmLength=400 cm`、`SocketOffset=(0,50,90) cm`、`RelativeLocation Z=70 cm`；HeroComponent CDO 中的 300/(0,0,0) 会在初始化时被覆盖。

相机更新段落还包含：

- `Camera.FieldOfView` 用 `FInterpTo(..., 90, dt, 2)`，即 90° 视场；
- `Temp_float_Variable_123=400`、`Temp_float_Variable_124=650`，由 `IsAttackMoving` 参与选择目标臂长；
- `FarArmLength=800 cm`，以及 `FarCameraInterpSpeed` 的动态 1/4/8/16 分支；
- `CameraLagSpeed=15`、`CameraRotationLagSpeed=15`。

## 当前 Web 实现

- 普通第三人称：臂长 400 cm、SocketOffset(0,50,90)、boom Z70、FOV 90° 水平、lag 15；
- 攻击时目标臂长 **650 cm**，用 `CameraInterpSpeed=2` 插值；
- 相机碰撞 AABB 收缩。

## 未实现/未证明

- `FarArmLength=800` 与 Far/Zoom 状态的具体触发分支；
- `ZoomSocketOffset=(300,50,30)` 的输入与状态；
- 相机弹簧后处理、碰撞后控制和动画 root-motion 对相机的影响。

这些分支只按 AST 值记录，未用自设计逻辑替代；下一步继续解析 HSM/HeroPlayerState 分支后再接入。
