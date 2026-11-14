# MANY压力：四项冻结预算通过

2026-11-15，BF-202609141645。仅适用于精确MANY_WATER1基线459a46e5…、实际T6、源码142；[独立自然≥12资格](baiqi-pressure-natural12-fixture.md)、[初始细读](baiqi-pressure-initial-readiness786787.md)与性能数据分开取得。NO_SITE尚未实测，[完整压力矩阵](baiqi-pressure-performance-results.md)和TC-036仍PARTIAL。

| 冻结预算 | 实际结果 | 判定与证据 |
| --- | --- | --- |
| B_plan：两目标p95≤20ms／最大≤50ms，各≥100纯十城 | Admin140样本p95 2.000093／max4.000187ms；Controller160样本p95 1.000166／max21.999836ms | PASS，[H](baiqi-pressure-many-stageA-H.md) |
| B_turn：五个固定10秒窗各≤1000ms | 142.000198／124.001265／154.000282／127.997398／228.997707ms，p50 142.000198、p95=max228.997707，>1000为0 | PASS，[I](baiqi-pressure-many-fullscript-I.md) |
| N_req：五个完整回合各≤64次原生提交 | 2／2／2／2／4，p50 2、p95=max4，>64为0；收尾12的2次另列 | PASS，[I](baiqi-pressure-many-fullscript-I.md) |
| B_delta：25段总体差值中位≤500ms、逐段对照比例中位≤10% | 中位6.999969ms／0.780376%，全部对照分母非0 | PASS，[五组原值及分析](baiqi-pressure-many-pairS-group5.md) |

B_delta差值p95为743.999720ms、最大1584.000111ms，严格>500ms共2段；比例p95为80.957519%、最大176.195799%，严格>10%共5段。全部正负值、尖峰和世界差异保留。冻结判据用总体中位数，没有逐段、逐组、p95或最大值附加门；也没有扣除外交或忙碌墙钟。单个较高值不被解释成确定的模组独占CPU。

S系列10个独立冷进程按启用先／对照先交替，每次当前Steam离线证明、EXE／CPU1—8／三份设置指纹一致，预热≥60秒后重新载入原459a副本。每侧普通END6—10各一次、原生激活7—11，11固定活动窗后停止，无END11。50次军队SKIP请求的逐回合ID／类型顺序相同，无同回合重复；回执、排队物理执行与原生激活仍分别表述。所有侧时钟错误／拒绝0、采样城市数10、检查点已保存、自有进程已收尾，没有人工文职／生产填补或UserForced。

正式采样期间没有本负责人构建、测试或HTTP。最初环境重叠的整侧和R1零END中止原件独立保留、不混入25段；[拒绝与纠正](baiqi-pressure-pair-overlap-rejected.md)、[固定只读恢复](baiqi-pressure-visibility790791.md)说明真实执行边界。没有截图、Steam上线或上传。产品142的119文件及发行ZIP2457efba…不变，主334独立保护，继续NO_SITE验收。
