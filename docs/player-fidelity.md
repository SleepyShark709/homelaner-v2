# 玩家角色还原度优先（2026-10-25）

方案 A 的世界/建筑/AI 扩展暂停。当前只处理**玩家可操作角色**，按单项顺序完成并验证，前一项不通过不进入下一项。

## 顺序与状态

| 顺序 | 问题 | 状态 |
|---|---|---|
| 1 | 玩家一闪一闪/间歇消失 | 已做第一轮修复，等待实机确认 |
| 2 | 动作切换不连贯 | 待处理 |
| 3 | 攻击无自动锁定/瞬移 | 待处理 |
| 4 | 快跑/飞行/攻击无特效 | 待处理 |
| 5 | 人物穿模/局部模型入地 | 待处理 |
| 6 | 热射线键位与 E 起飞冲突 | 待处理；候选 H |

建筑模型缺失、市民 AI、街区边界、任务链不在此工作流内；不要混入本次修改。

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

攻击结束保留 attack clip 到下一次 locomotion 更新；如果攻击组已停止，crossfade 会立即切到移动目标，而不是从空来源淡入导致骨架回到 rest/T-pose。攻击结束探针现在 `fades=[]`，直接出现一个 `Hero_SprintRun:1.00` 组。

攻击进入也不再 `stop()` 全部动画并 `returnToRest()`；现在从当前 locomotion 姿势 0.1s crossfade 到 attack clip，攻击命中仍正常。

飞行同样改为单组：垂直 FlyFastUp/FlyUp/FlyDown/FastDown/BulletDive 优先，否则按 back/side/forward 速度和方向选一个，不再同时混合 7 个全身飞行组。

冲刺停止现在会记住“刚从冲刺状态来”，使用 `Hero_Stopping_Sprint`，而不是因为松开 Shift 后状态已清零而误用 `Hero_Stopping_WalkRun`。探针：`SprintRun -> Stopping_Sprint -> Idle`。

补充验证 clip 时长没有被导入器减半：

```text
Hero_SprintRun: glTF duration 0.567s
原版 notify: PlayFootStepR 0.264s / PlayFootStepL 0.556s
```

两者吻合，说明动画本身不是 2 倍速。快跑松开 Shift 后探针看到 `Hero_SprintRun` 的 speedRatio 回到 1.11，masterFrame 从 0 完整走到 34 再回 0，循环周期约 0.51s，不是 1→3→1 截断。旧代码的多组权重加 stale speedRatio 才会造成那个观感。

## 验收方式

- `?view=play` 硬刷新后观察 idle/走/跑/跳/飞；
- 若复现，记录：静止还是移动、全身还是局部、是否随镜头/阴影变化；
- 通过后才进入第 2 项“动作切换”。
