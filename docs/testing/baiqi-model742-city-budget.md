# 742城市预算测试原稿未达断言

2026-11-14，BF-202609141645。[审阅原值](../research/baiqi-model742-city-budget-2026-11-14.json)。739因真实夹具形状错误被拒后，742获得实际ProcessCity、Config、Planner、mock_world、生产与控制器测试、735原6处补丁，并要求恰两项有意义的计数测试。它仍给三项，setup直接访问真实mock中的局部city／queue对应的nil全局。原样在实际141夹具执行3项、3个Lua错误，尚未到任何预算断言，代码／测试0采用。

其文字也同时假设budget1先被Granary耗用、却期待后来的Monument请求；district方法未移除更早消费预算的Buildings，Map假设也不符。不能把这些原稿错误记成产品回归、735已通过或城市就是J71ms来源。Owner最初关于“加载后设Config无效”的审阅理由也错误：Controller的C直接引用BaiqiConfig表，事后设置有效；发布前撤回。重复完整上下文后仍无可用测试，Owner接管对应范围，不继续重发同一失败任务。

单attempt／完整stop／DONE／严格JSON，19516总tokens（2610输出），HTTP19319.8164ms／TTFT2322.3611ms，峰1。累计742／689完整流（含历史JSON拒绝）／50length／3最终transport／772HTTP／30extra。canonical1.19.5每日维护成功缓存复用，OpenCode原生0，成本null。

实际141冷实例已离线启动、原85初载预热73.563秒并正式重载一次，尚未开始本轮五窗采样；城市735优化继续未采用，后续按新实机归因决定范围。
