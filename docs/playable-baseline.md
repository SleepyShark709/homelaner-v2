# 可玩原版基线 B1/B2/B3：原街区、原角色、原输入、战斗与动态碰撞

日期：2026-10-25。入口：`http://127.0.0.1:5178/?view=play`；可用 `&district=TitleMenuLevel` 等主世界关卡切换检查目标（预览人口只在 ResidentialArea1 加载）；`&startup=1` 先执行原 17 包启动链再进入可玩模式。

这是**可玩切片**，不是完整 UNDEFEATED 移植。B1 把原角色放回恢复后的原版街区，用原高度场和原输入语义驱动；B2 增加预览人口、原战斗动画/弹道和相机遮挡收缩。攻击命中、AI、任务、Boss、菜单/存档、完整动画状态机和同机位对照仍需继续。

## 本次接入

- 世界：`MainLevel + ResidentialArea1` 静态装配，3,782 个源对象组件、144 块地形；资源/纹理失败 0。
- 角色：`/assets/character/hero.gltf`，原身体/头发/墨镜三套网格与骨架，18 段原动画；保留原骨架与比例。
- 地面：144 块原 Landscape 高度场逐点采样（`TerrainHeightfield`），不是旧的单平面地面。
- 碰撞：从恢复后的静态对象 TRS 与 asset bounds 生成 1,432 个 AABB 代理（2,171 个对象中跳过 731 个过小、8 个过大）；这是可玩性代理，不是原 cooked PhysX。相机偏移会对附近 AABB 做收缩，避免穿墙。所有存活预览 actor（含市民、车辆、报刊箱）的 `solidBoxes` 每帧加入玩家动态碰撞。
- 相机：第三人称按原 `PlayerBP` `CameraBoom` 的 `TargetArmLength=400 cm`、`SocketOffset=(0,50,90) cm`、`RelativeLocation Z=70 cm` 校准，并使用原 `CameraLagSpeed/RotationLagSpeed=15` 做相机位置/朝向平滑；弹簧回弹、碰撞后处理和输入曲线仍是近似。
- 输入：Space 地面跳跃 / 空中开飞 / 飞行退飞；E/Q 升降；地面按住 E 约 1 秒自动开飞；Shift 冲刺；Alt 慢行；F 预留互动；R 为调试回出生点。按 P07，Shift 只有与移动输入同时存在才进入冲刺；松开 Shift/停止移动即解除，Alt 慢行取消冲刺。
- 动画：`Hero_Idle`、`A_ThirdPersonRun`、`Hero_IdleFlying`、`Hero_FlyFastSprint` 随状态切换；B1 实测前三条。
- 出生点：旧原型街区局部坐标 `(50, 1.37)` 加上 city manifest `originUE [-10000,-55000,0]` cm，得到恢复世界 `(-50.0, -548.63)`，位于 ResidentialArea1 的实际公寓街区；仍不是原 `PlayerStart`。MainLevel `BP_RespawnAndSpawnPoint` 的 x/z 作为备用。
- B2 预览人口：14 个 actor（8 市民、3 Sedan、3 报刊箱），使用原 citizen/vehicle/NewspaperBox 网格与动画；位置/短路线来自旧原型 `population-manifest.json`，并按同一 `originUE` 平移到恢复世界，不是恢复出的原版 AI、导航或交通。
- B2 战斗：接入原 14 段动作时间轴与攻击动画；左键/J 四段近战，右键/K 远程拳波，Shift 强攻；弹体 150 m/s、4 s 寿命。当前用 `baseline` 伤害模式：只有强力攻击可摧毁车辆，市民/道具伤害与自由破坏仍后置。
- 热视线在 B1/B2 强制关闭：E 仍是原上升/地面蓄升键；`Combat` 以 `{heatVision:false}` 构造，避免抢占输入。

## 已实测

浏览器探针 [probe-play-b1.js](../scripts/probe-play-b1.js)：

- 地面待机：`Hero_Idle`，grounded=true；
- 按 W 0.7 秒：移动 6.44 m，速度 10 m/s，`A_ThirdPersonRun`；
- Space：跳起约 6.11 m（预览跳跃参数），随后空中 Space 进入飞行；
- 飞行中按住 E 0.45 秒：上升 13.83 m（速度 40 m/s）；按住 Q 0.7 秒下降 7.33 m；
- 飞行中 Space：退出飞行并落回地面；
- 全程 `objects=3782`、`terrain=144`、资源/纹理失败 0。

B2 探针 [probe-play-b2.js](../scripts/probe-play-b2.js) / [probe-play-b2-hit.js](../scripts/probe-play-b2-hit.js)：

- 近战：`近战连击` + `Hero_Attack1`，结束后回到 `待命`/`Hero_Idle`；
- 远程：`远程攻击` + `Hero_LongFistForce_L`，生成 1 个弹体；
- 强力远程命中预览车辆：剩余 actor 14 → 11、hits 0 → 3、destroyed 0 → 3，最近车辆 alive=false；
- 按住 E：`heatActive=false`，地面蓄升 charge 正常累加；
- 相机位置不在任何 AABB 内（cameraInside=false）。

单测 [test-play-controller.mjs](../scripts/test-play-controller.mjs) 7/7：地面/行走方向、跳跃/开飞/退飞、地面蓄升 1 秒边界、冲刺/慢行/升降、Shift 必须配合移动输入、动态车辆 AABB 阻挡、R 重置；原 14 段战斗时间轴由 `npm test` 覆盖。

