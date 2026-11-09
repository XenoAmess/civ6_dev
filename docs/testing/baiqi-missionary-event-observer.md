# 最后一次传播的只读事件观察工具

用于继续定位[104实机139最后一次回执失败](baiqi-domestic-spread-and-final-charge-104.md)。新增工具只订阅指定自有单位的UnitChargesChanged、UnitOperationStarted、UnitOperationDeactivated、UnitRemovedFromMap，保存原始事件参数和调用者提供的只读快照，不确认传播、不调用游戏命令或桥、不读写产品属性，也不进入mod安装包。

事件参数含nil时保留实际argc，最多复制8个标量；快照限制32个标量字段并独立复制，只标RAW或UNKNOWN。记录默认64、最大128条，满后不再读快照。所有事件端口先完整核验再订阅，Add失败时连当前尝试一起撤除；Restore只重试撤除失败的回调，部分失败后也先停止采样，不重复移除已成功撤除者。

8项Lua5.1行为检查通过。原模型候选也能编译，但同8方法有10个失败事件：丢弃尾部nil参数、没有8参数限制、快照别名和非法结构、无有效回合守卫、Add异常漏撤当前回调、部分Restore重复移除成功回调。原稿整份拒绝、0实机执行；负责人独立实现。原产品1577项完整检查切点保留，本次只运行新增8项工具检查，不能写成完整1585已跑过。

577普通HTTP1请求、1830+1251=3081 tokens、7.622741秒，stop／DONE／合法JSON。累计577任务／538完整／36截断／3最终传输失败、607HTTP／30额外重试，OpenCode原生生成0，未知缓存／人工成本null。输入提供了真实原版事件签名来源、现有订阅示例与明确接口合同，不是模型自行发现API。

当前Core／UI均已只读确认四类事件的Add／Remove存在；尚未订阅实机，事件是否发出、参数及删除时序未知。已保存139失败分支，再正式加载138检查点做独立观察，只有Load ACK，尚无实际世界读回，未重发。源码与运行104保持，尚未改动最后一次回执处理。Steam他机占用期间0上线或上传，公开Alpha2仍内部82。

[结构化记录](../research/baiqi-p6-religion577-passive-missionary-event-observer-software-evidence-2026-11-09.json) · [工具源码](../../tools/lua/diagnostic_missionary_events.lua) · [8项检查](../../tests/test_diagnostic_missionary_events.py)
