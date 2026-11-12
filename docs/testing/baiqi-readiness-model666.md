# 290：区分领袖弹窗与等待中的只读监视器

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-readiness-model666-2026-11-12.json)。模组源／安装／运行仍129，此次只修改离线证据分类工具和被忽略的验收驱动。

旧监视器只读UI就绪状态，40次轮询会把晚期计算与领袖弹窗都归为失败。END288后继续独立等待确认289；END289后遇西班牙领袖，旧截图因超过60秒被拒绝、0输入，重新检查新鲜原图后点击原版“再见”一次，再独立确认290。两次都没有重发结束回合。287—289共3个普通END／21次测试玩家军事SKIP，0UserForced。已确认290的11城food／vitals通过，邢州仍11；核聚变自然完成，后台接控制论72／0/1100，广州自然完成核电站，但煤／油／铀均0，不能据建筑完成授持续供电通过。

666先行提供纯分类器及两个只读Lua producer，完整1834+1132=2966tokens、7054.4387ms、stop／DONE／合法JSON。原分类器在expected、UI turn、scene turn三个巨大整数位置均抛OverflowError；两个producer又都漏读实际GetLocalPlayer，无法满足自己的资格字段。Owner只采用分类逻辑并保护有限数判断，两个Lua按真实API补实际玩家编号；原limits字符串不作为网络实现采用。原候选未直接进入Native。

[纯分类器](../../tools/readiness_evidence.py)要求两个上下文的scope、实际玩家0、实际回合对齐，严格布尔。READY只表示这次读取已就绪，can_end_turn仅记录，不产生EndPermission；NPC_BLOCKED、WAIT_AI、TURN_PASSED和UNKNOWN均不合格。11项测试覆盖巨大整数、缺字段、坏类型、不同scope／回合、可见领袖场景、过期／越过目标及输入不变；全部通过。此前1858项产品全套仍是本次新增前的独立结果，没有将新11项算入旧全套。

私有监视驱动串行读取BaiqiExecutor和LeaderScene，每次查询前后核PID／birth／exe／endpoint，每个真实context均有两seed／玩家／领袖／首都资格assert；只有两个实际turn一致才判定。保留原严格帧解析，最多120对、每对开始前检查90秒截止，单次Native查询仍受原超时限制；并非硬保证整个进程90秒退出。领袖可见立即返回NPC_BLOCKED、非零退出，不自动点击，不重试任何动作。初次实机两个实际290／玩家0／同scope读回READY。新监视器的NPC分支有软件验证，尚待后续真实弹窗见证。

为继续现有科技链，仅将129私有驱动上限290扩至320，保留旧副本并逐一AST检查；不增加产品权限。HTTP累计666／620完整／43length／3transport／696HTTP／30extra，OpenCode同机同用户维护缓存复用、原生生成0，缓存／成本／净收益未知为null。后续控制论／预测系统、海上施工、持续供电、粮食历史矩阵继续，Steam保持离线、工坊82。
