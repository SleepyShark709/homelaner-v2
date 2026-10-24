# UNDEFEATED Web

> 2026-10-24纠偏：用户要求全面REA逆向及原版还原。当前Web仅为部分原资产的重建演示，不符合完整移植验收；已暂停新玩法扩展，正在补原程序、完整关卡、材质和逻辑证据。见[纠偏与逆向覆盖报告](research/rea-audit/README.md)。

独立项目位置：`E:/undefeated-web`。

目标是先重建 UNDEFEATED 的浏览器版本，优先复用原角色骨架、动画和场景；再加按住 E 的热视线、自由破坏及无惩罚模式；最后将主角外观替换成祖国人。

默认入口现为**原版世界恢复查看器**：按原启动加载链选择 17 份城市关卡，按原关卡坐标、模板继承、实例矩阵、道路样条与高度场装配城市，加载原材质与纹理，并接入原天空 HDR 采样。可切换城区及全部主世界静态总览，使用漫游相机检查。46 处参考姿态附件和已发现的骨骼材质槽歧义已修复，并接入 25 份原 shader 计算合同与已恢复的启动加载链执行检查。它尚不是可完整游玩的原版移植；原构造脚本、角色控制、AI、事件和流程仍待恢复验证。

旧玩法原型保存在 `/?view=prototype`，角色/动画实验室在 `/?view=assets`。原版可玩基线 B1/B2/B3 切片在 `/?view=play`：原角色 + 原 ResidentialArea1 街区 + 原高度场 + 原输入语义 + 预览人口与原战斗动画 + 车辆/道具动态碰撞；说明与缺口见 [docs/playable-baseline.md](docs/playable-baseline.md)。新增热视线、自由破坏与换模开发暂停，先完成原版基线。当前证据及验收见 [世界恢复记录](docs/world-recovery.md)，历史原型记录见 [docs/progress.md](docs/progress.md)。

## 运行

需要 Node.js >=24。在本项目目录执行：

```powershell
npm install
npm run dev
```

本机可以直接使用已有的 Codex Node 运行时启动：

```powershell
powershell -ExecutionPolicy Bypass -File E:\undefeated-web\scripts\dev.ps1
```

脚本只为该进程设置运行时路径，不修改全局环境变量。浏览器访问 `http://127.0.0.1:5178`。

```powershell
npm run typecheck
npm run verify:world
npm run test:world
npm run test:streaming
npm run test:sky
npm run test:play
npm run verify:assets
npm run verify:game
npm test
npm run build
npm run capture:world
npm run capture:play
npm run capture:play:b2
```

当前世界资源位于 `public/assets/world`，旧原版派生资产位于 `public/assets/original`，工具与中间导出位于 `tools/asset-pipeline` 和 `research/exports`。二进制游戏资源不跟踪进 Git。本地缺少资产时，查看器会明确提示，不能只复制源码就得到完整资源。

动画中间模型位于 `public/assets/animated`，完整角色在 `public/assets/character`，原街区在 `public/assets/city`，均排除在 Git 外。角色资源重建入口为 `scripts/prepare-assets.ps1`（需要 Python 3、原游戏、便携 repak、UModel、UAssetGUI）；已有导出时可加 `-ReuseExports`。城市使用 `python tools/asset-pipeline/export-city.py` 重建。

当前世界查看器：WASD 漫游，拖动鼠标转向，E/Space 上升，Q 下降，Shift 加速；区域选择、全景/靠近、高清地形与线框用于检查恢复结果。

旧原型操作（仅 `?view=prototype`）：WASD 移动，拖动鼠标转向（也可点击“锁定鼠标”）；Space 跳跃，空中再按 Space 进入飞行；F 切换飞行；飞行中 Space 上升、Ctrl 下降，Shift 加速，R 回到起点，Esc 暂停。左键/J近战，右键/K拳波，Shift+右键/K强力拳波，按住E热视线（不再上升）；Q也可下降。默认自由破坏，可切换基础交互，并用“重置街区”恢复所有目标。画质按钮可切换流畅/高清。

## 工程资料

- `docs/architecture.md`：引擎选择、原资产转换和角色蒙皮路线。
- `docs/roadmap.md`：用户要求的阶段顺序与验收边界。
- `docs/implementation-plan.md`：完整执行方案、实现顺序与技术解释。
- `docs/progress.md`：旧原型实际成果与限制。
- `docs/world-recovery.md`：当前世界恢复范围、证据、浏览器验证与缺口。
- `docs/playable-baseline.md`：B1/B2 可玩切片、原输入语义、预览人口、战斗动画、碰撞代理与已知近似。
- `docs/city-reconstruction.md`：原地图坐标、道路样条和资源来源。
- `docs/character-assembly.md`：原头发/墨镜挂点与装配。
- `docs/combat-spec.md`：已恢复原战斗行为与动画命中时序。
- `research/evidence`：原游戏文件身份、蓝图调查与转换证据。
- `tools/asset-pipeline`：便携工具和可复用转换脚本。

当前采用 Babylon.js + TypeScript + Vite。UE 蓝图不能直接在浏览器执行。移动使用固定步长的运动学扫掠碰撞；Havok尚未接入，后续车辆、残骸物理需另行验证。
