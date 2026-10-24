# 技术路线与资产复用

本项目是 E:/undefeated-web 下的独立工程。用户要求优先保留 UNDEFEATED 原骨架、原动画、原场景与原玩法，最后只替换主角外观。

## 选择

采用 Babylon.js 9.32.0 + TypeScript + Vite；先使用 WebGL 浏览器兼容路径，后续需要时再验证 WebGPU。选择原因是本项目需要统一的场景、骨骼动画组、资产加载、粒子、相机及调试能力。原有 homelander-simulator 的技术栈和源代码不作为本工程基础。

物理引擎候选为 Babylon 原生接入的 Havok。在原版资源尺度和碰撞需求完成验证前，资产查看器不引入物理依赖；后续用固定物理时间步分别处理玩家控制、车辆和残骸。此时 Havok 尚未集成，不应写成已实现。

Babylon 能导入 glTF 的网格、骨架和动画，但不能执行 Unreal 蓝图。原版 PhysX 的参数也不能未经测试直接映射成相同效果。

## 可复用和需转换的内容

| 原内容 | Web 处理 |
| --- | --- |
| SkeletalMesh、骨架、蒙皮 | 导出后保留骨骼对应关系，转换为 glTF/GLB |
| Animation Sequence | 保留原动作采样与原骨架绑定；验证坐标、帧率和根运动 |
| Montage、AnimNotify、AnimBlueprint | 在 TypeScript 中重建状态、混合、事件窗口和命中时机 |
| 城市模型、贴图、音频 | 转换格式，检查 UV/材质，并分区加载 |
| 地图中的 Actor 布局 | 恢复位置、旋转、缩放和依赖，另存场景清单 |
| UE 材质和粒子图 | 依据效果重新制作 Web 材质/粒子；不能把提取贴图当作材质已完整还原 |
| 蓝图 gameplay | 使用逆向规格重写，保留证据与行为对照 |
| 平台相关 UI | 只移植游戏需要的流程，不引入 Steam/主机平台集成 |

## 最后替换祖国人的外观

默认路线是沿用原角色骨架和动作，把祖国人的网格对齐原绑定姿势，转移或重新计算蒙皮权重，再修正关节和披风。这样原动画可以继续驱动同一套骨架。

因此，这个新目标下可能确实要重新蒙皮，但不等于重新造一套骨架或重做所有动画。祖国人现有动画不作为必须保留的输入。只有当外形比例与原骨架不适合时，才考虑保留祖国人骨架并做动画重定向。

游戏逻辑依赖语义挂点（双眼、手部、脚底、相机），不直接依赖外皮文件名。外观替换不能改变命中胶囊或玩家速度。

## 模块边界

- assets：来源清单、加载、转换结果及模型验证。
- game/player：原版地面/空中移动、控制与动作状态。
- game/animation：原版动作映射、动画事件和混合。
- game/combat：射线、近战、远攻、统一命中接口。
- game/world：城市分区、市民、交通与对象回收。
- game/rules：原版模式与自由破坏模式的规则。
- UI：菜单、HUD、按键提示及加载状态。

当前已实现 assets 验证场景、World 原街区加载、Character 原角色及18动作、Input、PlayerMotor、collision 数值模块，以及 Combat 时间轴/近战/拳波/热视线、combat-rules 模式策略、Population 短路线人车及受击、Effects 程序特效。街区为右手Y-up米制；移动以1/120秒固定步长执行，使用角色盒体对建筑/地台AABB的连续扫掠和滑动。这是简化运动学碰撞，不是原PhysX，也未接入Havok。完整原AI、敌人/Boss、任务与城市事件尚未实现。基础交互开关只恢复部分目标规则，并非完整原版模式。

## 来源

- [Babylon 文件加载](https://doc.babylonjs.com/features/featuresDeepDive/importers/loadingFileTypes/)
- [Babylon 功能](https://www.babylonjs.com/specifications/)
- [UE Viewer](https://www.gildor.org/projects/umodel)
- 本地 research/evidence 内的原程序身份和蓝图调查结果。
