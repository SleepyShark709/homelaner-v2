# 玩家角色还原度优先（2026-10-25）

方案 A 的世界/建筑/AI 扩展暂停。当前只处理**玩家可操作角色**，按单项顺序完成并验证，前一项不通过不进入下一项。

## 顺序与状态

| 顺序 | 问题 | 状态 |
|---|---|---|
| 1 | 玩家一闪一闪/间歇消失 | 第一版已修，自动验证无空帧 |
| 2 | 动作切换不连贯 | 第一版已修；StartSprint/Stop 已缩短，待实机确认 |
| 3 | 攻击无自动锁定/瞬移 | 第一版已实现，6m→1.45m 验证 |
| 4 | 快跑/飞行/攻击无特效 | 第一版程序化速度线 |
| 5 | 人物穿模/局部模型入地 | 未处理 |
| 6 | 热射线键位与 E 起飞冲突 | H 热射线已从默认撤下，`?heat=1` 才启用 |

建筑模型缺失、市民 AI、街区边界、任务链不在此工作流内；不要混入本次修改。

## 实机反馈 2026-10-26 23:16 后的修复

- 攻击后卡动作/浮空：根因是瞬移后玩家停在地面支撑上方约 4 cm，`grounded` 阈值只有 3 cm，状态一直卡在 `jump/Hero_JumpFall`，Space 也被吞掉。现在清理 NaN 支撑高度、瞬移使用当前 Y、落地容差放宽到 12 cm；真实目标攻击探针结束为 `grounded=true, Hero_Idle`，随后 Space 正常跳起。
- 普通跑→快跑的长下蹲：`Hero_StartSprint` 原长 1.405 s，现在 1.4x 播放且 0.34 s 后交叉到 SprintRun；Stopping 限制 0.36 s。
- H 镭射眼确实不是 REA 还原，是作者预览；已默认关闭并从 HUD 撤下，`?heat=1` 才启用。
- F 的标签改为“退出飞行并落地”；探针从 20.47 m 落地到 y=0.47、grounded=true。
- 飞行镜头抖动：相机 boom 撞到建筑时此前每帧直接 snap 到安全点，安全距离变化会抖；现在以 45/s 快速缓动到安全点，只有初始化和瞬移才 snap。飞行位置/速度探针显示贴地飞行 2.2 s 内速度稳定、相机无跳变。
- 2026-10-27 飞行录屏逐帧：角色在直立 IdleFlying 与前倾 FlyForward 之间来回切换，不是镜头。已给飞行选择加 0.35 s 移动记忆、25° 侧向滞回和 900/3600 m/s 前向速度滞回，避免速度/碰撞短暂下降时整组飞行 clip 翻转。新的水平 fly clip 还必须稳定 0.12 s 才会切换，垂直 clip 仍立即响应。
- 攻击时按住方向键不再边走边打：攻击 timeline 期间设置玩家 `attackLocked`，清空水平输入/速度；探针按住 W 挥空拳，攻击期间仅 8 cm 漂移，结束后恢复移动。
- 普通跑↔快跑不再播放长 StartSprint/Stopping montage：Shift 直接 0.12 s crossfade 到 SprintRun，停下 0.15 s 回 Idle，避免下蹲/站立动作跟着位移。
- 2026-10-28：减速惯性降低。保留原加速值，仅在目标速度低于当前速度时使用 1.8x 减速度；探针跑步 10 m/s 停 257 ms/1.19 m，飞行 37.9 m/s 停 529 ms/9.56 m。
- 普通攻击斩击已恢复为原版 `P_NormalAttackSlash` 图集（`T_ky_slash01_4x4`，frames 3..10，0.2 s，加色 sprite）；飞行尘土改为原版 `T_RaP_Smoke_puff_4x4_2k` 烟雾，原程序化蓝色飞行速度线已移除；地面起跑冲击波改用原版 `T_BlastWave` 贴图。其余冲击/远程特效仍是程序化预览。资产清单与后续顺序见 `docs/vfx-recovery.md`。
- NPC/建筑穿模与局部入地尚未处理。

## 第 1 项：闪烁

已修改：

- 所有玩家 skinned mesh 设置 `alwaysSelectAsActiveMesh = true`；
- 保留 `receiveShadows = true`；
- 避免 rest-pose bounding box 在动画姿势离开视锥时整帧剔除。

帧探针：

