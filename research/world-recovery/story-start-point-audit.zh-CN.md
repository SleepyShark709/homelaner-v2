# StoryStartPoint 审计（未命中开始广场）

日期：2026-10-25。来源：MainLevel 解码 actor + `startup=1` 全城加载的浏览器检查。

## 1. StoryStartPoint_427

- 位置约 `(-576, 251)`；
- 全城启动 + overlay 后是一个空旷的铺装平台/海岸边，只有远处城市；
- 截图 `play-storystart1-startup.jpg`；
- 不是原程序开始广场。

## 2. StoryStartPoint_2

- 位置约 `(-3.4, 36)`；
- 全城启动后是城市街道和大型建筑/空白广告牌；
- 自动朝向看到巨大建筑立面，手动转向看到草地和建筑；
- 截图 `play-storystart2-startup.jpg`、`play-storystart2-plaza.jpg`；
- 不是原程序开始广场的砖石广场构图。

## 3. StoryStartPoint_3

- 已恢复的 z=170.9 m 高位点；
- 未作为可玩出生点验证；它更像空中/剧情检查点，不像地面开始广场。

## 结论

三个 StoryStartPoint 都不是原程序开始广场的直接答案。当前最接近的仍是：

```text
/?view=play&plaza=1
```

MainLevel `(-20,0)` + `startup=1` + 砖石 overlay + 相机净空；但地面是预览 overlay，长椅/相机/建筑仍未逐项匹配。

证据：`research/evidence/player-logic.json`、`play-mainplaza-*`、`play-storystart*.jpg`。
