# 原程序与 Web 可玩切片：第一轮视觉对照

日期：2026-10-25。目标：把原程序实际窗口截图和当前 `?view=play` 画面放在一起，先核对角色/相机/光照/UI 的明显差异。**仍不是像素等价验收。**

## 2026-10-25 更新：第一张真实同机位

通过 UE4SS 调用 `WBP_TitleSinboard_C:GameStartEvent()` + 一次 `InputDone()`，intro 结束后原程序真实 gameplay transform 为：

```text
pawn (x,y,z) = (-311.999, 7473.891, 167.150) cm
cam  (x,y,z) = (-361.999, 7073.891, 327.150) cm
rot          = (-10, 90, 0)
```

换算到 Web（x/100, z/100, y/100）并在 `(-3.12, 74.73891)`、相机 `(-3.62, 3.2715, 70.73891)`、实测 FOV 90 下重截，得到同一玩家/相机的对照：

![原版 gameplay 起点 vs Web 同机位](../research/runtime-observation/comparison-live-gameplay-start-web-v3.jpg)

相机位置、朝向、人物位置/比例、建筑柱/门洞和地面透视已经对上。剩余差异集中在门/窗玻璃与金属框、光照/接触阴影、材质、HUD/minimap 和角色动作。**同机位门已过，视觉等价未过。**

### 原版 HUD/minimap 底图接入

已恢复 `T_StaticMinimap_Tex`（1024×1024）、`map250` 墨迹边框和 `T_PlayerIcon` 玩家箭头，并读取 `BP_WorldCaptureCamera` 的 `WorldOrigin=(-130000,-130000)`、`BoxExtent=(130000,130000)`、`OrthoWidth=260000`。默认 HUD 现在隐藏自制面板，按该映射绘制原版底图、边框和玩家箭头；`?hud=help` 才显示原探索面板。

![原版 gameplay 起点 vs Web 原版 HUD](../research/runtime-observation/comparison-live-gameplay-start-calibrated.jpg)

同一建筑区域实测亮度：原版 mean 55.8 / std 31.3；Web 未校准 mean 86.1 / std 41.7；Web `exposure=0.55` 后 mean 58.4 / std 31.0。默认采用 exposure=0.55 的**预览亮度校准**（`?exposure=1` 关闭），它只对齐同机位整体亮度/对比，不是原版 UE 自动曝光/tone curve。

边框随状态的绿/红着色、任务图标和原版缩放材质尚未恢复，所以 HUD 仍未等价。

`?ssao=1` 可打开仅检查用 SSAO2 接触阴影预览，用于比较柱脚/门洞暗部；它是屏幕空间近似，不是原版 AO/lightmap 重建，也不是默认效果。

![原程序与 Web 对照](../research/runtime-observation/comparison-character-camera.jpg)

## 来源

- 原程序：`research/runtime-observation/original-start-plaza.png`，1282×752 窗口截图，裁掉 30 px 标题栏后缩放到 1280×720。原程序版本 2.1.0；启动/进入城市及存档校验见 [report.zh-CN.txt](../research/runtime-observation/report.zh-CN.txt)。
- Web：`research/screenshots/play-fov.jpg`，1280×720，`?view=play`，ResidentialArea1 车道，预览照明 + 预览角色阴影；位置 `(-50.0, 0.0, -548.6)`。相机按原 `PlayerBP` 的 `CameraBoom` 默认值校准：`TargetArmLength=400 cm`、`SocketOffset=(0,50,90) cm`、RelativeLocation Z=70 cm，并把 `Camera.FieldOfView` 按原 90° 水平视场换算；`SetPlayerComponentReference` 会用 CameraBoom 的 400/(0,50,90) 覆盖 HeroComponent CDO 的默认值（`research/evidence/player-logic.json`）。
- 两张图不是同一地点、不是同一相机参数；对照只用于角色外观/相机/光照/UI 的初步差异记录。

## 观察

| 项目 | 原程序 | 当前 Web |
|---|---|---|
| 角色外观 | 黑色短袖/长裤，体型、发型轮廓与当前 Web 角色一致 | 同一原 `hero.gltf`，黑色服装与比例基本一致 |
| 角色阴影 | 角色在铺装上有清晰动态阴影 | 已加入预览角色阴影（跟随预览太阳方向）；级联/软硬/接缝与原版不同 |
| 相机 | 第三人称，角色约占画面高度 1/3，距离更近、略高 | 已按原 `CameraBoom` 400 cm/SocketOffset(0,50,90)/boom Z70 cm 校准，FOV 改为原开始相机实测 90°，CameraLagSpeed/RotationLagSpeed=15；攻击时插值到 650 cm，CharacterSpeed>60 m/s 时 FarArmLength=800 cm。其它 Far/Zoom 状态、弹簧回弹和碰撞控制仍不同 |
| 光照/雾 | 原版光照、树影、环境雾与高光 | Babylon 预览半球/方向光；无原雾/后处理 |
| 世界 | 起点广场：长椅、树、铺装、成排建筑立面 | ResidentialArea1 街道：砖砌公寓、车道、预览行人和车辆 |
| 远景 | 城市立面/天空，无明显白色山体 | 白色未恢复材质的背景山体非常显眼 |
| UI | 原版小地图、准星、HUD | 自定义检查面板/状态 HUD；没有原版小地图/菜单 |

