# 原版主角外观装配

`public/assets/character/hero.gltf` 已合并原身体、`SK_Hair_001_pompadour` 头发、`SK_Sunglasses` 墨镜及四段原动画。输入为已有 `animated/hero.gltf` 和 `original/hair`、`original/sunglasses`。未修改原模型顶点、纹理或动画数据，未重绑骨骼。

复现命令：

```powershell
python scripts/assemble-original-character.py
```

脚本直接静态解码已提取的 `SKEL_Male.uasset`；不启动或修改原游戏。PlayerBP JSON 默认在本项目 `research/exports/decoded` 缓存，缺少时从只读Pak提取并用本项目解码器生成，也可用 `--player-json` 指定。脚本临时骨架解码文件在结束后自动清理。来源文件、解码工具 SHA-256、原始属性与验证记录写入 `research/evidence/character-assembly.json`。

## 挂点证据与装配

PlayerBP 的 `SCS_Node_5`（export 127）为 `SK_Hair`，`SCS_Node_27`（export 110）为 `SK_Sunglasses`。两者均以 `CharacterMesh0` 为父组件、`head_accessories` 为挂点。对应组件模板 export 134、135 没有额外位置、旋转或缩放覆写，采用默认零位移、单位旋转和单位缩放。

`SKEL_Male` 的 `SkeletalMeshSocket_0`（export 1）定义：

| 属性 | 原游戏值 |
|---|---|
| SocketName | head_accessories |
| BoneName | head |
| RelativeLocation | (0, 0, 0) |
| RelativeRotation | Pitch -90°，Yaw 1.5°，Roll 0° |
| RelativeScale | (1, 1, 1) |

这不是“把饰品放到头骨原点即可”：头骨自身局部轴与饰品坐标不同，必须恢复挂点旋转。glTF socket 四元数为 `(0.00925574179, -0.00925574179, -0.70704620163, 0.70704620163)`；绑定姿势下它的世界轴近似角色整体轴，Y 坐标约 1.655162 米。

对于 UE 变换，坐标转换采用与 UModel 网格一致的 `(X,Z,Y)/100`，旋转采用相同基变换 `B R B⁻¹`；这里没有 PSA 中预先存在的镜像，因此不能套用 PSA 的 `(X,Z,-Y)`。脚本先将 UE FRotator 转四元数，再在反射基变换下得到 `(-qx,-qz,-qy,qw)`。

结构为：原 `head` → `head_accessories` → 头发/墨镜组件 → 各饰品原模型。主角原 93 关节 skin 和四段动画原样保留。头发、墨镜各自的原 2 关节 skin 保留在组件内部，总计 3 个 skin；这不会增加或改动主角的 93 个关节，也不需要把饰品的 `head_acc` 当成主角 `head` 重定向。

## 运行时坐标

模型为右手系、Y 向上、米制，**正前方 +Z**。证据包括双脚脚趾关节相对踝关节均沿 +Z 约 0.16429 米，以及原 PlayerBP 对身体组件使用 UE Yaw -90°，将模型原来的 +Y 朝向旋转到角色 Actor 的 +X。

以下数值未加 gameplay 的 1.05 缩放：

| 测量 | 米 |
|---|---:|
| 绑定姿势身体脚底 Y | -0.0045661274 |
| 绑定姿势身体顶部 Y | 1.8257546425 |
| 绑定姿势含头发顶部 Y | 1.8510607825 |
| 绑定姿势含头发总高度 | 1.8556269099 |
| 待机动画第 0 帧脚底 Y | -0.0241806336 |

脚底为实际顶点测量，待机值由原蒙皮权重和动画姿态进行 CPU 蒙皮计算；读取了 glTF `normalized` 整数权重，未把 0–255 权重当浮点权重。它是姿势相关数据，不是统一胶囊底点。站立时可将模型局部 Y 抬约 0.025 米作为初始补偿，最终应结合动作与地面碰撞验证；若 gameplay 使用原 1.05 比例，补偿也乘 1.05。

原 PlayerBP 的身体组件另有 `RelativeScale3D=1.0499999523`、UE `RelativeLocation.Z=-99.5 cm`、`Yaw=-90°`。这些是相对原 Character 胶囊/Actor 的布局，**没有烘焙进输出模型**。Web 控制器应选择自己的 Actor 朝向与胶囊原点，只在 gameplay 层施加需要的朝向和缩放，避免再次无条件加 -0.995 米偏移。

## 验证与限制

已验证主角原骨骼局部变换、skin 关节列表、逆绑定矩阵引用、四段动画 JSON 完全不变；所有输出 buffer 长度/视图边界有效。饰品 skin 的世界关节矩阵乘逆绑定矩阵与挂载网格世界矩阵相符，避免饰品受到双重头部变换。输出共 103 个节点，三套 skin 为 93、2、2 个关节。

绑定姿势的头发范围约 Y=1.642825–1.851061 米，墨镜范围约 Y=1.679508–1.715574 米，符合真实挂点与原模型尺寸。需要浏览器进一步验证四段动作中头发和墨镜都跟随头部，特别是快速飞行时的旋转；静态数学验证不等于完成视觉验收。

此装配没有实现原游戏摘墨镜的动作及从 `head_accessories` 切换到手部挂点的逻辑。Web 材质使用已有转换结果，UE 材质图精确还原及头发透明度/高光调校不属于这次装配。
