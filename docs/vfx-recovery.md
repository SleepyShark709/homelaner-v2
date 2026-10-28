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

第一次 Web 原型尝试用 Babylon `StandardMaterial` + 图集 UV 播放，但材质/UV 绑定结果不正确：出现黑色/白色方块而不是红色斩击。该原型已回退，未进入提交，避免把错误效果当成原版。

下一步不是继续猜 Babylon 材质参数，而是：

1. 解出 `M_Effect_Master_RGBSubUV` 的实际混合/颜色/UV 规则；
2. 用原版 quad 的 UV/材质合同重建，而不是通用 plane；
3. 按 `P_NormalAttackSlash` 的 burst/lifetime/size/SubImageIndex 播放；
4. 再按 AnimNotify/PlayerBP 绑定到手/武器位置；
5. 逐个替换 `Effects.ts` 的程序化 effects。

## 优先级

1. 普通攻击斩击（P_NormalAttackSlash）
2. 飞行尘土/上升/音爆（P_FlyDust、P_FlyIdleDust、P_FlyUp、P_FlySonicBoomFPS）
3. 起跑/冲刺（P_StartSprint）
4. 远程/重击（P_LongRangeSlash、P_FistCannonSpawn、P_SuperPunchSpawn）
5. 空中攻击/冲击（P_AirAttack_Shock、P_AirKIckWind、P_Attack_Wave）

飞行贴边镜头/角色抖动暂不处理（用户已明确跳过）。
