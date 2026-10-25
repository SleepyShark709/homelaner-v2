# UNDEFEATED 原版还原：剩余 TODO 总表

日期：2026-10-25  
当前 Git：`17a2342`（本表随下一次提交更新）  
目标顺序：**原版还原 A → Web 扩展 B**。B（热视线 / 自由破坏 / Homelander）在 A 的门禁通过前冻结。

图例：`P0` 阻塞还原验收；`P1` 还原必需但可在同机位可见性之后；`P2` 完整度/性能/收尾。

## 0. 已建立的事实与当前状态

### 已完成

- 原程序可启动并进入真实 gameplay：UE4SS 调 `WBP_TitleSinboard_C:GameStartEvent()`，随后**只调用一次** `InputDone()`。
- 真实 gameplay 起点：
  ```text
  pawn = (-311.999, 7473.891, 167.150) cm
  cam  = (-361.999, 7073.891, 327.150) cm
  rot  = (-10, 90, 0)
  fov  = 90.000  (PlayerCameraManager:GetFOVAngle)
  ```
- 同机位 Web：
  ```text
  player = (-3.12, 1.6715, 74.73891) m
  camera = (-3.62, 3.2715, 70.73891) m
  ```
  对应 `?view=play&startup=1&at=-3.12,74.739&yaw=0&exact=1&cam=-3.62,3.2715,70.739&camyaw=0&campitch=-0.1745&fov=90`。
- 同机位对照：`research/runtime-observation/comparison-live-gameplay-start-final.jpg`。
- 门/窗材质：`-Window_mat`、`Tilable_metal_TintC_Inst` 已按恢复参数投影，不再是中性灰；玻璃已使用原版 `clouds.png` 云层 emissive（u/v=.2），但 `mask_grunge_tileable`、Contrast/Greunge 数学仍未实现。
- 原版 minimap：`T_StaticMinimap_Tex`、`map250` 边框、`T_PlayerIcon`、最近 8 个任务图标已接入，默认 HUD 即 minimap；`?hud=help` 显示自制检查面板；`?minimap=all` 可检查全部 21 个触发点。已从 `DT_MinimapIcon` 恢复 14 个原版图标纹理（`research/world-recovery/minimap-icon-manifest.json`，详见 [minimap-recovery.md](minimap-recovery.md)），当前 fire/material 类用橙色/青色 canvas tint 预览；active/completed 图标状态机、敌人/Boss/飞行环放置仍未恢复。
- 亮度对照（同一建筑区域）：
  ```text
  原版 mean=55.8 std=31.3
  Web 未校准 86.1/41.7
  Web exposure .55 + default SSAO mean=55.6 std=30.1
  加入原版 clouds 云层后 mean=57.8 std=31.0（原版 55.8/31.3）
  ```
  exposure .55 与 SSAO 是预览校准，不是 UE 自动曝光/AO/lightmap 重建。
- UE4SS 工具与流程：`tools/runtime/ue4ss/README.md`、`LightDump/`、`CoordDump/`。
- 原版动画状态机资产已解码：`HeroAnimBP`、`HeroABS_MoveGround/Flying/JumpFallLoop/AirAttack`。记录见 `docs/animation-state-recovery.md`。

### 当前已知缺口（一句话）

同机位构图/亮度已接近，但**原版光照/材质、完整 HUD、动画面部/状态机、AI/车辆/任务/物理、全关卡流送都没有完成**。不能称为完整还原或迁移成功。

## 1. P0：Gate 3 视觉/场景还原

### 1.1 建筑雨棚/檐口与石材明暗

- [ ] 确认开始建筑（CommercialArea `SM_MERGED_Building_2_01_9`）雨棚/檐口/门框对应的实际 mesh slot 与材质。
- [ ] 还原雨棚底面、柱脚、石材接缝的环境遮蔽/阴影，不新增猜测的暗面。
- [ ] 对照原版同机位截图逐块修正；验收标准：同机位同尺寸截图的主要轮廓、玻璃、金属框、檐口不再存在明显色差/缺失。
- 参考：原版实抓 `research/runtime-observation/original-gameplay-start-final.png`；对照图上方路径。

### 1.2 原版 MainLevel 光照 / 自动曝光 / Lightmap

