# 原生写入覆盖清单：59版静态核对

本表对照[TC-036冻结协议](baiqi-performance-protocol.md)整理实际59源码，补齐N_req及全模块计时的观测边界。它不是已安装的观测器、运行次数或预算通过证据。源码固定在[6b246ee](https://github.com/XenoAmess/civ6_dev/tree/6b246ee6d2ad8da926aaa03ac8d5dae557bb2f19/mod/Baiqi)。

| 上下文／实际生产者 | 实际写入边界 | 调用路径及仍缺证据 |
| --- | --- | --- |
| BaiqiExecutor／Controller的词法辅助函数RequestCivilian、RequestCivilianStandby、RequestMissionary、RequestDistrictPerson、RequestProphet、ProcessCreative、ProcessCity | UnitManager.RequestOperation／RequestCommand、CityManager.RequestOperation，共7处源码提交点 | Tick由RunNow或Update进入。NextRequest分配逻辑关联号，不等于原生提交数或实际效果；根函数计时未记录每次提交。59分阶段建造最终仍到原RequestCivilian，没有新增提交API。 |
| BaiqiExecutor／Admin的Pantheon、Religion、Governors、Dedication、GreatPeople及Run | UI.RequestPlayerOperation，共9处源码调用点，具体操作由枚举及参数区分 | Once只是模块去重，不共享Controller预算。实际调用次数仍须全回合记录。 |
| BaiqiExecutor／Admin的Government | culture:RequestChangeGovernment、culture:SetGovernmentChangeConsidered | 前者改政体，后者是决定保留政体后的原生确认状态写入；都绕过静态UI提交代理。54清单遗漏后者，不能记成新加玩法。 |
| BaiqiExecutor／BaiqiAdmin.Run | culture:RequestPolicyChanges | 此调用在Run末端，不在Government辅助函数中；对象方法需独立观测。 |
| BaiqiExecutor／Recover | UI.RequestPlayerOperation(EXECUTE_SCRIPT) | Update及RunIfReady在规划根包装外调用；RunIfReady又由加载完成／本地回合激活进入。只在currentEntry存在时记动作会漏掉此提交。 |
| 玩家WorldInput／BaiqiActions.Interact确认回调 | UI.RequestPlayerOperation(EXECUTE_SCRIPT,fresh) | 选中军队与敌城交互、报价重核、玩家确认后才提交；不能归为AI后台征城。继续正常进攻分支调用原生移动，亦属玩家输入。 |
| 核心Gameplay／BaiqiCapture的词法Execute | CityManager.TransferCity | OnRequisition调用Request，Request再进入Execute。须关联同一requestID，不能把同一UI代理转发记成第二份UI提交，也不能因此漏掉实际核心转城效果。 |
| 核心Gameplay／词法Settle及Recover | treasury:ChangeGoldBalance、UnitManager.FinishMoves；unit:SetProperty | 结算、行动消耗及单位回合标记分别留账；Recover只结算已有可核回执，不重新发起转城。未知结果冻结。 |
| 核心Gameplay／Persist、Recover、OnRequisition | player:SetProperty：征城日志及结果 | 日志状态写入与效果分项，不凭ARMED／SUBMITTED认定游戏效果。 |
| 核心Gameplay／MigrateStandby | player:AttachModifierByID、前后player:SetProperty | 通过恢复事件按原生待命资格处理一次迁移；附加效果、提交意图及返回态分别记录。 |
| 核心Gameplay／RetireLegacyControls | plot:SetProperty、Game.SetProperty、player:SetProperty | 加载脚本末次恢复事件及OnGameTurnStarted可能触发；旧粮仓／暂停状态清理不得退款或制造收益。它不在两个UI根规划包装中。 |
| 核心GP／Creative／Religious意图模块的词法Persist、Load及桥入口 | player:SetProperty | ExposedMembers桥导出受保护的词法函数，Baiqi*IntentGameplay空表不是Prepare方法容器。初始化、回合／恢复事件的Bootstrap，创作原生事件及Inspect／Prepare／Observe等实际路径分别核对；不能仅包装Prepare或只测UI根函数。 |
| 原版界面中的BaiqiUIGuard | NativeUnit／NativeCity的RequestOperation与RequestCommand、NativeUI.RequestPlayerOperation转发 | 仅合格转发才有底层提交；资格查询不算写入。代理链一次实际调用只记一次；玩家军队／外交与后台来源分项。 |

源码提交点是静态位置数，不能乘回合或当作调用上限。实际原生写入、核心效果、持久状态都必须保留原始数量和关联，不能因分类就从N_req漏计。ACK、接受、效果与冷重载保持分别验收。当前[NewQueryCounter](../../tools/lua/diagnostic_queries.lua)可复用来透传静态API并记桶，不另造一套相同计数器；对象方法、跨上下文来源与完整还原尚须单独验证。

模型230的“根包装内所以无观测缺口”结论已拒绝；其SetGovernmentChangeConsidered清单项核实后保留。231分类作为参考，错误函数／行号及遗漏由负责人重写；旧54已列Recover、政体／政策及核心效果，不能冒称这些是新发现。[逐案证据](../research/baiqi-p6-write-coverage230231-evidence-2026-11-03.json)。

两个入口的十秒包含耗时不足以判全模块B_turn或全回合N_req。59软件594项通过，59五窗口实机此记录冻结时正在进行；此前[58普通包性能仍FAIL](../research/baiqi-p6-performance-native58-evidence-2026-11-03.json)。下一步完成实际全模块入口／写入账本、恢复核对、跨上下文计时校准及行为关闭匹配对照；不降低20／50ms等冻结门槛。
