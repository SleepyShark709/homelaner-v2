# 原版动画转换记录

已将四个真实 UModel PSA 动画合并到原角色的材质版 glTF：`public/assets/animated/hero.gltf`。原模型的 93 个关节、蒙皮、逆绑定矩阵、网格和纹理均来自 `public/assets/original/hero/hero.gltf`，没有换骨架或生成替代动作。

重新生成：

```powershell
python scripts/convert-original-animations.py
```

脚本只使用 Python 标准库。输出目录包含模型、原模型二进制、纹理、`animations.bin` 与 `validation.json`。后者记录每个输入 glTF、二进制、纹理、PSA 和 config 的 SHA-256，以及合并产物哈希。`--mesh` 和 `--output` 可覆盖路径；源资产不修改。

## 转换依据

核对的是 Gildor 官方 UEViewer 源码 commit `a0bfb468d42be831b126632fd8a0ae6b3614f981`，不把其他 ActorX 导出器假定为同一种约定。

- [ExportPsk.cpp](https://github.com/gildor2/UEViewer/blob/a0bfb468d42be831b126632fd8a0ae6b3614f981/Exporters/ExportPsk.cpp) 的 `MIRROR_MESH=1` 与 `DoExportPsa`：动画位置 Y 取反；四元数 Y、W 取反；采样顺序是动画→帧→骨骼。先逆转这一步。
- [ExportGLTF.cpp](https://github.com/gildor2/UEViewer/blob/a0bfb468d42be831b126632fd8a0ae6b3614f981/Exporters/ExportGLTF.cpp) 的 `TransformPosition`、`TransformRotation`、`ExportAnimations`：交换 Y/Z，位置乘 0.01，由厘米变为米；根骨四元数额外取共轭。四元数没有额外 W 翻转，源码中该行是注释。
- [Psk.h](https://github.com/gildor2/UEViewer/blob/a0bfb468d42be831b126632fd8a0ae6b3614f981/Exporters/Psk.h) 定义所解析的 120-byte 骨骼记录、168-byte 动画信息和 32-byte 动画关键帧。

因此，以 PSA 的 `p=(x,y,z)`、`q=(x,y,z,w)` 表示，输出位置是 `(x,z,-y)/100`，普通骨骼旋转是 `(x,z,-y,-w)`；根骨在此基础上再对 xyz 取反。归一化后，对相邻等价四元数选取同半球符号以避免长弧插值。按骨名忽略大小写匹配，与 UModel 自身 glTF 导出器一致。

每个 PSA 有 109 个骨名，模型有 93 个关节；模型的 93 个均成功映射。没有把剩余 16 个不存在的关节添加到模型，也没有使用 PSA 的虚拟父索引重建骨架。

`.config` 是必要输入：四份配置均有 `bAnimRotationOnly=1`。只有 `UseTranslationBoneNames` 指定的关节播放位置轨道，其他关节保留原模型的绑定位置。`RemoveTracks` 中的 `all/trans/rot` 轨道保留绑定值，不把缺失数据中的零位移/单位旋转写入动画。忽略这些配置会导致肢体拉伸或缺失骨骼复位。

## 结果与数字验证

| 动画名 | 帧数 | PSA 实际采样率 | 最后关键帧秒数 | 有效通道数 |
|---|---:|---:|---:|---:|
| Hero_Idle | 151 | 60.3999938965 | 2.4834439596 | 127 |
| Hero_IdleFlying | 151 | 60.3999938965 | 2.4834439596 | 127 |
| Hero_FlyFastSprint | 22 | 15.7142858505 | 1.3363636248 | 77 |
| A_ThirdPersonRun | 18 | 29.9999980927 | 0.5666667027 | 77 |

时间采用 `frameIndex / AnimRate`，没有假定 30 或 60 fps。最后关键帧是 `(N-1)/rate`；PSA 的名义周期 `N/rate` 分别约为 2.5、2.5、1.4、0.6 秒。当前遵循 UModel glTF 导出器的最后关键帧规则，没有人为补循环末帧，所以播放器循环周期与 PSA 名义周期相差一帧。循环衔接需视觉确认。

已完成：

- 所有块边界、结构大小、PSA 元数据、关键帧数量与源值有限性检查；非空 SCALEKEYS 会明确拒绝，避免静默丢失缩放动画。
- 原骨架世界矩阵乘逆绑定矩阵，最大单位矩阵误差 **0.00000418613**；原骨架与原蒙皮对应。
- 全部帧、全部有效关节的位置/旋转及世界坐标为有限值；最大动画局部位移长度 **1.368 米**；世界关节范围没有出现厘米被误当米的爆炸。
- 四段根骨位移均为零，因此浏览器中的行走/飞行整体位移由角色控制器负责，不应把动画误当根运动。
- 重新读取实际写出的二进制，检查每个 buffer/view 边界、输入输出关键帧数量、时间严格递增、动画目标唯一和所有输出值有限；四元数平方模的最大误差为 **8.79e-8**。

具体每段的全帧关节包围盒、未映射名称、忽略轨道和来源哈希见 `public/assets/animated/validation.json`。包围盒包含 IK 和末端辅助骨，不能直接作为网格可见包围盒或脚底高度。

## 浏览器验收方式与边界

运行时将导入路径切到 `/assets/animated/hero.gltf`，加载器应返回以上四个 animation groups。先停止其他组，分别播放一组，不同时混播来判断转换质量。建议在固定镜头、无角色位移条件下，记录各动画的第 0、25%、50%、75% 帧截图；对照原游戏姿态，检查左右手、膝盖、肩、脖子、脚底与飞行朝向，再验证循环和切换。披发/发型等独立附件需要按头部挂点随骨骼驱动。

这次数字检查证明真实数据已转换、目标骨架吻合且尺度合理，**不代替视觉动作验收**。本脚本未复刻 AnimBlueprint 的混合、IK、动画通知、物理次级运动或根运动消费，也未恢复 PSA 格式未承载的动画曲线。未映射/被移除轨道按配置保留绑定姿态；它们不是新增动画。当前配置的 retargeting 语义可处理，其他重定向模式会在进一步资产范围扩大时需要单独支持。
