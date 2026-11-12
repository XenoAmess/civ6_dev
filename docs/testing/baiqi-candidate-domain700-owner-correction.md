# 700：512生产候选与移民推荐分域纠正

2026-11-13，BF-202609141645。[逐项源码依据](../research/baiqi-p6-candidate-domain700-owner-correction-2026-11-13.json)。Owner在[698699审阅](baiqi-acceptance698699-owner-review.md)及共享摘要中提“配置候选上限512”时没有充分写明领域，可能误导为移民城址数量上限。本页明确纠正，旧blob、请求与候选保留；699擅定>1000夹具的拒绝依据是合同无此要求，不能用另一领域512作矛盾证明。

| 对象 | 当前源码实际边界 | 不能推出 |
| --- | --- | --- |
| 城市生产 | ProcessCity/Add的checked资格计数最多512，再做生产／操作资格 | 不限制外层建筑、区域地块、单位等遍历总工作；也不限制全地图城址 |
| 原生移民推荐 | 调用GetSettlementRecommendations(12)，实际用pairs遍历返回表 | 参数12不是本案例已测得的引擎返回长度硬上限；Lua此处无额外计数截断 |
| 既有移民目标 | ProcessSettler可把原preferredIndex合并、去重、重检 | 不能说永远只考虑原生新12项；原生若确实返回最多12项，另一个旧目标仍可能使合并前多1项 |
| 招募与移动 | ProcessCity调用RecruitAllowed；现有移民由ProcessSettler消费城址 | 两者不是模型写的ProcessSettler→RecruitAllowed调用边；firstOnly可短路，全部未合格时仍扫描候选 |

700获得完整当前Config／Policy／Planner／Controller后给出候选。只部分采用“生产和移民领域不同”的解释；其引擎硬12、遗漏旧目标、混淆调用边和笼统外层上限由Owner纠正。输入71078／输出914=71992tokens，完整stop/DONE／严格JSON，15431.6745ms／TTFT9363.4108ms；大输入准备及审阅净收益未知，不以部分采用声称节省。

0新代码、Native动作、软件测试或性能PASS。Nov13canonical1.19.5成功缓存复用，OpenCode原生0；累计700逻辑／649完整stop流（前692含严格JSON拒绝）／48length／3最终transport／730HTTP／30extra，新峰1，未知缓存／Owner总工时／净节省null。继续按真实演员及候选领域准备[协议1](baiqi-performance-protocol.md)压力，不假设全地图城址已枚举，也不把等待原因当全图无合法城址证明。