- [x] 已确认 `MainLevel_BuiltData` 内含 464 个 LightMapTexture2D 和 198 个 ShadowMapTexture2D，并成功导出 `HQ_Lightmap0_16` 样本；起始建筑所在的 `CommercialArea_BuiltData` 另有 76 个 LightMapTexture2D / 25 个 ShadowMapTexture2D，76 张已全部导出，清单 `research/world-recovery/lightmap-export-inventory.json`。清单见 `research/world-recovery/lightmap-inventory.json`，详见 [lighting-recovery.md](lighting-recovery.md)。
- [ ] 从 MainLevel/CommercialArea 的 StaticMeshComponent 提取 LightMapIndex、LightMapCoordinateIndex、UV scale/bias，定位起始建筑对应的 lightmap。gameplay 中 `tools/runtime/ue4ss/LightmapProbe` 已确认 `LODData` 长度 1，但 `LODData[0]` 的 fields 全为 nil（只有 `GetStructAddress()` 数值地址），Lua 反射不到 `FLODData/FLightMapRef` 内部引用；且 `comp.LightMap` 地址与当前 510/900 个 `LightMapTexture2D` 对象都不匹配，说明它是 FLightMap 包装对象而非纹理。已用外部 ReadProcessMemory 扫描 `LODData:GetArrayDataAddress()` 前 4096 字节，对 3436 个已加载 `LightMapTexture2D` 地址 0 命中，说明 LODData 不是平铺 lightmap 指针数组。UV 梯度分析给出候选 `HQ_Lightmap0_138`（TEXCOORD_2, flipV）；StandardMaterial lightmap 诊断显示色带确实对齐门框/柱础/玻璃分格，但导出 PNG 是紫绿粉色块而非中性光照；DDS 为 1024×1024 DXT5、SRGB=false，尝试 RGBE 解码得到黑白噪声。说明需要 Lightmass 运行时解码或 `FLightMap2D` 数据，不能直接使用图片。下一步需 SDK/`FLightMap2D` 内部读取。建筑 glTF 已有 TEXCOORD_2/TEXCOORD_3 两个 packed UV 候选，TEXCOORD_1 是常量不可用。
- [ ] 导出/绑定 mesh lightmap UV1，实现原版 lightmap 采样，而不是继续用 `LightingTest` 子关卡参数或全局 SSAO 冒充。
- [ ] 研究 UE4 自动曝光（AutoExposure 1..8）与 Bloom 2.5 的真实来源：`LightingTest` 参数已记录但**不是** MainLevel 结论。
- [ ] 评估 Web 端可实现的 lightmap/AO 投影；优先使用原版数据，不用全局 SSAO 冒充。
- [ ] 当前 `exposure=0.55`、默认 SSAO 只是同机位亮度对齐，必须保留“预览”标签，不能作为光照还原完成证据。
- 已知工具：`tools/runtime/ue4ss/LightDump`、`research/runtime-observation/original-live-audit.zh-CN.md`。

### 1.3 天空/雾/后处理

- [ ] 恢复 MainLevel 实际 Sky/Atmosphere/Fog/PostProcess（不是仅 sky 贴图）。
- [ ] 原版标题/开始画面中的高光、反射、玻璃、Bloom 在 gameplay 的实际参数。
- [ ] 评估 Babylong DefaultRenderingPipeline/SSAO/SSR；任何预览效果必须明确 provenance。
- 已知：`M_Sky_Panning_Clouds2_Inst`、`sky-material-manifest.json`；原版雾/曝光仍缺。

### 1.4 世界内容完整性

- [ ] 流送所有 41 张 map / 子关卡，而不是当前 17-package startup 静态快照。
- [ ] 补齐 thin-instance 物体：长椅、树、广告牌、路灯、栏杆、街道家具、车辆、行人；不能只 materialize 少量。
- [ ] 检查所有材质的 shader 投影缺口（`material-manifest.json`、`unresolved`/`unsupported`），逐项恢复。
- [ ] 检查地形/道路/水面/碰撞体与原始 Landscape。
- [ ] 保持 `public/assets/world` 等派生资产本地、Git 忽略；源身份/生成清单继续维护。

### 1.5 原版 HUD / minimap 完整化

- [ ] 恢复 `NewMiniMap_Widget` 的真实布局：底图缩放/偏移、边框状态着色、玩家图标、active quest/事件图标。
- [ ] 当前最近 8 个任务图标是预览；需要从原版 quest state/DataTable 动态取 active/inactive/completed。
- [ ] 恢复 HUD 其余元素：HP/能力/等级/连击/任务/敌人/Boss/锁定/提示/暂停/标题。
- [ ] 恢复 `M_MiinMapChangeVisualizer` / `M_MiinMapVisualizer` 参数，而非生成的 outer-rim tint。
- [ ] 确保 UI 分辨率/DPI 与原始 1296×759 窗口内容区域一致。

### 1.6 物理/相机/输入精确度

- [ ] 将当前扫掠 AABB/简化运动学替换或对照原版 PhysX/Havok 行为；楼梯、斜坡、贴墙、飞行碰撞逐项验证。
- [ ] CameraBoom 的 Far/Zoom/Spring/Collision 状态完整恢复；当前只校准了基本 4 m/10° 状态。
- [ ] 原版输入映射/死区/鼠标灵敏度/手柄；E 上升与 Shift+E 的原始冲突在 B 阶段前保持原版优先。
- [ ] 保存/检查点/暂停/标题流程与原始一致。

