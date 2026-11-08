# 旧 ARMED 恢复：原版 CANCEL 入口尚不构成撤销证明

2026-11-09，机器 `BF-202609141645`。本轮继续检查[旧 82→85 的 ARMED 失败](baiqi-armed-upgrade-and-native-api-85.md)，没有加载或操作该旧演员。本机仍是 97 的已正式重载 176 正案，9 城，产品代码未变。

原版 `Base/Assets/Gameplay/Data/UnitCommands.xml` 声明 `UNITCOMMAND_CANCEL` 可在 UI 显示、INPLACE、HoldCycling=false。`UnitPanel.lua:459—465` 为间谍单独路由取消任务；非间谍仍会进入 `466—471` 的普通命令资格检查。因此不能把该入口说成仅供间谍使用。`EspionagePopup.lua:481—486` 确实会对间谍调用 RequestCommand(CANCEL)，但这并不是模组的代码，也没有给出移民未决 FOUND 的取消语义。

`WorldInput.lua:813—834` 的 `UnitMovementCancel()` 清除显示路径、关闭镜头，并在存在排队目的时重新显示路径；它由 CANCEL 的 UnitCommandStarted 事件触发。这里是视觉响应，不能据此报告所有原生派发队列已空，或把事件当成特定 `request0:156:173` 的取消确认。

当前 Core 在新的 PREPARED→ARMED 写入／读回后只授予一次发令；ARMED 的检查通过实际自有新城和原演员消耗转为 OBSERVED。现有保存格式没有已确认取消状态。名字“Cancel”、资格 true、void 返回或 UI 路径消失，都不能自动替换这条持久协议的效果证明。所读 Lua 没有提供 C++ 的完整取消实现，这既不是证明它能撤销，也不是证明它不能撤销。

本次只读核对当前自有斥候 `196610@51,28`：3 行动力、单体、HasPendingOperations=false、QueuedDestination=nil；实际 CANCEL hash 为 `533311341`。按原版 UnitPanel 的两种 CanStartCommand 签名读取，均返回 boolean false；没有请求 CANCEL、WAKE、MOVE 或 FOUND，没有写属性。这只说明这个闲置演员的当前资格，不推广成所有斥候或移民都不支持取消。

本地模型 557 完整 stop／SSE DONE／外层合法 JSON，1 次 HTTP，13981 输入＋1059 输出＝15040 tokens，耗时 `9.1455516` 秒。关于视觉路径及命令开始事件的两个事实、间谍专门路由和 NOT_PROVEN 的窄结论可采用。它还错误地把原版 EspionagePopup 的 OnAbort 标成 `BaiqiSettlementIntentCore.lua:481—487`；该文件仅 124 行，且不含该函数，此引用拒绝。它遗漏了已给出的普通命令路由，并把文档已确认的 HasPendingOperations 泛称为未知 API；这些表述由负责人纠正。关于整个工程是否有引擎事件更新日志的断言也没有获得完整工程证据，不采用。

不增加新的取消许可，不清 ARMED／LEGACY、不重放 FOUND，旧失败继续保留。下一步只能在明确夹具中核对取消适用状态、原生效果以及能否关联到原请求；健康军队的玩家取消实验也不能直接替旧移民提供取消回执。当前只读调用没有授予这样的行为通过。

本包没有软件修改或新测试方法。累计 557 逻辑任务／519 完整 stop 合法外层 JSON／35 length 丢弃／3 最终传输失败／587 HTTP／30 额外尝试／0 新 OpenCode 原生生成，当前在途 0。复用 11 月 9 日同机同用户每日维护成功缓存，installed/latest 1.19.5、updated=false；缓存 tokens、负责人有效时间、净节时未知，保持 null。原始请求、SSE、候选和本机原版摘录只留忽略目录，公开文件仅保留事实、调用签名及[结构化证据](../research/baiqi-p6-cancel557-source-qualification-evidence-2026-11-09.json)。

Steam 外机正在使用，0 次模式切换、上线、登录、下载、上传器初始化或上传。完整恢复、宗教、兼容、性能和完整 40 项仍开放。
