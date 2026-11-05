# 74版：地图外对象仍通过征城恢复的软件反例

2026-11-05，BF-202609141645。实际Capture／Requisition／Policy／Planner和现有mock_requisition形成真正转城、扣款及UNKNOWN回执后，保持军队完整ID／owner／类型／编队／行动，改其读值为地图外、延迟销毁。当前74在CHARGED和FINISHING两阶段都继续调用FinishMoves替身、写冷却并记COMMITTED／DONE；两个正常军队对照也完成。[结构化四例、源码指纹及模型413审阅](../research/baiqi-p6-capture413-removed-actor-software-evidence-2026-11-05.json)。

| 项目 | 中断后的真实软件前态 | 当前74恢复后 |
| --- | --- | --- |
| 收据 | UNKNOWN／CHARGED或FINISHING；transferObserved／chargeObserved真 | COMMITTED／DONE |
| 费用 | 初1000，已扣400，当前600 | 仍600，未二次扣款／退款 |
| 正常军队 | ID9／owner7，2,2，行动2 | Finish1，行动0 |
| 地图外军队形状 | 同ID／owner，-9999,-9999；IsDead=false、IsDelayedDeath=true，行动2 | 同样Finish1、写冷却8、行动0 |

没有直接拼造journal或改COMMITTED；先由真实Request／阶段中断创建正回执，再只覆盖软件单位的读取方法。结果指出的是恢复缺少地图位置／延迟销毁资格，TC-018要求不访问已删除对象。本例没有重复收费，不能另写成已复现双扣或退款漏洞。

Native来源是[411移民真实建城后](baiqi-settler-recovery-founded-74.md)的Core对象：完整ID／owner保留，坐标-9999，IsDead=false／IsDelayedDeath=true，119重载也如此。那是移民，不能通过军队类型条件；因此目前不是实机军事恢复故障。Native FinishMoves面对同形状军队的实际后果尚未测，软件替身的动作不能授为引擎动作。

413候选Python编译，但93行超过75行要求，吞partial异常，使用无self的Python lambda，并在注释／limits说设置了死亡标志却没实际赋值。原稿0软件／游戏执行；负责人只参考实际class与CHARGED注入方向，另用Lua方法覆盖、保留异常和四组前后值形成该反例。412上一轮length原件已整体弃用，未拼接。

当前源码／安装／运行仍74，正常114已恢复且测试绑定清；正在审阅414最小资格守卫候选，然后补真实Capture回归、必要完整软件检查和Native复测。修复未完成前不授本项通过；完整40项仍未完成。