## 2. P0：Gate 4 原版动画/状态机

### 2.1 导入缺失的原版 locomotion PSA

已确认原版 AnimBP/BlendSpace 引用：

```text
Hero_Walk
Hero_SprintRun
Hero_SprintSuper
Hero_StartSprint
Hero_Stopping_Sprint
Hero_Stopping_WalkRun
Hero_JumpSpeed
Hero_JumpLand
ALS_N_Jump
HeroABS_MoveGround
HeroABS_FlyingMoveAnim
HeroABS_FlyingUpDonwAnim
HeroABS_JumpFallLoop
```

- [x] 从 pak 提取并导入 `Hero_Walk`、`Hero_SprintRun`、`Hero_SprintSuper`、`Hero_JumpSpeed`、`Hero_JumpLand`、`Hero_JumpFall`、`Hero_JumpFallFast`、`Hero_StartSprint`、`Hero_Stopping_Sprint`、`Hero_Stopping_WalkRun`、`Hero_FlyForward`、`Hero_FlyForwardLow`、`Hero_FlyFastForward1`、`Hero_FlyDown`、`Hero_FlyFastDown`、`Hero_FlyUp` 十五段 PSA + config。
- [x] 用 UModel `-export -game=ue4.27 -path=... -out=...` 导出 PSA + config（**没有 `-psa` 参数**；动画对象默认导出 PSA）。以 `-HeroGame/...` 开头的包名需复制到不以 `-` 开头的目录并在该目录内用本地 package 名导出。
- [x] 写 `scripts/append-locomotion-animations.py`，把十六段追加到原 93 骨骼 hero.gltf；原 18 段保留，共 34 段；报告：`research/world-recovery/locomotion-import.json`。
- [x] 更新 `src/game/Character.ts`：低速使用 `Hero_Walk`，run 使用 `Hero_SprintRun`，JumpStart 后使用 `Hero_JumpFallFast`（对应 `HeroABS_JumpFallLoop` 的 Speed≈1250/SpeedZ≈-5000 低空样本）；`Hero_SprintSuper` 已导入但实测姿态不是正常跑步，暂不用于默认 run；已用真实 W/Space/Alt+W 输入截图验证无畸形。
- [ ] 仍未导入：`ALS_N_Jump`、`HeroABS_MoveGround` 的完整方向 blendspace 样本、`Hero_FlyLeft`/`Hero_FlyRight`/`Hero_FlyBack`/`Hero_FlyTame`；fly 已按 velY/平面速度直接切 `FlyUp/FlyDown/FlyFastDown/FlyForward/FlyForwardLow`，仍不是 BlendSpace 采样。
- [x] jump 的起跳/下落/落地顺序已接入：`Hero_JumpSpeed → Hero_JumpFallFast → Hero_JumpLand`。
- [ ] jump 状态仍未按 `HeroABS_JumpFallLoop` 的 Speed/SpeedZ 轴选择与混合；当前是固定片段，不是 BlendSpace 采样。
- [x] 已接入基础直接状态链：`StartSprint→SprintRun`、`SprintRun→Stopping_WalkRun→Idle`、`JumpSpeed→JumpFall→JumpLand`（用 `AnimationGroup.getLength()` 计时）。
- [ ] 用 AnimBP 的真实 transition/blend 时间替换直接计时，并验证起跳/落地和冲刺起停边界。


### 2.2 恢复 HeroAnimBP 状态机

- [x] 解码 `HeroAnimBP` 的资产/引用；基础 idle/run/jump/fall/land 直接状态链已实现。
- [ ] 恢复 `HeroABS_MoveGround` 的实际 BlendSpace 轴、过渡条件、混合时间和飞行混合空间，替换当前直接片段计时。
- [ ] 实现 montage 攻击的 section/通知/连招/取消窗口；现有攻击时间轴仅是部分恢复。
- [ ] 恢复 AnimNotify：命中、移动、脚步声、飞行尘土、攻击碰撞、结束；当前只覆盖部分。
- [ ] Root motion / 惯性 / 转向 / 空中控制与原始一致。
- [x] 数据级校验：`npm run verify:locomotion` 检查 34 段动画的四元数范数、NaN、关节覆盖；报告 `research/world-recovery/locomotion-frame-validation.json`（<5e-8，无 NaN；部分 PSA config 删除配饰轨道故为 68 关节）。
- [ ] 验证方法：在真实 gameplay 同一帧读原程序骨骼/动画状态，与 Web 同帧骨骼比较；不能只看截图。
- [ ] 验收标准：逐帧（至少逐关键帧）骨骼旋转/位移在容差内，无穿插/畸形，状态转移与原始一致。

### 2.3 Homelander 替换（B 阶段，冻结）

