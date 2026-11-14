# TC-036 压力性能矩阵

2026-11-15，BF-202609141645。源码142在已测GS单人环境的两种压力场景八项预算全部PASS；结合原85夹具，[TC-036实测通过与完整报告](baiqi-performance142-complete805.md)。冻结[协议](baiqi-pressure-performance-protocol.md)未改，全40项功能验收继续。

| 场景与精确初始点 | B_plan | B_turn | N_req | B_delta |
| --- | --- | --- | --- | --- |
| MANY_WATER1，T6，459a46e5… | **PASS**，[H](baiqi-pressure-many-stageA-H.md) | **PASS**，[I](baiqi-pressure-many-fullscript-I.md) | **PASS**，[I](baiqi-pressure-many-fullscript-I.md) | **PASS**，[25段](baiqi-pressure-many-pairS-group5.md) |
| NO_SITE，T1，92f43e9c… | **PASS**，[J](baiqi-pressure-nosite-stageA-J.md) | **PASS**，[K](baiqi-pressure-nosite-fullscript-K.md) | **PASS**，[K](baiqi-pressure-nosite-fullscript-K.md) | **PASS**，[25段](baiqi-pressure-nosite-pairN-group5.md) |

[MANY完整分布](baiqi-pressure-many-complete.md)；NO_SITE完整分布、请求桶、覆盖、样本质量及R4替代的精确映射见[最终报告](baiqi-performance142-complete805.md)。所有尖峰／世界差异保留，固定中位预算不增加逐段门，不作因果CPU解释。

[MANY旧重叠整侧](baiqi-pressure-pair-overlap-rejected.md)与[原N4启用侧失效](baiqi-pressure-N4-invalid-admission804.md)独立保留、不混入有效样本。N4使用全新R4启用侧及原有效对照；实际NO_SITE共11冷侧／10有效侧，未按数值筛选。各阶段文档PARTIAL均保留为历史切点。
