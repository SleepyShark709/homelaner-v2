# 任务状态机恢复记录

## 已恢复

### FireQuest_BP

```text
class         FireQuest_BP_C
Active        true
Tags          CFire
SphereRadius  5000 cm = 50 m
```

UberGraph 关键调用：

```text
GetPlayerCharacter
GetAllActorsOfClass
Array_Length / Array_Get
Add_IntInt
Less_IntInt
SendHeroPoint
RescueEvent
TutorialQuestClear
PublishQuest
ForceFinishQuest
SpawnQuest
SetQuestRefToHeroComponent
K2_DestroyActor
```

因此 FireQuest 的完成是**计数/事件驱动**：统计完成的 fire/rescue 事件，达到数量后 publish/finish；不是按 F 直接完成。

### MatQuest_BP

```text
class       MatQuest_BP_C
Tags        Mat
BoxExtent   (450, 450, 32) cm
```

调用模式与 FireQuest 相同，也是 counted events。

### BaseQuest_BP

```text
GetGameState / GetDistanceTo / Add_FloatFloat
QuestClearFunc / CheckQuestFuncLib / SpawnQuestFunc
```

走距离/QuestFuncLib 的检查，没有 F-key 完成路径。

## Web 当前

- 用真实触发半径做 proximity discovery；
- `?quests=1` 只显示触发范围和提示；
- **F 只是检查提示，不推进任务**；
- 不实现计数/RescueEvent/PublishQuest 状态机，避免伪造完成。

清单：[quest-behavior.json](quest-behavior.json)

## 下一步

1. 恢复 FireQuest 的具体计数对象（FIre1..4/MainFire/RescueEvent 目标）；
2. 恢复 MatQuest 的 SpawnPeople/救援流程；
3. 接入 `SendHeroPoint`/`PublishQuest`/`ForceFinishQuest` 的实际奖励与 UI；
4. 与任务存档状态联动。
