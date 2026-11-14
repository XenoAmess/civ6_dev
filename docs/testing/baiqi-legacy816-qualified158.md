# 142重读旧ARMED158：补齐活动资格，取消仍不合法

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-legacy816-qualified158-2026-11-15.json)。保护原85中断档629900字节／SHA256 `53a08d9f9eff2fb65a5bc93a11b938b78c5f18a09b50c75dddb6b58a73d9c579`，另克隆再以当前142正式加载／当前日志Continue一次；[现代342修复档](baiqi-automatic-repairs342-814.md)保持。

旧158／地图44×26／14城／58单位，原移民8650807仍10,19、2行动、单独编队、伤害0。目标846可见、无主、非城市。UI和Core原账本ARMED／settle:0:1／0:156:173及empty=true／conflicting=false均相同。UI本次同时读到active=true、strategic=true、busy=false、processing=false，两种原版CANCEL资格仍boolean false；这补齐[97旧读](baiqi-oldarmed97-native158.md)缺少活动资格的范围，不能扩大为永久取消禁令或网络派发已空。

Core后一个只读时点亦active／strategic=true、HasPendingOperations=false／GetOperationType=−1。UI没有GetOperationType，Core没有GetQueuedDestination与UI忙碌端口；缺失明确UNKNOWN，不借另一上下文值凑完整或称原子读。0取消／唤醒／移动／建城／END158／探针写属性，旧恢复FAIL保持。

816候选5547输入／1236输出、8383.8860ms、TTFT897.9163ms，完整stop／DONE／strictJSON。两代码字段仅包装并返回字符串，实际不执行探针；解包后又用未提供的Game.IsTurnActive等，整拒／0Native。Owner读器采用实际p:IsTurnActive、完整ID、账本与条件资格。纯读取仅双Lua编译及无写者审查，未为低风险查询额外制造mock测试。

Owner自己的两个适配遗漏单列：载入原件只有messages而Continue消费者期望receipt，首读在任何输入前KeyError，后续直接验证原始精确ACK、未改原件；Core共用UI GetUnitType失败，实测GetType才是实际接口，保留失败后另立Core2。当前SettlementUnitCore原本就用GetType，不能把Owner诊断错误说成产品错误。现代地图专用就绪GUARD没有用于旧小地图。

当前142旧158基线另存630000字节，SHA256 `7c22f1aae87cd029799fcaab08e9618519aaaae66ce623154b358a7203dbdda5`。原移民／日志保持，供后续独立扩张策略测试；原档与现代成果均未覆盖。源码确认所有活移民计入maxSettlers=1，会阻止新的正常移民生产。817正在评估有硬上限的独立生产方案，尚未改变原记录或授新行为通过。

截至816累计816逻辑／757完整／56length／3最终transport／846HTTP／30extra；817后到候选另案。Nov15同机维护成功缓存复用，新增OpenCode原生工具0，未知成本null。Steam离线、0上传／模式切换／截图；TC-036实测142 PASS与其余未闭合范围保持。
