# TC-036 压力性能矩阵

2026-11-15，BF-202609141645。按[冻结协议](baiqi-pressure-performance-protocol.md)执行；原85夹具结论保持，各压力格独立记录。[MANY四项完整汇总](baiqi-pressure-many-complete.md)。

| 场景与精确初始点 | B_plan | B_turn | N_req | B_delta |
| --- | --- | --- | --- | --- |
| MANY_WATER1，T6，459a46e5… | **PASS**，[Native H证据](baiqi-pressure-many-stageA-H.md) | **PASS**，[Native I证据](baiqi-pressure-many-fullscript-I.md) | **PASS**，[Native I证据](baiqi-pressure-many-fullscript-I.md) | **PASS**，[25段](baiqi-pressure-many-pairS-group5.md) |
| NO_SITE，T1，92f43e9c… | 未测 | 未测 | 未测 | 未测 |

MANY的两规划目标分别140／160个纯十城样本，p95为2.000093／1.000166ms、最大4.000187／21.999836ms，满足冻结p95≤20、最大≤50。304保留行包含4个已验证激活前样本，后者单列；0丢弃／无效时钟，4096总容量不变。

独立全脚本I覆盖33上下文，1201保留样本，198时钟校准／396计时切换全通过。五窗并集142.000198／124.001265／154.000282／127.997398／228.997707ms，最大低于1000ms；完整回合写入2／2／2／2／4，最大低于64。收尾12的2次写入另列。MANY五组配对已齐，中位差6.999969ms／比例0.780376%满足冻结判据；2段>500ms／5段>10%均保留。完整矩阵和全套报告尚未完成，TC-036仍PARTIAL；继续NO_SITE性能测量。

[首配对侧整轮拒绝](baiqi-pressure-pair-overlap-rejected.md)：普通跨UI流程跑通，但Owner构建与正式测量重叠，整侧拒绝、原值保留；r系列另在0END时中止。随后s系列按同一口径完成25段，不将旧失败混入。





配对进度：[MANY已完成5/5组、25/25段](baiqi-pressure-many-pairS-group5.md)；最终判定见该报告。
