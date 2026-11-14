# 全脚本实际日历与构建／784—785

2026-11-14，BF-202609141645。[结构化证据](../research/baiqi-pressure-observed-calendar784785-2026-11-14.json)。全脚本构建器／驱动新增pressure_initial_turn，严格T为0—2147483641、source142、bounded_zero=True及4096保留上限。构建器只在私有BaiqiExecutor的仪表化源码前增加P6Q20PressureBuild，source为baiqi142-pressure-observed-v1、版本142／实际T；已有同名对象在覆盖前拒绝。其余96个Lua的仪表化字节、33上下文分配和4096总上限保持，产品119源不变。

全脚本采用**6次**普通结束T—T+5，观察五个活动窗T+1—T+5各10秒，在实际T+6激活时收尾，不结束T+6；与配对计时5段后停的口径明确分开。压力驱动在初始化、预留、轮询及完整停止时核build／stage来源与T；异常退出按自有token停止诊断，不因被篡改的压力元数据阻碍撤销自有采样。普通回调继续精确4字段ACK，不引入配对桥依赖；未知READY、动作ACK或传输结果不重放。默认None保持旧85—91行为和结果结构。

11项新方法与37项原观测相关方法通过，共48个唯一方法。构建测试实际生成默认与T6两套119文件／97Lua双编译包，差异仅Executor压力前缀，核验元数据、ZIP逐项内容、源哈希和4096分配；真实头部在Lua51／53执行并验证对象碰撞保护。驱动在33个合同替身的Lua53环境检验T0／T6／最大边界六END／五窗及收尾，所有生成查询另经Lua51解析；不冒称运行33个真实Native上下文。异常模式／无效builder头／stage篡改、丢ACK／READY、未激活超时、外交与只读故障均覆盖。

Owner初版新测试有一个无效时钟断言：把表达式与turn*0比较，不能证明10秒间隔；已换成实际回调时间对激活anchor+10的检查，并重跑6方法。最终计时结论不依赖原断言。

784输出6500达到上限，半截正文未读、整体弃用，驱动由Owner接管。785完整候选7锚点均唯一，实际默认与pressure包都能双编译，但接受bounded_zero=1和int子类，默认metadata额外加入3个None字段；压力metadata还缺source／initial_turn正确字段，把窗口写成字符串。Owner修精确类型及条件元数据，部分参数／头部／mode／ZIP／CLI思路采用，0原测试。

额外独立构建核验确认默认119个内容哈希及ZIP解包字节与785之前全等。首轮Owner错误地把包含archive_sha256的全部metadata也要求相同，失败后未重建或改原件；逐项比较证实仅容器摘要不同，97个Lua ZIP成员时间戳不同，其余metadata在移除原稿3个错误None字段后相等。因此只授内容兼容，不声称整个ZIP字节一致。

T6完整私有压力包已准备，SHA-256 `7ce568328093e39624fb2e4cc36b62f527cb3a467b9a0bc4bcddc7e244d56b3b`，窗口7—11、实际12收尾，尚未安装。后续仍须固定实际初始读回、当前实例离线确认、相应配置60秒预热／正式重载、全部上下文与质量证据。自然12资格另见[独立F观察](baiqi-pressure-natural12-fixture.md)，不授压力计时通过。

7849401input／6500output、41689.960ms length；7857279／1120、10841.314ms stop／DONE／strictJSON，各1POST，在途峰2、共同10.840002秒。累计785逻辑／727完整（含历史JSON拒绝）／55length／3最终transport／815HTTP／30extra；维护成功缓存复用、OpenCode原生0，未知缓存／server并行／负责人完整成本保持null。主334及各冻结存档保持，Steam0联网／上传、0截图；TC036仍PARTIAL，继续正式压力验收。
