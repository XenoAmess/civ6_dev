# 669：回合转换时停止后续输入

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-phase2-transition-model669-2026-11-12.json)。模组源／安装／运行129不变，只修改私有验收驱动。

END295已返回后，fresh-state仍见active true，但下一次pending只读已active false；旧assert误报失败，实际0额外输入。669先提供完整1750+1338=3088tokens／8378.2509ms／stop／DONE／合法JSON候选，12个无真实IO／Native／子进程的隔离场景通过，整份审阅后用于私有after_end。pending非零、缺标记、已失去操作权或已到下一回合时，只打印PHASE2_NO_DEPENDENT_INPUT并落到末尾既有只读监视器；不progress，不重试pending或使者动作。使者前置异常继续失败退出，新鲜合法军事SKIP仍阻止progress，原帧解析不改。新增分支本身尚无真实pending漂移触发样本，不能把软件覆盖写成该分支实机通过。

Owner最初误读嵌套JSON转义，隔离原件证实制表符正确、0修改；AST夹具也先修正了把list交给ast.dump的问题再采用，两者不算模型失败或HTTP重试。未经审阅原件0Native；经审阅整份候选已用于私有驱动，不称产品代码采用。

独立监视END295后实际5context同295返回NPC_BLOCKED，原图为巴西谴责，测试玩家“再见”一次，再独立296 READY，补上此前666待定的NPC实机分支。295→296跨回合守卫NO_LOSS，历史上海损失仍携带；邢州自然11→12。控制论自然完成，BACKGROUND接续预测系统74，实际0/1150，煤／油／铀0。尚未完成海上风电解锁或施工。

296首先1次正式无REASON结束已返回，90秒监视未到297。新鲜原图仍同回合，独立读取先前排队的建造者7798799已从60,30到原2205／59,29，完整ID／owner／formation1保持、queued nil；新鲜pending剩余军队SKIP均false。[原测试玩家流程](baiqi-test-player-turn-workflow.md)明确正式动作可能先执行排队移动而留在原回合，因此以新意图queue-settled296再发1次正常UI.RequestAction(ACTION_ENDTURN)，不加REASON，不重放未知文职动作，也不把ACK当297。本记录尚不声明实际297结果。

为后续真正项目提交前读数，复用原Owner665未改Lua逻辑，295主线恢复后以新命名空间安装临时观察器；0自发游戏命令，尚未据此授正燃料项目分支通过，未来保存前需还原。累计669／623完整／43length／3transport／699HTTP／30extra；同机同用户每日维护缓存复用、OpenCode原生0，未知成本null。继续预测系统／实际海上建设／持续供电，上海与旧人口矩阵开放；Steam离线／工坊82。
