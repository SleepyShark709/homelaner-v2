# 原世界初始场景与关卡流送合同

本合同来自已解码原包的 UAssetAPI 属性、Blueprint 字节码以及 Kismet VM 偏移重建。不是原生 REA 结果，也不是运行原游戏得到的可见性轨迹。未修改游戏安装或 Web 源码。

## 可以直接消费的基线

`public/assets/world/streaming-manifest.json` 的 `baseline.packages` 是准确的包路径集合；`baseline.levelNames` 是对应短名。建议原城预览先只装配这些关卡包，再通过独立事件加入条件内容。不要使用地图名字的包含关系分类。

基线共 **17 包**：

- 持久世界：MainLevel。
- MainLevel 原 World 表内的 AlwaysLoaded：LightingTest、CitizenWayPoint、CustomEventLevel、TitleMenuLevel。
- 主 GameMode 的 BeginPlay 加载链：DownTown → Park → FinancialDistrict → CommercialArea → IndustrialArea → Beach → Slam → ResidentialArea1 → ResidentialArea2 → ResidentialArea3 → Coast → DynamicProps。

12 次请求均 `MakeVisibleAfterLoad=true`、`ShouldBlockOnLoad=false`。每次的完成回调进入下一请求，顺序由 latent continuation 的 VM 偏移证明，而非按 JSON 排列猜测。生成器会逐个断言链条和 6 个类的函数字节数；194 个函数全部与原 `ScriptBytecodeSize` 相等。

入口配置为 `/Game/-HeroGame/Maps/MainLevel.MainLevel`；MainLevel `/Exports/11844/Data` 的 DefaultGameMode 导入准确解析为 HeroGameMode_C。ReceiveBeginPlay `/Exports/49/ScriptBytecode/0` 进入 21526，主图名比较和 IsMainLevel 赋值见主函数语句 825–827；启动城区入口为 24124，即语句 913。

这里的“基线”指主场景启动加载完成、尚未加入可选教程/剧情/挑战/Boss 的包集合。它不意味着这些包的每个 Actor 同时渲染；尤其 TitleMenuLevel 常驻与其内部 Actor 是否由 TitleOptions 隐藏是两件事。DynamicProps 后续会卸载再加载重置，也不能称永不卸载。

## 启动中的条件内容

LoadLevel 是过渡包。原调用完成后延迟 1 秒再卸载，证据为 HeroGameMode 主函数语句 830 → latent 1609（语句 58）→ latent 1545（语句 56）。这是独立分支，不能表述为“全城区加载完成后再等待 1 秒”。

EnelightMeteor 不在无条件基线：DynamicProps 完成后，只有 `HeroGameInstance.SaveData.IsFirstPlayerSpecialAction=true` 才请求加载；语句 25–27、53 保留精确分支。没有读取或假定用户存档当前值。

GameStartEvent 中 `NOT SaveData.IsFirstTutorial` 进入 ForceStartTutorial 路径；后者延迟后调用 HeroGameInstance.LoadTutorial。TutorialLevel 由 HeroGameInstance 的显式加载/卸载函数管理。此处按原布尔条件记录，不用变量名字推断“第一次”语义。

## 挑战、剧情与 Boss

挑战通过 `StartOrEndCQ` 的类型和难度匹配后调用 StartCQEvent。MainLevel 路径在重置中会卸载对应关卡两次，然后通过完成回调重新加载；生成器保留实际链而非优化掉重复请求。非 MainLevel 分支才选择 DPropTest/FPropTest，不能把这两个测试道具关卡加入原城基线。

QuestType=0/1 分别索引原默认 QuestLevelNameD/F 数组。难度的 **实际枚举整数** 为 0 Easy、1 Normal、2 Hard、3 VeryHard、4 Ultimate、5 Tutorial。`NewEnumerator4` 的整数其实是 5；不能拿序列化名字的数字后缀当值。VeryHard/Ultimate 的四个 CQ 包名存在于默认数组，却不在原 Pak 的 41 个 /Game 地图中；manifest 明确 `shippedPackageExists=false`。

