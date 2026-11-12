# 687／688：己方完成通知的电力、燃料只读观察器

2026-11-12，BF-202609141645。[逐项审阅](../research/baiqi-p6-power-completion687688-2026-11-12.json)，[Owner模块](../../tools/lua/diagnostic_power_completion.lua)，[独立11项Lua5.1测试](../../tests/test_diagnostic_power_completion.py)。当前133／312煤2、油1；正燃料缺电与新计划配对仍未验完。本工具软件通过、尚未Native安装。

工具只订阅自己的CityProductionCompleted和CityProjectCompleted回调，跟踪给定己方城市名单1—64、固定回合范围和1—128条上限；允许忙碌／间回合读取，不发游戏命令、不替换规划函数／原订阅。逐事件双读电力、煤油铀、当前队列和UI状态，再核当前玩家／非多人／人类白绮／城归属及回合；未知／漂移保UNKNOWN和errors，不当零。完成通知与当时的非原子双读不能单独证明规划输入、奖励或燃料消费因果。

Owner修正原任务包的一处来源说明：当前Controller只订阅CityProductionCompleted；另一个CityProjectCompleted的实际三参数消费端在已安装XP2 TutorialLoader_Expansion2.lua211—220，已读正文核对。原包保留，不把此描述错误算给模型；两个端口各有真实消费端，Native触发仍需另测。

687完整stop/DONE/合法JSON，3781+2725=6506tokens、21844.1917ms。原稿整拒／0Native：空／额外key名单可过、输入名单未复制、安装后身份门漏核、漂移静默消失、最终失去归属仍KNOWN／新包装反而消失、失败Remove却true/restoredtrue、Add异常后的失败callback漏撤。隔离运行Owner独立11方法，unittest实际14failure／11error（含subTest，不冒称25方法），完整失败日志私存。

688完整SSE但length5000，8893tokens、33291.9891ms；正文未读／未解析／未采用／未重试／未拼接。Owner完整重写模块和独立fixture，首跑11/11通过0.099s，覆盖真事件样本、严格输入、身份变更、双读漂移／未知、上限不多读、两exact refs撤销、失败撤销不谎报／不重发、Add后附着失败清理、名单冻结与记录不别名；所有游戏写端口外计0。Restore先禁用自己的callback，再各撤一次；未知撤销结果不重复Remove。

两HTTP真实峰2／重叠21.844057秒，累计688逻辑／638完整47length3transport718HTTP30extra，Nov12同机用户维护成功缓存复用／OpenCode原生0／缓存成本净收益null。源133／119产品文件不变，旧1933全量是冻结历史，不冒重跑。0Steam上线上传，工坊82。下一步只安装Owner已验证模块，采集少量正常回合后精确撤销；通知、请求、实际队列与电力分列。
