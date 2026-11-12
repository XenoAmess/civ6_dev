# 698／699：恢复历史与性能压力候选审阅

2026-11-13，BF-202609141645。[结构化证据](../research/baiqi-p6-acceptance698699-owner-review-2026-11-13.json)。两份都是普通HTTP完整stop/DONE／严格JSON，698为19801tokens／7277.8312ms，699为9993tokens／13369.4700ms，实际峰2／重叠7.277938秒；没有新增代码采用、游戏动作、测试PASS或性能结果。

698未找出新的Capture缺陷，所列CHARGING冻结是已有正确行为，具体门在private Recoverable，不是其标注的public Recover。候选把mock的throwAfterTransfer／failCharge软件场景标成P4实机，不能采用。它建议的TRANSFERRED／CHARGED“缺少实机”也不能作全项目盘点：Owner包只给P4/P5及test_requisition，漏了[27冷恢复记录](results/2026-11-01-p6-acceptance.md)、[74冷态](baiqi-cold-recovery-74.md)、[75CHARGED](baiqi-charged-before-cooldown-75.md)和独立test_baiqi_capture_recovery。后者已有确定阶段、故障及缺reader回归；输入遗漏由Owner记账，不称模型忽略已供源码，不为补数重复旧绿。

699保留了[67四预算／25配对已满足](baiqi-performance-67-baseline-results.md)的范围，但整份压力方案拒用：虚钉69文件、把4096记录上限混作内存上限，以“丢弃超过4096”替代任何丢弃即失完整性，并擅定>1000候选和新增地貌压力为既有义务。所提 `--paired-clock true` 实际独立CLI见证退出2／unrecognized arguments:true，0输出目录、0安装。真实parser为store_true，应单传flag。当前候选上限512的生产者／配置也未放进699输入，这项准备缺口由Owner承担；不把历史十城85固定档要求机械扩到所有新压力地图。

继续[协议1](baiqi-performance-protocol.md)下真正缺少的无合法城址／候选多压力夹具；先给齐当前生产者、消费者、配置及已有测试，保持4096cap、冻结预算、私有对照和发布版无开关。136住房实机[另包](baiqi-native136-housing-completed332.md)，不变成当前性能样本。

Nov13同机同用户canonical维护1.19.5成功缓存复用。累计699逻辑／648完整stop流（含前692严格JSON拒绝）／48length／3最终传输失败／729HTTP／30extra；OpenCode原生0，未知缓存、Owner总成本和净节省null。


后到[700领域纠正](baiqi-candidate-domain700-owner-correction.md)：512只约束ProcessCity/Add内部资格计数，不限制全部外层工作或移民城址；原生请求12也未在本案例验证返回硬上限，保留旧目标另算。本页先前的无领域512表述由Owner纠正，不以其反驳全图>1000的可能性。
