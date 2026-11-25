# 正式版 1.0.0 · 构建185

替换工坊Alpha 3／构建172；包含173–184的12个产品工作包，不将工作包数量当作独立缺陷数。

- 50722940 Preserve player army escort commands and native argument forwarding
- db1880fe Fix nullable result contract for blocked city commands
- 0347abb2 Recover idle builder standby after transient native path holds
- 8175db03 Allow guarded one-edge civilian evacuation from threatened overlaps
- a05d328c Recover production blocked by visible hostile district occupation
- 1c46d488 Consume a confirmation double-click before it queues map movement
- b39a431f Reconsider temporarily unavailable city production at bounded intervals
- 894af49e Recover production blocked by walls superseded by urban defenses
- 1a594012 Respect saved player raze choices throughout peaceful expansion
- 7895e902 Recover autonomous research from completed UI selections
- 85b4ee88 Accept passive governor loyalty effects in unassigned cities
- 21201c94 Defer initial builder path queries to the next callback

固定40项及12项性能指标在规定GS单人环境完成。详见[验收范围](KNOWN_ISSUES.zh-CN.md)及[发布字节清单](verification.json)。

正式版资格及185元数据变更影响：[审阅记录](stable-assessment.json)。