截图：[play-b1.jpg](../research/screenshots/play-b1.jpg)、[play-b2.jpg](../research/screenshots/play-b2.jpg)、[play-b3.jpg](../research/screenshots/play-b3.jpg)。记录：[playable-b1-validation.json](../research/world-recovery/playable-b1-validation.json)、[playable-b2-validation.json](../research/world-recovery/playable-b2-validation.json)。

## B3/B4 进展

- 修正旧原型街区局部坐标：`originUE [-10000,-55000,0]` cm 使原先的 `(50,1.37)` 实际对应恢复世界 `(-50.0,-548.63)`；spawn 和 14 个预览 actor 一起平移，截图从空旷主路变为 ResidentialArea1 的实际公寓/街道（`play-b3.jpg`）。
- 预览所有存活 actor（含市民、车辆、报刊箱）的 `solidBoxes` 每帧加入玩家动态 AABB；单测新增“Shift 需移动输入”“车辆 AABB 阻挡行走”，目前 7/7。
- 新增 `?district=` 参数：对 MainLevel + 指定主世界关卡做装配与碰撞代理，出生点取该关卡 bounds 中心附近的地面空闲点；预览人口仍只在 ResidentialArea1 加载。`play-titlemenu.jpg` 是 TitleMenuLevel 的实际浏览器检查，不是原版开始画面。
- 新增可选 `?population=original` 检查：`tools/asset-pipeline/export-citizen-spawns.mjs` 从原版 `CitizenWayPoint` 取玩家附近 12 个 `BP_CharaSpawnPoint`，转成恢复世界坐标，生成 `population-original-citizens.json`；路线只是最近邻预览。12 个最近出生点会挤在玩家附近，且原版 spawner 不会同时生成全部市民，所以**默认仍用预览人口**，该模式只用于位置检查（`play-original-citizens.jpg`）。

## 多区可玩检查

| 区域 | 对象 | 地形 | 失败 | 截图 |
|---|---:|---:|---:|---|
| ResidentialArea1 | 3,782 | 144 | 0 | `play-b3.jpg` |
| DownTown | 4,274 | 144 | 0 | `play-downtown.jpg` |
| Park | 4,105 | 144 | 0 | `play-park.jpg` |
| TitleMenuLevel | 3,469 | 144 | 0 | `play-titlemenu.jpg` |
| 17 包启动链（`startup=1`） | 8,824 | 144 | 0 | `play-startup.jpg` |

每区都使用同一原角色、原输入、原高度场和该区静态 AABB 碰撞代理；除 ResidentialArea1 外没有预览人口/战斗目标。记录见 [playable-districts-validation.json](../research/world-recovery/playable-districts-validation.json)。

## 原启动链可玩模式

`?view=play&startup=1` 先由 `OriginalStreaming` 执行恢复出的 17 包/12 步启动加载，再构建**全部启动关卡**的静态 AABB、生成原角色和预览人口。实测：

- 8,824 个源对象、144 块地形、0 资源/纹理失败；
- B1 浏览器探针通过：移动 6.68 m、跳跃约 6.66 m、E 上升 14.17 m、Q 下降 9.00 m；
- 截图 `play-startup.jpg`。

这是“原启动链 + 可玩角色”的整合检查，不代表原版运行时流送状态机、可见性或性能已等价。
- 已审计原版 `CitizenWayPoint` 解码数据：2,806 个 `BP_CharaSpawnPoint`、85 个 spline 路径 actor、559 个 child waypoint；最近 spawn 位置与玩家街区对齐（100 m 内 897 个）。但 UAssetAPI 的 actor/component Outer 链与 spline 局部坐标转换尚未闭合，本轮不把它们替换进 Population，避免用未核清坐标冒充原版路径。详见 [citizen-waypoint-audit.zh-CN.md](../research/world-recovery/citizen-waypoint-audit.zh-CN.md)。

## 明确近似与缺口

- 预览人口的位置与短路线来自旧原型清单，不是已恢复的原版 AI/导航/交通/市民状态机；不能把它当作原版城市活动。
- 战斗只接入 `baseline` 伤害策略：强力攻击可毁预览车辆；市民/道具伤害、自由破坏、无惩罚规则和热视线属于后续阶段。
- `?population=original` 是检查模式：12 个最近原始 spawn 点会聚集在玩家附近，路线是最近邻预览；原版 spawner 生成节奏/数量/导航未恢复，所以不能当默认人口。
- 预览人口只加载于 ResidentialArea1；DownTown/Park/TitleMenuLevel 没有市民、车辆、AI、任务或可攻击目标。
- 玩家动态碰撞已覆盖预览市民/车辆/报刊箱；原版 actor 胶囊形状与非统一骨骼碰撞未恢复。
- 跳跃冲量、重力曲线来自旧原型预览值；建筑/道具碰撞是 AABB 代理，不是原 PhysX；相机 boom 已按原参数校准，但 lag/弹簧/碰撞后处理仍是近似。
- 地图中烘焙的参考姿态市民被隐藏，预览市民不是原地图 AI；角色阴影、IK、蒙太奇/通知、完整 HeroAnimBP 状态机未实现。
- 尚未与原程序做同机位/同输入对照。

## 复现

```powershell
npm run test:play
npm run capture:play
npm run capture:play:b2
```

`capture:play` 执行 B1 探针并更新 `playable-b1-validation.json`；`capture:play:b2` 执行强力载具命中探针并截图。两者都需要 Node ≥24 与本机 Chrome/Edge。

材质/世界证据仍见 [world-recovery.md](world-recovery.md)。原游戏安装保持只读；B1/B2 没有修改或读取原游戏存档。
