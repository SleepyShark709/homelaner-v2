# UNDEFEATED 还原状态（2026-10-25）

本文件是当前实现与证据的入口。详细剩余项见 [todo-restoration.md](todo-restoration.md)，可复现命令和长期环境事实见 [AGENTS.md](../AGENTS.md)。

当前执行范围是 [方案 A：单城区自由沙盒](plan-a-sandbox.md)：一个完整街区、移动/飞行、市民/车辆/道具、可攻击市民并死亡/重生、基础战斗/破坏、沙盒 HUD；任务链、剧情、Boss、全城和存档暂不做。

## 结论先行

这不是完整移植，也不是视觉等价。当前是 **原始游戏确定性还原 + 可玩切片**：

- 原版角色、骨架、49 段原版动画、原版输入/移动/攻击时间轴；
- 原版脚步/挥击/命中/破坏/强力/空中冲刺/飞行风噪；
- 同机位位置、朝向、FOV 90；
- 同机位整体 luma 已对齐到原版 +0.30；
- 起点店面材质/小地图 HUD 已按恢复参数接入。

Gate 3（baked lightmap、局部石材/雨棚、完整 HUD 状态机）与 Gate 4（精确 BlendSpace 轴值、全部 transition 条件、notify 行为）仍未完成。

## 门禁状态

| Gate | 状态 | 证据 |
|---|---|---|
| 1 真实 gameplay transform | 完成 | `WBP_TitleSinboard_C:GameStartEvent()` + 一次 `InputDone()`；pawn `(-311.999,7473.891,167.150)`，cam `(-361.999,7073.891,327.150)`，FOV 90 |
| 2 同机位相机 | 完成 | `?at=-3.12,74.739&yaw=0&exact=1&cam=-3.62,3.2715,70.739&camyaw=0&campitch=-0.1745&fov=90` |
| 3 光照/材质/天空/HUD | 进行中 | 整体 luma Web 56.03/30.42 vs 原版内容区 55.73/31.34；店面 5 子网格材质已映射；lightmap 未应用；石柱/雨棚局部仍不同 |
| 4 动画/状态逻辑 | 进行中 | 49 段原版动画、24 段含 notify（116 事件/39 名称）、33 条 crossfade 时间、主要 group crossfade 已实现；地面方向轴/垂直连续混合/状态条件未完成 |

## 当前可玩切片

```text
?view=play
```

包含：

- 原版 `hero.gltf`（93 骨骼，49 动画）；
- 地面速度/方向加权、飞行 2D 采样、JumpFall/Fast、AirAttack；
- 秒级 group crossfade（默认 .2 s、跳跃 .55 s、StopSprint .25 s、Landing .1/.25 s）；
- 原版脚步/攻击/命中/强力/风噪音频（`?audio=0` 关闭）；
- 原版小地图纹理/边框/玩家图标（状态机仍是预览）；
- 原版同机位默认相机与预览曝光/SSAO 校准。

## 关键证据

- 同机位对照：[comparison-latest.jpg](../research/runtime-observation/comparison-latest.jpg)
- 同机位数值：[same-camera-latest.json](../research/world-recovery/same-camera-latest.json)
- 店面材质：[storefront-meshes.json](../research/world-recovery/storefront-meshes.json)
- 动画导入：[locomotion-import.json](../research/world-recovery/locomotion-import.json)、[directional-import.json](../research/world-recovery/directional-import.json)、[fly-directional-import.json](../research/world-recovery/fly-directional-import.json)、[fly-vertical-import.json](../research/world-recovery/fly-vertical-import.json)
- Notify：[notify-times.json](../research/world-recovery/notify-times.json)
- Transition：[animbp-transition-timing.json](../research/world-recovery/animbp-transition-timing.json)
- 音频清单：[footstep-sound-manifest.json](../research/world-recovery/footstep-sound-manifest.json)、[combat-sound-manifest.json](../research/world-recovery/combat-sound-manifest.json)、[impact-sound-manifest.json](../research/world-recovery/impact-sound-manifest.json)、[ability-sound-manifest.json](../research/world-recovery/ability-sound-manifest.json)、[flight-wind-manifest.json](../research/world-recovery/flight-wind-manifest.json)
- 自动验收：[validation-summary.json](../research/world-recovery/validation-summary.json)

## 明确未完成

### Gate 3

1. 应用真实 baked lightmap/ShadowMap；`HQ_Lightmap0_138` 的 UModel 解码仍是 chart 色，不能使用。
2. 恢复 `mask_grunge`/Contrast/Greunge shader math；当前 brick/trim 是派生 tint 校准。
3. 石柱/雨棚局部亮度、天空/远景山体材质。
4. 小地图完整状态机、敌人/Boss/飞行环/城市破坏图标与 active/completed 过滤。
5. thin-instance 前景不可拾取；逐材质屏幕采样工具暂不可用。

### Gate 4

1. 地面方向轴：当前 controller orient-to-velocity，ALS 方向样本只解析 forward。
2. 垂直飞行仍是阈值切换，不是完整 FlyingUpDown 连续混合。
3. 33 条 transition 中仅主要边有秒级 crossfade，其余仍用默认 .2 s。
4. notify 行为：脚步/挥击/命中/强力/风噪已接；尘土、移动、镜头/音效、finish 行为等未接。
5. `JumpFallFast` 只在 < -35 m/s 使用，普通跳跃为 `JumpFall`；如与原程序逐帧不符，需要继续核对。

## 可复现验证

使用 bundled Node 24：

```powershell
$env:PATH = 'C:\Users\Shark\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin;' + $env:PATH
npm run typecheck
npm run build
npm test
npm run verify:locomotion
node scripts/audit-root-motion.mjs
npm run preview
```

同机位截图与数值：

```powershell
node scripts/measure-luma.py research/screenshots/play-window-emissive.jpg
```

## 断言边界

- 不声称完整移植、视觉等价或逐帧动画等价；
- 原版资产保持本地/Git 忽略，源与派生资产有独立 manifest；
- 预览曝光/SSAO、brick tint、window emissive、音频分层都是校准/近似，不是已恢复的原版 shader/Cue 图。
