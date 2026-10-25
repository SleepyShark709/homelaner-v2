# Homelander 真实模型接入与动作映射

日期：2026-10-25。模型由用户提供：

- `E:\homelander.glb`（29 MB，当前使用）
- `E:\homelander-style.glb`（33 MB，未使用）

本地副本：`public/assets/character/homelander.glb`（Git 排除）。

## 模型结构

- Blender glTF 2.0，1 个蒙皮 mesh，49,978 顶点，68 骨骼；
- 自带 3 张贴图与 18 段动画：idle/walk/jog/sprint/fly/hover/jump_start/jump_land/land/fall/takeoff/punch/combo_a/combo_b/casual_attack/slam/laser_hip/laser_back；
- 骨骼名 `root.x`、`spine_01.x`、`shoulder.l`、`arm_stretch.l`、`forearm_stretch.l`、`thigh_stretch.l` 等；与原 103 骨骼 UE 骨架命名/rest pose 不同。

## 当前接入

`?view=play&skin=homelander`：

- 替换原 `hero.gltf`，使用 Homelander 自带 mesh/贴图/骨架/披风；
- 原版 `?view=play` 仍使用原角色和原 18 段动画；
- Shift+E 热视线、右键远程、`mode=free` 保留；
- 默认模型无 T-pose/手臂畸形。

### 动作策略

原始蓝图状态机、攻击时间轴、连招、相机和输入未改；把原版动作名映射到 Homelander 自带动作：

| 原版动作 | Homelander |
|---|---|
| Hero_Idle | idle |
| A_ThirdPersonRun | jog |
| Hero_IdleFlying | hover |
| Hero_FlyFastSprint | fly |
| Hero_Attack1/2/3/4 | punch / combo_a / combo_b / casual_attack |
| Hero_Smash_A | slam |
| 其它攻击 | punch/combo/slam/casual_attack 映射 |

这不是“原版动作逐帧重定向”；是**动作名/行为映射**，以保证视觉无畸形。

## 为什么不做逐帧重定向

已生成实验性重定向：

- 脚本 `tools/asset-pipeline/retarget-homelander.mjs`
- 输出 `public/assets/character/homelander-retarget.json`（4 MB，本地）
- 开关 `?retarget=1`

将原 18 段动画按骨骼名/rest-pose 重定向到 H 骨架后，idle 可接近，但 run/attack 手臂会横向展开或抬起；原因是两套骨架 rest pose（T-pose vs A-pose）、骨骼轴/roll 和 68 vs 103 骨骼差异。当前不作为默认。

## 边界

- 动作风格来自 Homelander 模型，不是原版逐帧动作；
- 若必须逐帧原版动作，需要继续做 rest-pose/骨骼轴向修正或改绑；
- `homelander-style.glb` 未比对/未使用；
- 模型贴图/版权由用户提供，仓库只保留本地副本。

## 截图

`play-homelander-final.jpg`（idle）、`play-homelander-ownrun2.jpg`（run）、`play-homelander-ownattack.jpg`（punch）、`play-homelander-heat.jpg`（Shift+E 热视线）。
