# 原程序与 Web 可玩切片：第一轮视觉对照

日期：2026-10-25。目标：把原程序实际窗口截图和当前 `?view=play` 画面放在一起，先核对角色/相机/光照/UI 的明显差异。**不是同机位、同输入或像素等价验收。**

![原程序与 Web 对照](../research/runtime-observation/comparison-character-camera.jpg)

## 来源

- 原程序：`research/runtime-observation/original-start-plaza.png`，1282×752 窗口截图，裁掉 30 px 标题栏后缩放到 1280×720。原程序版本 2.1.0；启动/进入城市及存档校验见 [report.zh-CN.txt](../research/runtime-observation/report.zh-CN.txt)。
- Web：`research/screenshots/play-camera.jpg`，1280×720，`?view=play`，ResidentialArea1 车道，预览照明 + 预览角色阴影；位置 `(-50.0, 0.0, -548.6)`。相机按原 `PlayerBP` 的 `CameraBoom` 默认值校准：`TargetArmLength=400 cm`、`SocketOffset=(0,50,90) cm`、RelativeLocation Z=70 cm（`research/evidence/player-logic.json`）。
- 两张图不是同一地点、不是同一相机参数；对照只用于角色外观/相机/光照/UI 的初步差异记录。

## 观察

| 项目 | 原程序 | 当前 Web |
|---|---|---|
| 角色外观 | 黑色短袖/长裤，体型、发型轮廓与当前 Web 角色一致 | 同一原 `hero.gltf`，黑色服装与比例基本一致 |
| 角色阴影 | 角色在铺装上有清晰动态阴影 | 已加入预览角色阴影（跟随预览太阳方向）；级联/软硬/接缝与原版不同 |
| 相机 | 第三人称，角色约占画面高度 1/3，距离更近、略高 | 已按原 `CameraBoom` 400 cm/SocketOffset(0,50,90)/boom Z70 cm 校准；取景比例接近，但相机 lag/碰撞和控制曲线仍不同 |
| 光照/雾 | 原版光照、树影、环境雾与高光 | Babylon 预览半球/方向光；无原雾/后处理 |
| 世界 | 起点广场：长椅、树、铺装、成排建筑立面 | ResidentialArea1 街道：砖砌公寓、车道、预览行人和车辆 |
| 远景 | 城市立面/天空，无明显白色山体 | 白色未恢复材质的背景山体非常显眼 |
| UI | 原版小地图、准星、HUD | 自定义检查面板/状态 HUD；没有原版小地图/菜单 |

## 结论与下一步

这轮确认了“原角色确实回到原街区、比例/服装方向基本一致”，并补了预览角色阴影，但仍暴露高优先级视觉缺口：

1. 相机已按原 `CameraBoom` 校准，但相机 lag/弹簧/碰撞后的控制曲线仍需对照；
2. 背景山体材质仍为白色，原版雾/光照也没有；
3. 角色阴影只是预览，不是原版阴影级联/后处理；
4. 原版起点广场位置尚未在 Web 场景中定位，不能把 ResidentialArea1 街道当同机位。

下一步优先处理背景山体/雾和相机 lag，再继续寻找原版起点广场/同机位；这些改动不会冒充完整原版渲染等价。
