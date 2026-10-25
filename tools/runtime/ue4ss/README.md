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

## 已知限制

- 菜单/标题场景也会被打印；必须确认已经进入 gameplay；
- 当前尝试的 `ClientTravel("MainLevel", 0, false)` / `ConsoleCommand("open MainLevel")` 被游戏拒绝，不能用来跳过菜单；
- 必须在真实 `GAME START` 流程后读取并移动验证，不能拿菜单 Pawn 当起点。
