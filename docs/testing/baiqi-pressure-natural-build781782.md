# 自然池穷尽实机与配对构建器／781—782

2026-11-14，BF-202609141645。[结构化证据](../research/baiqi-pressure-natural-build781782-2026-11-14.json)。准备实例4372经正式OnExitGame正常退出、0强杀。新实例23492在Steam当前实例后台离线确认0.003705秒后启动，安装119文件启用版自然census，仅Controller作可逆观察改动，5文件地图插件保持。正式载入冻结6be8…基线一次；当次日志按0／18／31顺序确认Load返回、Controller初始化和LoadScreen完成后，向自有准确HWND发送一次Esc，独立读回126上下文和实际T1。没有截图或Steam联网。

取得10次自然recruit_choice调用，均发生在T1、开始／结束10城，raw_hints／admitted／visited均3，全部穷尽，cheap_pass2、support_false2、returned0、failed=false，0丢样／坏行／分类错误，观测容量256。10行均为EXHAUSTED_NO_ACCEPTED_SITE_IN_POOL，many_candidate_pool=false，global_no_legal_site保持null。没有人工推荐或RunNow调用；这是实际有限候选池穷尽证据，**当前单水域基线未取得≥12多候选资格**。同样不能把1132裸陆地认作可接受落点。

后台自行向10城提交纪念碑并分别读到queue_observed，10城队列均1、人口4／粮食盈余2保持至T6。测试玩家只在T1—5对同一名勇士每回合SKIP一次并各发一次普通无REASON结束，独立快照确认激活2—6，0同单位同回合重复，0人工文职／生产输入。勇士仍为131073、坐标3／4、编队数1。该证据不替代特定排队军令恢复用例。T2—6没有新增选址调用，不能推断这些回合Native推荐值也相同。

T6撤销自有census后再次导出，enabled=false／retired=true、10行／零丢弃／零坏行；未结束T6。观察存档Baiqi_P6_20261114_V142_PressureWater1Observed6，324195字节，SHA-256 `459a46e5d23d0600db7bd682a8d99f44218cc1812ba34bd6cdbe07993340da0a`。原始6be8…基线保留，观察存档不替代正式性能初始状态。没有压力性能采样／配对通过，也没有AI扩张成功结论。

配对包新增--pressure-initial-turn及Python同名参数，严格T为0—2147483641、source142、paired clock和普通END桥同时启用；验证在输出目录创建前完成。压力包将实际T传入真实桥，metadata明确source／initial_turn／五次结束和激活日历、独立mode及ZIP名。启用／关闭副本前缀字节相同；默认None及旧140／141／142前缀四个SHA与修改前全等。normal_end_driver_ready、cross_context_begin_native_verified仍false；完整Python驱动、玩家回调和实机子脚本仍待扩展。

4项新测试与6项原构建相关方法通过，共10个唯一方法。真实prefix在Lua51／53验证T0、T1、最大边界各5段；非法参数／缺选项不创建目录，两种实际119文件包的97Lua双编译、前缀哈希、元数据／ZIP和源指纹均核验。构建验证没有安装新配对包或发游戏动作。

781完整候选10个锚点中第6／9项不匹配。仅为反证作lstrip适配后，build因version赋值前读取抛UnboundLocalError，prefix因缺Lua表右花括号解析失败，输出目录未创建；metadata名称也未按合同。部分参数／范围／CLI／mode／ZIP思路采用，Owner修锚点、验证位置、注入和字段，0原测试。782达到8000输出上限，半截正文未读、整体弃用，负责人继续接管剩余驱动范围。

7817436input／1888output、17024.182ms，stop／DONE／strictJSON；78210828／8000、49382.600ms，length。各1POST，实际在途峰2、共同17.024656秒。累计782逻辑／725完整（含历史JSON拒绝）／54length／3最终transport／812HTTP／30extra。维护成功缓存复用，OpenCode原生0；负责人完整准备／修改／验证成本未知，未追记或声称节省。142产品源及ZIP未改，主334 f70b…、NO_SITE 92f4…保持；TC036仍PARTIAL，下一步继续驱动和更合适的多候选夹具诊断。
