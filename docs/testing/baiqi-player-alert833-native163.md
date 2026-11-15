# 玩家军队警戒与145普通162→163

2026-11-15，BF-202609141645。[证据](../research/baiqi-player-alert833-native163-2026-11-15.json)。同一145冷实例、119安装哈希保持。[833原稿拒绝及软件切点](../research/baiqi-military-alert833-software-2026-11-15.json)不回写；本页增加后到实机结果，未新增模型调用。

TEST_PLAYER完成161原版议会：森林条约B／雨林、间谍协定A／窃取科技提升、外交胜利A／白绮、世界运动会支持各1票，提交复核总花费0。原版OnAccept自身请求一次普通结束，不能算Owner重放先前END161。独立实际162，结果页确认森林B雨林平局通过；间谍结果实际选陷害总督，不等于玩家选择科技提升获胜。返回游戏一次；支持点721→738跨回合的变化不作单纯投票费用归因。南京移民162为34/220，163为51/220，原队列仍在。

Owner军队警戒工具仅TEST_PLAYER、精确限于161已执行玩家SKIP的34个完整ID；排除原本SENTRY的旧侦察兵1114120。每单位原生ALERT资格、单编队、健康、无pending／queued及当前领袖／单人／回合／位置／选择单位均检查，临发令再次FindID和合法性重检。独占意图先于动作；冷实例级issued账本先记再发，不重置或重发。46个双Lua隔离场景覆盖新鲜变化、非法单位、已有意图和请求异常后的拒绝重放；已知ALERT待执行门26场景与实际普通END双编译通过。

首个1048576在162收到一次警戒，随后Owner只读脚本数字相邻and编译失败；新读回又因过早要求立即SENTRY而断言失败。真实状态是原位13,16、健康单编队、queued=nil、pending=true、ACTIVITY_OPERATION1225574625、两种ready均false。无军令重发／取消。其余33军队原版SKIP后，普通END162一次，独立实际163；该单位仍原位、pendingtrue且无需重新下令。正常结束保留这条已知玩家警戒，未知pending军令仍拒绝。不能把这种等待写成pending清空或立即转SENTRY。

随后163仅对同一原34名单中其余原生ALERT合法单位各发一次，共26个；每个独立读回原位／健康／单编队／queuednil／pendingtrue的原生待执行活动及非ready。合计27条独立玩家警戒，0背景军令、0军队MOVE、0文职或生产输入；不合法单位继续普通SKIP，不改变玩家军权。163原页中ACTIVITY_OPERATION不称SENTRY；跨下一回合的整批持久性及后续冷重载另验。脚本仍有旧ALERT162_COMPLETE文本标签，实际行turn与phase收据均163，不能据标签误记回合。

Owner另有两个只在Python入口发生的错误：续行三元表达式缺空格导致解析失败，及新END包装缺life全局导致main前NameError；都在相应游戏动作意图前失败，原日志保留，修正后才执行。前者不会重放首批请求，后者不是第二次END162。随后有界窗口在163因原版单位阻塞停止，0END163；834只读普查62单位、1个ready／41个pending，唯一ready为自然学家9306162。原生SKIP=false、SLEEP=true、无安全公园目标，现有只试SKIP的托管待命缺口成立，未人工跳过或移动自然学家。163现场保存644722字节，SHA256 `4cf2b8223b1ffc7f080f5a3a178bfaf4071f08d86c91348dce6707dd702ecc34`。继续修复并冷验；旧ARMED恢复FAIL、完整功能和145性能仍开放。

834完整stop/DONE/JSON，1050+483tokens、3491.9592ms／TTFT401.8962；只读代码部分采用，Owner把两种ready标志相加的重复计数改成每单位一次，补选中单位owner和最终blocker。双Lua编译／无写审查后上述Native普查成立，没有为纯读取另造mock。另一次Owner端口读取误把第三参数true作为CanStartOperation参数而抛异常；改回已核nil第三参数并逐操作pcall后读到睡眠资格，0游戏动作。累计834逻辑／771完整／60length／3transport／864HTTP／30extra，835后继修复候选另案。