```text
13 meshes / 96 frames
missing active meshes = 0
hidden/alpha frames = 0
alwaysSelect = true
```

在 idle、walk、jump、fly 下均未发现 active-mesh 缺失。仍需用户实机确认；若仍有闪烁，下一步检查：

1. 是否有重复玩家 mesh 同位置 z-fighting；
2. 阴影/自阴影导致的明暗闪动；
3. 材质透明度或光照切换；
4. 相机近裁剪。

补充帧差验证（headless Chrome，1280×720）：

- 20 帧冻结 idle：逐帧差异 0；
- 30 帧 idle 动画：最大 mean diff 0.059，最多 566 个变化像素；
- 30 帧跑步起步：仅第 1–2 帧有启动位移（17677/9426 像素），之后稳定在 15–41 像素。

没有复现“整帧闪烁/角色消失”。如果用户实机仍复现，优先按上面的 1–4 继续定位。

## 实机反馈（2026-10-26）

用户确认仍会闪，条件明确：

- 按 W+A 向斜前方跑时；
- 攻击完再移动时；
- 同时移动有“一顿一顿、帧率很低”的感觉。

追加修复：

1. `setGroundBlend` / `setFlyBlend` 只启动权重 > 0.001 的组，权重为 0 的组直接 stop；此前 idle/walk/run/direction 多个零权重动画仍在每帧参与。
2. 新激活的步态组从当前主导 clip 的归一化相位启动，而不是第 0 帧，减少 WA 斜跑和攻击后接移动的腿相位跳变。
3. 玩家不再 `receiveShadows`：预览 1024px 阴影图没有角色专用 bias/normalBias，移动/攻击时会产生自阴影 acne 闪烁；角色仍向世界投射稳定阴影。

FPS 探针（headless）：

```text
idle      25.2 fps
WA run    25.2 fps
攻击后 W   23.6 fps
```

所以不是“移动时 CPU 掉帧”，更多是动画相位/自阴影造成的视觉顿挫。仍需实机确认。

### 追加：共面装饰层 z-fighting

`M_ShadowTrim`（身体/头发装饰阴影层）和墨镜镜片是共面 overlay，默认 `zOffset=0`，在斜跑/攻击后视角变化时会出现局部闪烁。

已设置：

```text
M_ShadowTrim -> zOffset=-1, zOffsetUnits=-1
MI_Sunglasses_003 / M_GlassLens_master_Black -> zOffset=-1, zOffsetUnits=-1
```

探针确认 2 个 `M_ShadowTrim` 和 4 个墨镜 primitive 都已生效。若闪烁是局部黑/白斑，这一项应优先观察。

## 实机录屏 2026-10-26 01:19（5–8s 启动走路）

逐帧抽帧确认：启动走路时角色会在**直立/跑步**两种全身姿势间跳变，不是单纯掉帧。根因定位到地面 locomotion 的多组权重混合：

```text
Hero_Idle + Hero_Walk + Hero_SprintRun + ALS_N_Walk_FL ...
```

多组同时以权重作用于同一骨架时，Babylon 的组权重没有形成预期的 UE BlendSpace 效果，表现为“跑动动作里加入了别的动作”。快跑切回普通跑后，组的播放长度/相位也随权重组变化，看起来像循环被截成 1-3-1。

已改为**单步态组**：

```text
Idle / Walk / SprintRun / SprintSuper 每次只选一个
状态切换用 0.2s group crossfade
播放速度显式设置为 speed / sampleSpeed
```

旧的 2D 多组混合默认路径已移除。

自动回归探针在 idle → 走 → 冲刺 → 松开 Shift → 停止的 524 帧里：

```text
非 crossfade 帧中同时活跃的步态组最大值 = 1
violations = 0
```

这直接保证不会再出现多个全身步态抢骨架的“插入别的动作”。

启动走路也不再经过 Idle→Walk→Run 两次连续 crossfade：默认 W 移动直接进入 SprintRun，只有 Alt 走模式才选择 Walk。这样录屏 5–8 秒处只发生一次 Idle→Run 过渡。

SprintRun/SprintSuper 边界加入滞回：17.25 m/s 进入 Super，14.5 m/s 才退回 Run，避免速度在 16.75 附近来回切换导致循环重启。

跳跃链探针（站立跳）：

```text
ALS_N_Jump -> Hero_JumpFall -> Hero_JumpLand
89 帧，empty active groups = 0，最高 y=4.47
```

没有 rest/T-pose 空帧。

