# 可玩原版基线 B1：原街区 + 原角色 + 原输入语义

日期：2026-10-25。入口：`http://127.0.0.1:5178/?view=play`。

这是**可玩切片**，不是完整 UNDEFEATED 移植。它第一次把原角色放回恢复后的原版街区，并用原高度场和原输入语义驱动。B1 之后仍需补攻击、AI、车辆、任务、Boss、菜单/存档、完整动画状态机和原版同机位对照。

## 本次接入

- 世界：`MainLevel + ResidentialArea1` 静态装配，3,782 个源对象组件、144 块地形；资源/纹理失败 0。
- 角色：`/assets/character/hero.gltf`，原身体/头发/墨镜三套网格与骨架，18 段原动画；保留原骨架与比例。
- 地面：144 块原 Landscape 高度场逐点采样（`TerrainHeightfield`），不是旧的单平面地面。
- 碰撞：从恢复后的静态对象 TRS 与 asset bounds 生成 1,432 个 AABB 代理（2,171 个对象中跳过 731 个过小、8 个过大）；这是可玩性代理，不是原 cooked PhysX。
- 相机：第三人称跟随，拖动鼠标偏航/俯仰；行走 5.5 m、飞行 8 m 距离。
- 输入：Space 地面跳跃 / 空中开飞 / 飞行退飞；E/Q 升降；地面按住 E 约 1 秒自动开飞；Shift 冲刺；Alt 慢行；F 预留互动；R 为调试回出生点。
- 动画：`Hero_Idle`、`A_ThirdPersonRun`、`Hero_IdleFlying`、`Hero_FlyFastSprint` 随状态切换；B1 只验证前三条实际播放。
- 出生点：沿用此前恢复的 ResidentialArea1 最近道路样条中点 `(50, 0.43, 1.37)`，不是原 `PlayerStart`；MainLevel `BP_RespawnAndSpawnPoint` 的 x/z 作为备用。场景内说明保留该来源差异。

## 已实测

浏览器探针 [probe-play-b1.js](../scripts/probe-play-b1.js) 在 1280×720 无头 Chrome 中执行：

- 地面待机：`Hero_Idle`，grounded=true；
- 按 W 0.7 秒：移动 7.04 m，速度 10 m/s，`A_ThirdPersonRun`；
- Space：跳起约 6.38 m（预览跳跃参数），随后空中 Space 进入飞行；
- 飞行中按住 E 0.45 秒：上升 14.5 m（速度 40 m/s）；
- 按住 Q 0.7 秒：下降 8.33 m；
- 飞行中 Space：退出飞行并落回地面；
- 全程 `objects=3782`、`terrain=144`、资源/纹理失败 0；FPS 是无头浏览器读数，不能与原游戏或正常桌面浏览器比较。

单测 [test-play-controller.mjs](../scripts/test-play-controller.mjs) 5/5：地面/行走方向、跳跃/开飞/退飞、地面蓄升 1 秒边界、冲刺/慢行/升降、R 重置。

截图：[play-b1.jpg](../research/screenshots/play-b1.jpg)。记录：[playable-b1-validation.json](../research/world-recovery/playable-b1-validation.json)。

## 明确近似与缺口

- 跳跃冲量、重力曲线来自旧原型预览值；原始 `Character.Jump` 曲线尚未对照。
- 建筑/道具碰撞为 AABB 代理；没有原 PhysX、屋顶/悬挑/凹形精确碰撞，相机也无遮挡碰撞。
- 地图中烘焙的参考姿态市民被隐藏（B1 没有人口/AI），不是已经实现原版市民。
- 没有攻击、右键远攻、热视线、自由破坏、车辆、市民、任务、Boss、菜单/存档。
- 角色阴影、IK、蒙太奇/通知、完整 HeroAnimBP 状态机未实现。
- 尚未与原程序做同机位/同输入对照。

## 复现

```powershell
npm run test:play
npm run capture:play
```

`capture:play` 会启动无头 Chrome、执行浏览器探针、更新 `playable-b1-validation.json` 并截图。需要 Node ≥24；系统 Node 18 不能运行这些脚本。

材质/世界证据仍见 [world-recovery.md](world-recovery.md)。原游戏安装保持只读；B1 没有修改或读取原游戏存档。
