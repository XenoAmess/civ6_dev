# Controller尖峰分项诊断／734软件

2026-11-14，BF-202609141645。[完整F](baiqi-stageA-F-complete-fail.md)已确认88回合约90ms、89约56ms纯十城Controller入口超50ms；产品仍140，未把低p95当作通过。[新私有制品与软件证据](../research/baiqi-controller-coarse734-2026-11-14.json)用于下一次粗分项定位。

新增诊断只在自身观察到88／89 Native锚点后的十秒内计量Controller.RunNow及ReadBack、ProcessCity、ProcessBuilder、ProcessSettler、RefreshSettlement、ArchaeologyPendingRead。所有根与子项共享同一个canonical profile，总容量4096，零时长不聚合；先于此观察的入口有意不采，不称完整Stage A。子项包含耗时可嵌套，不相加当总时间；插桩也会改变根开销，不用该根结果授B_plan。

10个新共享预算／元数据方法、3个实际构建／锚点／恢复方法通过。全97Lua51／53编译、119文件／ZIP逐字核对，只有Controller增加诊断尾段，原正文为精确字节前缀；原始RunNow和六处词法绑定按身份恢复，只删除自己注册的监听。原样透传false、nil、全部返回值和错误；未知读取不阻断原函数，坏时钟不冒充零，根记录缺失不会误写末尾子行。明确制品SHA256 `61f36547ac3c00e07ad467b7364fad749ab9624ce15f4a2c05f683d05d4a15a2`，此时仅准备、未安装／新Native。

734完整stop／DONE／合法JSON，66937总tokens（761输出），13045.7863ms／TTFT8481.7110ms。原样10方法5过5 Lua断言错误：serial未增导致rootId恒0、整数无上限、snapshot getter外抛阻断游戏正文、根时钟无效／容量满后未知元数据不计数。0原代码采用。Owner重写；原样运行后还加强了一处窗外返回值夹具，不回改原运行记录。累计734／681完整流／50length／3最终transport／764HTTP／30extra，本次峰1，维护缓存复用／OpenCode原生0／未知成本null。继续新冷诊断，不授性能或整例通过。
