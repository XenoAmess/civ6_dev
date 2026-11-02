# 原生写入覆盖清单：54版静态核对

本表用于补齐[TC-036协议](baiqi-performance-protocol.md)的N_req及全模块计时，尚不是运行计数或统一预算通过证据。依据54版实际调用者核对；本地模型202提供初稿，负责人修正遗漏的Executor恢复入口、调用函数名及征城来源。资格查询和请求提交分开，代理转发链不重复计数。

| Lua上下文／来源 | 实际调用边界 | 已有控制或观测 | 仍缺证据 |
| --- | --- | --- | --- |
| BaiqiExecutor／后台Controller | RequestCivilian、RequestCivilianStandby、RequestMissionary、RequestDistrictPerson、RequestProphet、ProcessCreative及城市生产的UnitManager.RequestOperation／RequestCommand、CityManager.RequestOperation | NextRequest限制Controller关联号；规划回调代理记录其内部提交 | 关联号会先于原生调用分配，不等于实际成功或精确原生次数；需完整回合账本 |
| BaiqiExecutor／后台Admin | UI.RequestPlayerOperation：研究、市政、万神殿、宗教信条、总督任命／晋升／就任、时代奉献、伟人招募 | Once去重；在Admin.Run内部的UI提交可被现有代理看到 | 不共享Controller计数；不能据Controller的64推断全模块上限 |
| BaiqiExecutor／后台Admin | culture:RequestChangeGovernment、culture:RequestPolicyChanges | 模块内Once去重 | 对象方法不经过上述静态UI代理，需补独立实际记录 |
| BaiqiExecutor／Recover | UI.RequestPlayerOperation(EXECUTE_SCRIPT) | 恢复／待命解锁的一次性状态 | Recover在规划包装外执行；现有代理在没有currentEntry时不存动作，不能当作零提交 |
| 玩家地图交互／BaiqiActions.Interact | UI.RequestPlayerOperation(EXECUTE_SCRIPT) | 用户选军队、与城市交互及确认代价后才提交 | 独立Lua上下文；与后台请求分项，并关联核心征城执行 |
| 核心Gameplay／征城执行及恢复 | BaiqiCapture.Execute的CityManager.TransferCity；Settle的treasury:ChangeGoldBalance、UnitManager.FinishMoves | 持久事务及恢复逻辑 | 这些是玩家征城事务的核心效果，不能标成后台主动征城；须记录真实调用及事务关联 |
| 核心Gameplay／迁移及意图回执 | MigrateStandby的AttachModifierByID；GP／创作／传教士桥与征城日志的持久状态属性写入 | 现有模块保存意图及回执 | 效果调用、授权、状态记录分别列账，不能凭状态ARMED或属性写入认定军队动作已经执行 |
| 原版UI／BaiqiUIGuard代理 | NativeUnit、NativeCity、NativeUI的转发 | 可拦截托管对象，手动军队与外交放行 | 同一提交经过代理和原生边界只记一次；玩家普通军队输入另账，不能算作AI指挥 |

原生查询CanStartOperation／CanStartCommand／路径读取不算动作提交；提交ACK、引擎接受、实际效果和读档保持也是不同证据。54版新增[资格查询计时工具](baiqi-diagnostic-profile.md)只解决查询耗时归因，不补齐本表缺失的写入覆盖。

下一步先在明确持有的上下文记录完整回合、调用序号、来源及同一事务关联，验证代理只透传一次并可完整还原，再汇总协议要求的实际提交与核心分项。只有Controller／Admin的10秒回调样本，不能证明整回合N_req、全模块B_turn或行为关闭对照通过。当前[53版五窗口](../research/baiqi-p6-performance-native53-evidence-2026-11-03.json)仍为TC-036未通过；54版尚在实机复测。
