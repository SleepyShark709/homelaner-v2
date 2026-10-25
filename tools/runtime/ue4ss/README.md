# UE4SS 运行时坐标探针（只读）

用于还原阶段读取原程序 gameplay 的 Pawn/相机 transform。不要修改原安装。

## 1. 准备 staging 副本

以 `E:\SteamLibrary\steamapps\common\UNDEFEATED` 为例：

```powershell
$stage = "$env:TEMP\undefeated-ue4ss"
New-Item -ItemType Directory -Path "$stage\UNDEFEATED\Binaries\Win64" -Force
Copy-Item '...\UNDEFEATED\UNDEFEATED\Binaries\Win64\UNDEFEATED-Win64-Shipping.exe' "$stage\UNDEFEATED\Binaries\Win64"
Copy-Item '...\UNDEFEATED\UNDEFEATED\Binaries\Win64\OpenImageDenoise.dll' "$stage\UNDEFEATED\Binaries\Win64"
Copy-Item '...\UNDEFEATED\UNDEFEATED\Binaries\Win64\tbb12.dll' "$stage\UNDEFEATED\Binaries\Win64"
New-Item -ItemType Junction -Path "$stage\UNDEFEATED\Content" -Target '...\UNDEFEATED\UNDEFEATED\Content'
New-Item -ItemType Junction -Path "$stage\Engine" -Target '...\UNDEFEATED\Engine'
```

## 2. 安装 UE4SS

- 使用 [UE4SS v3.0.1](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/v3.0.1)；
- 把 `UE4SS_v3.0.1.zip` 解压内容复制到 `staging\UNDEFEATED\Binaries\Win64`；
- 复制本目录的 `CoordDump` 到 `Binaries\Win64\Mods\CoordDump`；
- 在 `Mods\mods.txt` 加入 `CoordDump : 1`；
- 用 staging 的 `UNDEFEATED-Win64-Shipping.exe` 启动。

## 3. 读取

UE4SS 日志：

```text
staging\UNDEFEATED\Binaries\Win64\UE4SS.log
```

每秒会打印：

```text
COORD loc=(x,y,z) rot=(pitch,yaw,roll) cam=(x,y,z) crot=(pitch,yaw,roll)
```

单位：UE cm；`loc` 是 Pawn，`cam` 是 PlayerCameraManager。

## 进入 gameplay 的真实路径

仅调用 `ClientTravel("MainLevel", 0, false)` / `ConsoleCommand("open MainLevel")` 会被游戏拒绝。已确认可用的路径是标题 Blueprint 自身的事件：

```lua
local title = FindFirstOf("WBP_TitleSinboard_C")
title:GameStartEvent()
-- 等 intro 开始后只调用一次，避免重复推进过场：
title:InputDone()
```

intro 结束后 `CoordDump` 停在：

```text
pawn = (-311.999, 7473.891, 167.150) cm
cam  = (-361.999, 7073.891, 327.150) cm
rot  = (-10, 90, 0)
fov  = 90.000
```

这是当前用于同机位对照的真实 gameplay 起点。`PlayerCameraManager:GetFOVAngle()` 实测为 90.000；Web 同机位也必须用 FOV 90。

## 光照/后处理探针

`LightDump` 会枚举 `DirectionalLight` / `SkyLight` / `PostProcessVolume`，用于记录原版光照与 postprocess 参数。当前从 `LightingTest` 子关卡读到：

```text
PostProcessVolume AutoExposureMinBrightness=1.0
                   AutoExposureMaxBrightness=8.0
                   AutoExposureBias=0.0
                   BloomIntensity=2.5
```

注意：这些是 `LightingTest` 子关卡参数，不代表 MainLevel 的烘焙光照；光照仍是 Gate 3 未完成项，不能把 Bloom 2.5 直接硬塞进 Web 当作等价。

## 已知限制

- 菜单/标题场景也会被打印；必须确认已经进入 gameplay；
- `InputDone()` 只能调用一次；重复调用会不断推进/循环过场；
- 当前尝试的 `ClientTravel("MainLevel", 0, false)` / `ConsoleCommand("open MainLevel")` 被游戏拒绝，不能用来跳过菜单；
- 不能拿菜单 Pawn 当起点；以 intro 结束后的稳定值为准。

## 原版窗口截图限制（2026-10-25）

尝试在 UE4SS staging 下用 `-windowed` 启动原游戏，并通过 `SetWindowPos(HWND_TOPMOST)`、`SetForegroundWindow`、`AttachThreadInput` 和 Alt+Tab 把窗口置前，再发送 Shift+W 并用 `CopyFromScreen` 抓取。`GetWindowRect` 返回 1280x720，但所有截图仍是浏览器桌面，不是游戏画面；进程窗口无法被真正置前/显示。

因此这几次截图（已删除）**不能作为原版冲刺证据**。若以后要抓原版移动帧，优先使用：

- 游戏自身的截图/控制台方式；或
- 独立桌面/虚拟显示会话；或
- 直接把窗口渲染到可读交换链的工具。

不要再把 `CopyFromScreen` 的结果当成游戏证据，除非先确认截图内容是 UNDEFEATED 画面。
