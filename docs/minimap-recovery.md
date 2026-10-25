# Minimap / HUD 图标恢复记录

## 已恢复

`DT_MinimapIcon` 的 NameMap 给出原版图标表使用的 14 个 Texture2D：

```text
destruction32
flight32
quest_accident
quest_fire
quest_terrorist
T_BossIcon
T_BossIcon_Fire
T_BossIcon_Lightning
T_BossIcon_Wind
T_CityDamage
T_EnemyIcon
T_FlightRing_G
T_FlightRing_N
T_StoryPointIcon
```

已从原 pak 的 `/Game/-HeroGame/Res/UI/` 导出为 PNG，清单：

`research/world-recovery/minimap-icon-manifest.json`

## Web 当前使用

- `quest_fire` → `kind === 'fire'` 的任务触发点；
- `quest_accident` → 其他（当前 `kind === 'material'`）任务触发点；
- `T_StaticMinimap_Tex` + `map250` + `T_PlayerIcon` 已作为默认 HUD；
- 默认显示最近 8 个任务触发点；`?minimap=all` 显示全部 21 个 recovered trigger，仅用于检查。

## 未恢复

- 原版 active/completed quest 的图标颜色/大小状态机；
- 敌人、Boss、飞行环、城市破坏等图标的**运行时放置**与条件；
- `M_MiinMapChangeVisualizer` 的完整 tint/filter 逻辑；
- 因此当前图标布局仍是 recovered trigger preview，不是原版图标状态机。
