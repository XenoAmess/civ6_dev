# Stage A D86仍缺锚点与独立87参数实证／728

2026-11-14，BF-202609141645。[两次不同范围的原生证据](../research/baiqi-stageA-nativeD-arguments728-2026-11-14.json)。inline Activate包新鲜offline冷启，73.250秒预热／正式原85重读；普通END85后，86仍读到1个Controller.RunNow `anchor_missing`，已知1794603719.388，86锚点1794603719.6300001。初始6、关闭记录前最终9调用／9样本，0丢弃／时钟异常／零聚合，10城；仍未通过B_plan完整性。两规划包装及自有监听已撤，原数据不Reset、不重分类；D86唯一存档503983字节，SHA256 `7564a56383abcdeae8aee09cf37c22cc35a6006dfd53a33751db7c58f671efe8`。

复核完整消费者发现：Executor将TurnReady()传给Controller.Update，后者即使false仍会调用RunNow(false)；Tick先做被动初始化／事实回执协调，false门随后阻止进入新发令部分。原先只检查Executor的直接RunNow入口不完整。为了验证真实参数，而非猜D86旧值，在保留D86后另装有界参数观察器，原函数所有参数／返回／错误透传，没有计时或补装内政。

独立诊断仅TEST_PLAYER普通END86、18次原版军事／允许支援SKIP，实际87；9条调用入口、1条原生通知记录，错误／丢弃0。第一条87调用在1794604346.9349999、恰有1个参数且确为boolean false，比这个独立观察器的原生时刻1794604347.2590001早约324ms；之后是无参数及true调用。Native事件第二参数为flag，观察器用新鲜Game.GetCurrentGameTurn取回合。参数包装及自有监听已确认撤回，正式D数据仍9调用／1资格错误。

这证明存在提前的false参数调用路径；没有测得D86旧错误的参数／完整耗时，也没有证明内部引擎首个物理通知时刻，**不追认旧失败通过**。独立87另存506005字节，SHA256 `3e885f384a92de2d979927298f682a76db758a258fedb59792a4d05c4eaae162`，已原版退出一次。受保护主333不变。

新增外部`diagnostic_plan_arguments.lua`，64入口／8通知上限，受限沙箱7方法通过：false不丢、nil孔、getter异常不阻断原函数、原错误身份、回调fresh turn、退休缓存无观察、未知Add／Remove清理不重放。该同一助手随后真实运行成功；入口记录没有duration，不是正式延迟样本。

728完整2785tokens／2739.2022ms／TTFT490.1598ms，单次stop／DONE／合法JSON。raw6探针5失败1变参返回检查过：`and/or`丢false、getter异常阻断body、把原生第二flag误当turn、退休缓存仍观察、未知Add遗留包装。0原代码采用，Owner重写并实测。

下一版拟只对精确RunNow(false)、1参数且尚无原生锚点的调用记录完整canonical区间，先保持pending，收到真实锚点后才判断是否整段完成于固定窗前；跨界、未知或锚点不到仍不通过。729是该显式版本化证明组件的未完成候选，不是本页已交付功能，所有预算与100纯十城要求保持。累计through728：728逻辑／675完整流（含历史一次严格JSON拒绝）／50length／3transport／758HTTP／30extra，新峰1；维护成功缓存复用、OpenCode原生0、未知成本null。B_plan／B_delta／完整验收继续。