- [ ] 仅在 A 的门禁全部通过后开始。
- [ ] 优先保留原 93 骨骼/18+ 动作；Homelander 只替换外观 mesh/texture。
- [ ] 处理 68→93 骨骼映射、绑定姿势/T-pose/A-pose、蒙皮权重、材质、头发/披风。
- [ ] 逐帧验证：同一动作下原角色与 Homelander 骨骼关键点、脚底接触、手部/武器 socket、面部无畸形。
- [ ] 不得用 Homelander 自带动作替代原版动作；用户明确要求原动作逐帧保持。

## 3. P1：完整 gameplay 还原

- [ ] AI：行人、车辆、敌人、Boss、警察/军队、生成/巡逻/战斗状态机。
- [ ] 车辆：`BP_TrafficSystem` 信号、路径、让行、碰撞、载具伤害。
- [ ] 任务：FireQuest/MatQuest/Boss/Challenge 状态机、完成/奖励/失败条件。
- [ ] 战斗：伤害公式、命中判定、连招、远程拳波、投掷、热视线、Boss 阶段。
- [ ] 城市事件/破坏/警戒/平民反应/新闻/评级。
- [ ] 音频：BGM、SFX、语音、环境声、动态混音。
- [ ] 特效：Niagara 粒子、尘土、冲击波、热视线、破坏碎片。
- [ ] 菜单/标题/开场影片/暂停/设置/存档/读档/键位。
- [ ] 完整关卡/支线/收集/挑战/成就。
- [ ] 全流程回归测试与性能预算。

## 4. P2：Web 端质量/工程

- [ ] 分辨率/DPI/窗口与原始一致；HUD 安全区。
- [ ] 浏览器性能：当前开始场景 ~20–25 FPS；目标稳定 60 或明确预算。
- [ ] 资源加载/流送/内存/缓存；避免一次性 8,824 objects。
- [ ] 网络/离线/local-only；不引入外部服务。
- [ ] 可重复的资产生成脚本与 clean-checkout 说明。
- [ ] 自动化：typecheck/build/B1/B2/B3/capture-world 同机位回归。
- [ ] 错误处理、资源缺失降级、日志/诊断。
- [ ] 浏览器兼容性/触控/手柄。
- [ ] 文档：资产 provenance、恢复状态、用户可复现实验步骤。

## 5. 冻结的 B 扩展（A 通过后再做）

- [ ] Hold-E 热视线；保留原右键远程攻击。
- [ ] 解决 E 原版上升冲突（不能破坏原版飞行）。
- [ ] 自由破坏：人/车/指定 prop；无玩家伤害、无负分、无退化、无强制失败、无资源限制。
- [ ] Homelander 外观替换与动作逐帧验证（见 2.3）。
- [ ] B 阶段所有新增行为必须有明确“扩展”标签，不能混入 A 的还原证据。

## 6. 下次继续的最短路径

1. `git pull`，确认 `17a2342`/后续提交；读 `AGENTS.md` 的 Durable handoff。
2. 打开 `tools/runtime/ue4ss/README.md`，按步骤重建 staging；原安装只读。
3. 原程序进入 gameplay：`GameStartEvent()` + **一次** `InputDone()`；不要重复调用。
4. 用 `?exact=1&cam=...` 复现同机位；确认 `comparison-live-gameplay-start-final.jpg`。
5. 先做 2.1：提取并导入 `Hero_Walk`/`Hero_SprintRun`/`Hero_Jump*`；每加一段做骨骼/脚底/循环验证。
6. 再做 1.1/1.2：MainLevel lightmap/雨棚；不要用新的全局调色替代原版数据。
7. 最后才进入 B。

## 7. 关键命令与路径

```powershell
# Node 24（系统 Node 18 会失败）
$env:PATH = 'C:\Users\Shark\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin;' + $env:PATH
npm run typecheck
npm run build
npm run capture:play
```

```text
原安装（只读）：E:\SteamLibrary\steamapps\common\UNDEFEATED
项目：E:\undefeated-web
UE4SS staging（临时）：C:\Users\Shark\AppData\Local\Temp\undefeated-ue4ss
UE4SS 说明：tools/runtime/ue4ss/README.md
同机位证据：research/runtime-observation/comparison-live-gameplay-start-final.jpg
原版实抓：research/runtime-observation/original-gameplay-start-final.png
动画状态机：docs/animation-state-recovery.md
同机位/亮度：docs/runtime-comparison.md
```

## 8. 验收门禁（未过不得称完成）

- Gate 1 真实 gameplay transform：**已过**
- Gate 2 同机位（位置/旋转/FOV）：**已过**
- Gate 3 光照/材质/天空/场景/HUD：**未过**
- Gate 4 原版动作/状态逐帧：**未过**
- B 扩展：**冻结**

本表是当前完整剩余工作清单；完成一项后更新本文件并在提交信息中引用对应条目。
