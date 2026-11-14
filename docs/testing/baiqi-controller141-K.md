# K的移民备选扫描仍聚集多次校验

2026-11-14，BF-202609141645。[K完整分项原值](../research/baiqi-controller141-K-2026-11-14.json)。独立141冷实例、原85初载预热73.967秒再正式重载，普通END85—89各一次，90活动十秒后停止、不END90。单4096池，12子项加根共79根／1159行，0错误／丢弃／坏时钟／元数据错误；全部父子区间、根序列、真实锚点及完整尾部审计过，通知前／后分别为{'whole_before_observer': 16, 'overlaps_observer': 0, 'observed_window': 63, 'outside_window_started': 0}。

88根12最大105.000019ms，ProcessSettler97.000122ms、SettlementSites69.999933ms、PathStep25.000095ms，KnownExpansionSupport最大30.999899ms；该根有3次支持检查。该根ProcessCity最大0ms，K整轮ProcessCity最大8.000135ms、ProcessBuilder3.000021ms；不能因此追认旧J71ms为城市问题或已修复。89根57另44ms，Settler34ms，其中支持17ms／寻路7ms；88根11另33ms，Settler26ms，其中支持21ms／寻路2ms。嵌套值不相加。

K没有重现正式141的428ms尖峰，不授原因／缓存／回归因果，也不授正式B_plan通过；正式Adminp95 21／Controllermax428的FAIL保持。代码审阅可确认现有SettlementSites(firstOnly)在找到第一个合法项前仍会连续否决多个原生城址，根12的多次支持检查与此一致。下一窄任务是只对ProcessSettler备选调用逐回调检查一个候选，显式more续行、否定ID去重，RecruitAllowed默认全枚举保持；745／746候选此时待审，尚无142实现或提速结论。

90已11城并保存518738字节，SHA256 `d7b9f4382f075674817d37e024936e082febf21f7a2cfac1fac998fad130eb5b`；十三绑定／自有观察器撤下，原版退出一次，无窗口／监听／CPU静止的自有残留在237.652897秒后清理。Steam后台离线新鲜确认后启动，全程无上线或发布动作。下一独立AdminL包已准备但此切点未安装，仍需主333兼容与全功能／整脚本／匹配对照验收。
