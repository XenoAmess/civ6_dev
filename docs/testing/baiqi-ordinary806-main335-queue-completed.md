# 普通334→335：原排队军令实际完成

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-ordinary806-main335-queue-completed-2026-11-15.json)。[恢复主334](baiqi-ordinary142-main334-restored803.md)后，只发一次`UI.RequestAction(ActionTypes.ACTION_ENDTURN)`，无REASON／UserForced／军队重发或人工内政。

此前弓箭手1507337在54,35，3行动、pending=true／queue2719。END返回后的独立读回仍是334／active=false／已发送结束，此时实际到55,36、0行动、pending=false／queue=nil；随后独立335就绪监测通过，弓箭手留55,36且3行动、无队列。调用ACK、原队列实际执行和换回合分别有记录，闭合333既有TEST_PLAYER路线的这一个样本；不能追授旧ARMED建城恢复。

11城人口无减少：广州18→19、秀容16→17、沈阳12→13，其余不变。既有有界资产／food／vitals读取及三个OBSERVED粮食记录已采，0Observe／Persist／手动文职。原版正式保存335一次，2465660字节、SHA256 `8037c4e381a74f43465b233369e85e06c77c748c227c143674b280a3c5b7fc38`，稳定复读，尚未重载。0END335，自有游戏仍运行。

806先给真实未写的单END工具提出候选，完整stop／DONE／strictJSON，8757输入／1696输出，11445.8503ms、TTFT1449.0271ms。一次发令／独占意图／Lua核心部分采用；原稿把四个guard调用写在错误模块层、漏11城／3行动门、只捕Exception且回执校验在unknown记录范围外。Owner复用实际owner检查、修nested guards、补门、覆盖BaseException及回执校验，并核唯一完整RETURN。4次raw／修订双Lua编译、9个Lua守卫场景与8个Python守卫场景通过；原稿未进Native，0模型测试代码采用。异常／缺标记／中断均留意图并拒绝二次查询。

仅软件及该正常队列窄链通过。旧ARMED FOUND恢复FAIL及全40项继续，产品142119文件未改，Steam保持离线、0上传／截图。累计806逻辑／747完整／56length／3最终transport／836HTTP／30extra，OpenCode原生工具0，缓存及完整Owner成本／净节时未知。
