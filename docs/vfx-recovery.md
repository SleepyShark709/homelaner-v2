# 玩家 VFX 还原（2026-10-28）

## 结论

当前 `src/game/Effects.ts` 里的速度线、拳风、冲击球、热视线都是 **Web 程序化预览**，不是原版 UE 粒子资产。声音和动画是原版，视觉特效不是。

用户已明确：玩家操控角色的原版特效优先级很高。后续以原版 `P_*` 粒子系统、材质、贴图、网格和 AnimNotify 为准，不再把程序化几何当作还原结果。

## 已定位的原版资产

原包：`E:\SteamLibrary\steamapps\common\UNDEFEATED\UNDEFEATED\Content\Paks\UNDEFEATED-WindowsNoEditor.pak`

`-HeroGame/Effect/` 下与玩家相关：

```text
P_NormalAttackSlash      普通攻击斩击
P_LongRangeSlash         远程/长拳斩击
P_LongRangeSlashBlack
P_FistCannonSpawn        拳头炮生成
P_SuperPunchSpawn        重拳生成
P_SuperPunchSpawnDust    重拳尘土
P_AirAttack_Shock        空中攻击冲击
P_AirKIckWind            空中踢风
P_Attack_Wave            攻击波
P_StartSprint            起跑
P_FlyDust                飞行尘土
P_FlyIdleDust            飞行悬停尘土
P_FlyModeCloud           飞行模式云
P_FlySonicBoomFPS        飞行音爆
P_FlyStrat_Wave          飞行起始波
P_FlyUp                  上升
P_FlyUpCharge            上升蓄力
P_FlyUpSequence          上升序列
P_Fly_Shock / Big        飞行冲击
```

## 第一个样本：P_NormalAttackSlash

已解包并用 UAssetGUI 解码：

```text
UParticleSystem: P_NormalAttackSlash
Emitter: ParticleSpriteEmitter
LOD: ParticleLODLevel_0
TypeData: ParticleModuleTypeDataMesh
Mesh: SM_ky_quad_centerRot
Material: M_Effect_Slash_G
  parent: M_Effect_Master_RGBSubUV
  texture: T_ky_slash01_4x4 (2048x2048, 4x4 subimages)
Lifetime: 0.2 s
SubImages: 4 x 4
SubImageIndex: 3..10
StartSize: 20
SizeMultiplyLife: 1 -> 1.5
bUseLocalSpace: true
bOverrideMaterial: true
RollPitchYawRange: 0..90
```

提取出的本地文件（Git 忽略）：

```text
public/assets/vfx/-HeroGame/Res/Effect/T_ky_slash01_4x4.png
public/assets/vfx/-HeroGame/Res/Effect/T_ky_slash01_4x4.tga
public/assets/vfx/-HeroGame/Mesh/Effect/SM_ky_quad_centerRot.pskx
```

贴图是原版四行四列斩击图集；红色月牙 + 蓝色 X 形，黑底。`T_ky_slash01_4x4` 的 `read_image` 检查已确认内容正确。

## 当前状态

`P_NormalAttackSlash` 已在 Web 中显示：使用 Babylon `SpriteManager` 直接读取原版 `T_ky_slash01_4x4` 图集，按原版 `SubImageIndex 3..10`、0.2 s 生命周期、加色混合、面向相机播放。之前 `StandardMaterial`/自定义 plane 的黑白方块原型已废弃。

截图：`research/screenshots/sprite-slash.jpg`。提交 `f2a0244`。

`P_FlyDust` / `P_FlyIdleDust` 也已换成原版烟雾图集：`T_RaP_Smoke_puff_4x4_2k`（1024×1024，4×4，RGBA），随机帧、0.9–1.4 s 生命周期、透明度衰减和放大。提交 `8ef204f`，截图 `research/screenshots/fly-dust2.jpg`。

这项仍是**原版贴图/材质族 + 作者发射节奏**，不是四个 GPU emitter 的完整复刻；原版参数已记录在上面的 module 数据中。

`P_StartSprint` 已接入原版 `T_BlastWave` 贴图：地面起跑时生成 0.4 s 加色扩散冲击波。原版 `SM_BlastWave` 网格和三个 mesh emitter 尚未转换，因此当前是**原版贴图/时序的首版**，不是完整网格粒子复刻。提交 `4c80a47`，截图 `research/screenshots/start-sprint-wave2.jpg`。

`P_AirAttack_Shock` 已接入同一原版 `T_BlastWave` 贴图：空中近战生成更大、更短的冲击环，0.3 s。原版三个 emitter（含 `T_Burst_M`/`T_Wave`）尚未完整转换。提交 `fa088bb`，截图 `research/screenshots/air-attack-shock.jpg`。

仍需继续对齐：

1. 原版 `M_Effect_Master_RGBSubUV` 的颜色/透明度曲线与精确尺寸；
2. `ParticleModuleTypeDataMesh` 的 roll/pitch/yaw 随机与手部 socket 绑定；
3. burst/lifetime/size 的精确组合；
4. `P_FlyDust` 四个 POP emitter 的 burst/速度/加速度按原参数还原；
5. `P_StartSprint` 的 `SM_BlastWave` 网格与三 emitter 参数；
6. 逐个接入其他 `P_*` 特效，替换 `Effects.ts` 的程序化 effects。

## 优先级

1. 普通攻击斩击（P_NormalAttackSlash）
2. 飞行尘土/上升/音爆（P_FlyDust、P_FlyIdleDust、P_FlyUp、P_FlySonicBoomFPS）
3. 起跑/冲刺（P_StartSprint）
4. 远程/重击（P_LongRangeSlash、P_FistCannonSpawn、P_SuperPunchSpawn）
5. 空中攻击/冲击（P_AirAttack_Shock、P_AirKIckWind、P_Attack_Wave）

飞行贴边镜头/角色抖动暂不处理（用户已明确跳过）。