跑动跳探针（W 移动中起跳，126 帧）：

```text
clips = ALS_N_Jump / Hero_JumpFall / Hero_JumpLand
empty active groups = 0
peak y = 4.46
```

B1 的 Shift 跑动跳单独覆盖 `Hero_JumpSpeed`。

攻击结束保留 attack clip 到下一次 locomotion 更新；如果攻击组已停止，crossfade 会立即切到移动目标，而不是从空来源淡入导致骨架回到 rest/T-pose。攻击结束探针现在 `fades=[]`，直接出现一个 `Hero_SprintRun:1.00` 组。

攻击进入也不再 `stop()` 全部动画并 `returnToRest()`；现在从当前 locomotion 姿势 0.1s crossfade 到 attack clip，攻击命中仍正常。

飞行同样改为单组：垂直 FlyFastUp/FlyUp/FlyDown/FastDown/BulletDive 优先，否则按 back/side/forward 速度和方向选一个，不再同时混合 7 个全身飞行组。

冲刺停止现在会记住“刚从冲刺状态来”，使用 `Hero_Stopping_Sprint`，而不是因为松开 Shift 后状态已清零而误用 `Hero_Stopping_WalkRun`。探针：`SprintRun -> Stopping_Sprint -> Idle`。

## 第 3 项：攻击自动锁定/瞬移（第一版）

`Combat.begin` 会选择镜头前方最近的存活目标：

```text
近战 12 m / 远程 80 m
按距离和朝向评分
检查墙体遮挡
```

- 面向目标，并同步 `input.yaw`；
- 近战在地面时尝试瞬移到目标外侧 1.45 m；
- 瞬移路径用玩家胶囊 AABB 扫墙，墙体阻挡则不穿墙；
- 近战/远程的命中方向优先指向锁定目标中心。

自动锁定探针：8 m 前放置真实市民，按 J 后市民被击杀；因落点被墙阻挡，玩家只从 7.98 m 接近到 4.47 m。开阔地会完成 1.45 m 瞬移。瞬移落点现在按 1.45/2.0/2.6/3.2 m 依次尝试，取第一个玩家盒扫墙通过的点；全被挡则保持原位，不穿墙。

锁定准星：每帧预览 12 m 内最近目标，屏幕投影为金色圆环 + 距离文字；目标死亡/离开视野隐藏。探针 4 m dummy：可见，位置 679.97/416.22 px，显示 `4.0 m`；死亡后 hidden。

干净 dummy 探针（只有该目标、6 m 正前方）：

```text
瞬移前距离 = 6.00 m
按 J 后 300ms（命中帧之前）= 1.45 m
```

之前测到 5–6 m 是因为目标死亡后尸体被击退，测的是“玩家到尸体”的距离，不是瞬移失败。

补充验证 clip 时长没有被导入器减半：

```text
Hero_SprintRun: glTF duration 0.567s
原版 notify: PlayFootStepR 0.264s / PlayFootStepL 0.556s
```

两者吻合，说明动画本身不是 2 倍速。快跑松开 Shift 后探针看到 `Hero_SprintRun` 的 speedRatio 回到 1.11，masterFrame 从 0 完整走到 34 再回 0，循环周期约 0.51s，不是 1→3→1 截断。旧代码的多组权重加 stale speedRatio 才会造成那个观感。

## 第 4 项：快跑/飞行/攻击特效（第一版）

新增程序化预览 VFX：

- 地面速度 > 12 m/s：金色竖向速度线；
- 飞行：蓝色速度线；
- 攻击开始：3 条蓝色挥击线；
- 上限 96 条，按生命周期缩放/销毁，`reset()` 清空。

这些是 Web 预览特效，不是原版 UE 粒子系统。强制速度探针能生成 6 条 streak。

![速度线](../research/screenshots/vfx-streaks5.jpg)

## 第 5 项：热射线键位

热射线已从 `Shift+E` 改为 **H**。E 继续负责起飞/上升和地面蓄力，不再与热射线冲突。

探针：

```text
按住 H -> heatActive=true, action=热视线, charge=0
按住 E -> heatActive=false, charge=0.358
```

HUD/帮助文本已同步。

## 验收方式

- `?view=play` 硬刷新后观察 idle/走/跑/跳/飞；
- 若复现，记录：静止还是移动、全身还是局部、是否随镜头/阴影变化；
- 通过后才进入第 2 项“动作切换”。
