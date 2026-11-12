# 当前原版交易界面的煤元数据：683／684审阅

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-trade-coal-reader683684-2026-11-12.json)，[只读模块](../../tools/lua/diagnostic_trade_coal.lua)，[12项Lua5.1测试](../../tests/test_diagnostic_trade_coal.py)。软件通过，尚未接实机交易界面；当前133／308已因新人口损失保存停END。

正燃料下的项目优先级仍待实机。本工具只读取玩家已经打开的原版普通交易界面：双方身份／已见／白绮人类／活跃回合和非忙碌等先核，读取既有OUTGOING工作deal及other→local资源候选，原版实际字段ForType／MaxAmount／IsValid。完整密集表1—256严格检查，坏行、稀疏、重复煤、nil或异常返回UNKNOWN；完整表缺煤才明确返回0，保留实际煤Index。再次检查当前界面、身份、回合、绑定和同一工作deal，不能冒称跨getter原子性或成交资格。无打开界面、清空／创建deal、添加物品、报价或成交入口，也不遍历其他AI私有库存。

683完整stop／DONE／合法JSON，11539+1789=13328tokens、15516.5028ms。原稿用合同没有的otherPlayerID，合法阳性因此UNKNOWN；仅为隔离另加镜像后，稀疏表、额外metadata key、1.5数量、非plain E、最终inactive、错误other对象ID、缺煤Index0、getter被换仍KNOWN共八个缺口。原稿整拒、0Native。684完整SSE但length5000，正文未读／未解析／未采用／未重试／未拼接。

负责人完整重写，12项新测试首跑通过0.137s，覆盖精确对方供给四参数、空表／无效行、环境拒绝、端口异常、密集键／重复／坏数、当前状态与绑定漂移、最后working getter变更、重复读取无状态／结果不别名，以及元数据新包装仍可读。原副作用端口在pcall外计数均0；未改133产品或119文件包，原1933全量是be1ebbb冻结历史，不冒称重跑新全量。

两HTTP实际峰2／重叠15.516009秒，累计684逻辑／635完整／46length／3transport／714HTTP／30extra，OpenCode原生0；同机同用户当日1.19.5维护成功缓存复用，缓存收益／owner主动及净节省未知。下一步由测试玩家按原版普通外交打开界面，核真实metadata形态；若正常交易能构造正燃料场景，必须单列TEST_PLAYER交易，不算后台外交或AI取得资源。当前0交易界面打开／购买／Steam上线／上传，工坊82。