## MainLevel 起点广场候选

`?view=play&startup=1&at=20,0&yaw=0` 在 MainLevel 原点附近加载全城后，出现石栏杆、古典立面、广告牌、城市街区和原生砖石楼板，构图比单区 CommercialArea 候选更接近原程序起点广场。`?view=play&plaza=1` 是同一检查的快捷预设，默认使用 `(20,0)` 开阔广场姿态（`comparison-start-plaza-native2.jpg`）。

![MainLevel 起点广场候选](../research/runtime-observation/comparison-start-plaza-mainlevel.jpg)

`SM_Floor12000x15000` 的 thin-instance→普通 mesh 材质化修复了原生砖石楼板；`&floors=overlay` 现在只是可选回退，不再默认。

候选姿态补充：`plaza=1&at=-20,0&yaw=0` 是喷泉/右侧栏杆近景（`play-plaza--20-native-trees.jpg`）；`plaza=1&at=-30,-4&yaw=0&exact=1` 是左侧栏杆/花箱/树木构图（`comparison-start-plaza-native.jpg`）；两者都不如 `(20,0)` 开阔，仍不是同机位。

三个已恢复 `StoryStartPoint` 的 startup 检查都没有命中开始广场，见 [story-start-point-audit.zh-CN.md](../research/world-recovery/story-start-point-audit.zh-CN.md)。

## 原程序实时开始画面（2026-10-25）

已直接启动原程序并截取 `GAME START` 后的实际画面：`research/runtime-observation/original-start-live4.png`（1296×759）。与原 Web `plaza=1` 并排对照见 `comparison-start-live-vs-web.jpg`。

结论：**当前 Web 起点构图/光照/场景物仍明显不匹配，不能称为同机位或视觉还原完成。** 运行时候选相机数据尚未验证，详见 [original-live-audit.zh-CN.md](../research/runtime-observation/original-live-audit.zh-CN.md)。

原生 floor/树木材质化后，`plaza=1&at=-30,-4&yaw=0&exact=1` 成为当前最新的候选取景：大块石铺装、左侧栏杆/花箱、左中景树木、中央/右侧古典建筑。对照图 `comparison-start-plaza-native.jpg`；仍不是同机位，原程序更开阔、长椅沿左栏杆排布、右侧广告牌不同。

`arm=6&fov=80` 的检查用相机覆盖（`play-plaza-arm6b.jpg` / `comparison-start-plaza-arm6.jpg`）让角色比例更接近原图，但场景左右关系仍不同；默认相机现使用恢复的 4 m / 实测 90°。

![相机净空后的广场候选](../research/runtime-observation/comparison-start-plaza-camera-clear.jpg)

仍不是匹配：长椅/相机/建筑朝向未对齐，overlay 也不是原程序渲染。这是候选地点，不是同机位验收。

## 起点广场候选

`?view=play&district=CommercialArea&at=91,181&yaw=3.14159` 能看到石栏杆、古典拱窗、长椅和开阔广场，和原程序起点广场的元素组合接近（`play-plaza-190.jpg`）。但地面仍是草地（原程序为砖石铺装），建筑/长椅/相机位置也未匹配，因此这是**候选地点**，不是同机位验收。

![起点广场候选对照](../research/runtime-observation/comparison-start-plaza-candidate.jpg)

楼板几何存在但被草地/其它地面遮挡的排查见 [commercial-plaza-ground-investigation.zh-CN.md](../research/world-recovery/commercial-plaza-ground-investigation.zh-CN.md)。

## 结论与下一步

这轮确认了“原角色确实回到原街区、比例/服装方向基本一致”，并补了预览角色阴影，但仍暴露高优先级视觉缺口：

1. 相机已按原 `CameraBoom`/FOV 90 校准，但 Far/Zoom 状态、弹簧回弹、碰撞后的控制曲线仍需对照；
2. 背景山体材质仍为白色，原版雾/光照也没有；
3. 角色阴影只是预览，不是原版阴影级联/后处理；
4. 原版起点广场位置尚未在 Web 场景中定位，不能把 ResidentialArea1 街道当同机位。

下一步优先处理背景山体/雾和相机 lag，再继续寻找原版起点广场/同机位；这些改动不会冒充完整原版渲染等价。
