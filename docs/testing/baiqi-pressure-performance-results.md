# TC-036 压力性能矩阵

2026-11-14，BF-202609141645。按[冻结协议](baiqi-pressure-performance-protocol.md)执行；原85夹具结论保持，各压力格独立记录。

| 场景与精确初始点 | B_plan | B_turn | N_req | B_delta |
| --- | --- | --- | --- | --- |
| MANY_WATER1，T6，459a46e5… | **PASS**，[Native H证据](baiqi-pressure-many-stageA-H.md) | **PASS**，[Native I证据](baiqi-pressure-many-fullscript-I.md) | **PASS**，[Native I证据](baiqi-pressure-many-fullscript-I.md) | 未测 |
| NO_SITE，T1，92f43e9c… | 未测 | 未测 | 未测 | 未测 |

MANY的两规划目标分别140／160个纯十城样本，p95为2.000093／1.000166ms、最大4.000187／21.999836ms，满足冻结p95≤20、最大≤50。304保留行包含4个已验证激活前样本，后者单列；0丢弃／无效时钟，4096总容量不变。

独立全脚本I覆盖33上下文，1201保留样本，198时钟校准／396计时切换全通过。五窗并集142.000198／124.001265／154.000282／127.997398／228.997707ms，最大低于1000ms；完整回合写入2／2／2／2／4，最大低于64。收尾12的2次写入另列。完整矩阵和全套报告尚未完成，TC-036仍PARTIAL；继续MANY五组配对和NO_SITE性能测量。