BP_StoryManager.StartStory 的原 MapProperty 将 StoryType 0–3 映射到 TutorialLevel、Story1Level、Story2Level、Story3Level，见 `/Exports/26/Data/1`。StartStory 会设置 CurrentStoryType、显示加载画面、EndContent、SetInputState(0) 后请求加载；ForceEndStory/ClearStory 请求卸载。

BP_CityManager.LoadBossLevel 明确要求 GameInputState=4 且现有 BP_BaseBoss 首项无效，才根据 BossType 和 IsMainLevel 选择包。MainLevel 下 0/1/2 为 WindBossLevel/FireBossLevel/LightningBossLevel；非主图选择对应 TestBossLevel。类型 3 的原字符串是 `BotBottLevel`，并不存在于地图清单，不替换成猜测值。类型 4 选择 None。卸载入口也有现存 Boss 有效性检查。自动 Boss 调度的上游进度/时间条件仍未完全解释，不能在初始场景同时加载三 Boss。

## 原入口体积与位置

manifest `triggerInstances` 含 MainLevel 中 **8 个挑战入口和 3 个剧情入口**，位置和缩放取自原组件/父组件变换；统一转为 `[UE.x, UE.z, UE.y]/100`。每个实例保留原 Actor 属性、组件属性、源 JSON 指针、枚举值和选定地图。

挑战 MainSphere 原半径 256 UE 单位，即 2.56 米；TutorialSphere 为 2000，即 20 米；剧情 Sphere 为 200，即 2 米。这 11 个入口的对应实例未覆盖模板半径且缩放为 1。

普通挑战入口需 Player tag、没有已存在 Boss、Deactive=false；若处于 Tutorial，则要求难度=5。它设置交互类型、显示提示并广播 CQSetting，不直接加载挑战关卡。离开会清空交互提示。教程大球的进入分支只在 InTutorial 等条件满足时关闭 P_QuestArea1 效果并设置 OverlapEffect，不是城区距离加载器。

剧情入口要求 Player tag 和 GameInputState=4，按原 `IsSotryClear` 设置交互类型：未清除为 1，已清除为 2；交互时 PlayerBP 的类型 1 调用 StoryManager.StartStory，类型 2 根据 StoryType 发起 BossSpawn。是否启用入口还受剧情进度影响，尚未转成完整可执行状态机。

## 覆盖、未知与验收

扫描了全部 291 个已解码项目类包，得到 **25 次 LoadStreamLevel + 21 次 UnloadStreamLevel**，集中在 5 个管理类；原来的“23 调用点”只是三个管理器的子集。另扫描 41 个 /Game 地图的 FunctionExport，未发现额外目标调用；未找到序列化原生 LevelStreamingVolume 实例。这支持采用启动事件链恢复城区，不能外推为所有原生自定义流送均不存在。

子地图中保存的 13 条嵌套 World 引用独立列在 `nestedWorldReferences`。它们包含 Lighting 等包，但未证实这些子世界的 streaming 表会传播到正在运行的 MainLevel，因此没有递归加入基线。

尚未证明：原运行时的加载成功/失败和实际可见性、完整 Actor 初始隐藏状态、所有剧情进度门控、自动 Boss 调度阈值、教程离开入口的完整后效、首次出生/菜单摄像机的最终运行姿态。manifest 不声称这些已移植。

本轮验收可逐项检查：

1. 原城装配仅取 17 包基线；默认不混入全部 CQ、剧情、Boss、过渡包。
2. 12 个启动请求的每条 latent 目标匹配下一请求，保存的布尔参数不改变。
3. 条件陨石和教程需显式存档状态；状态未知时不擅自触发。
4. 入口坐标和半径直接取 manifest；接近提示与确认加载分开处理。
5. 不存在的包名保持失败/未知，不生成替代关卡。

重建命令：`python tools/asset-pipeline/restore-world-streaming.py`。校验记录在 `research/streaming-validation.json`，原始调用扫描在 `research/streaming-call-inventory.json` 与 `research/streaming-map-scan.json`。所有 offset/view 文件均位于 `research/streaming-*`。
