# 302：工坊修复再次受阻与674/675

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-blocked-workshop302-model674675-2026-11-12.json)。正式130、实际302，0END302；[300→301项目修复及首座风电](baiqi-project-repair-first-offshore-native130.md)保持原结论，未将后续再次受损说成第一次未修好。

END301先返回但仍在同回合；独立确认世界／城市资产相同，两建造者与13原路线商人移动完成、52单位队列均成功返回单nil、剩余军SKIP均原生false、NPC隐藏后，发送一个新普通结束才到实际302 READY。因此301计2正常END、7军SKIP、0UserForced。负责人首次比较只预期两单位变化，遗漏13商人，断言在输入前拦住；依据实际行纠正，没有把商人移动算后台军令。

302人口守卫NO_LOSS，秀容仍15、库存77.640625／净+9。工业区301已完好、302又pillaged；原因尚无逐城因果。旧工坊修复72/97、HasBuilding=true且IsPillaged=true，唯一typed建筑18队列hash0，包含检查true／排除false；前置工业区9受损90/121，两个检查true，原生PREPEND修复资格true，0新修复请求。现有旧建筑分支只允许尚未拥有的建筑，须补既有修复项受阻的窄类型，不破坏旧建筑或130项目。夹具定义了CityProductionDirectives.CONSTRUCT，并非本次实机枚举见证；BUILDING字段实机nil，负责人首次假定该字段的只读断言已纠正，不归模型错误。

首座风电2132仍完好；完整227购买可见自有格盘点现有4座，新增1901、2133、2134，均真实海上风电且未pillaged。秀容freePower4／required3、fullyPowered true／ByActiveProject false，是本回合独立免费供足快照；上海2/5仍靠项目，沈阳2/2但ByActiveProject true，不扩大为全域长期供电通过。旧项目投入仍143/157。

674/675两真实独立HTTP各一次完整stop/DONE/合法JSON，峰2、重叠24.20032秒。674为23486+3049=26535tokens／27495.7875ms：完整替换函数删掉旧未拥有建筑分支，旧13方法出现17断言失败、0异常，整稿拒绝；QueueReady／过滤／读回窄段仅候选，尚未采用。675为23538+2236=25774tokens／24277.3412ms：15方法4断言失败0异常；明确夹具两种CanProduce均true，若干负例不运行控制器，未拥有测试仅pass，还有回调自身的递归fallback，整拒、0rawNative。负责人审阅脚本原先误预期setup异常已纠正；queues/current/cities在实际父夹具存在，不将这个误判归模型。一次纯Lua递归fallback试读未结束，已中断该软件进程；没有完成的fallback运行结果，递归缺陷按源码记录，未触碰游戏。

302正式保存2327250字节，SHA-256 91ae21103401db2552fb3f03fad4ff2f48e27de7fa5d182b9ded92cad4981b77；已建新130停止标记，旧129停止标记与两次人口损失保留。源码131尚未写／编测，下一步负责人保旧分支、窄采用审过的段并编写实际工坊回归，再同302档冷验。累计675逻辑／629完整／43length／3transport／705HTTP／30extra；当日维护成功缓存复用，OpenCode原生0，未知成本null，Steam离线／工坊82。
