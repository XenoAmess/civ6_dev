# 642／643：Core真实维护费与既有水电站

2026-11-12，BF-202609141645；运行仍123，未修改游戏源码。[逐项证据](../research/baiqi-p6-model642643-core-upkeep-hydro260-2026-11-12.json)，[已完成的付费／排水／市场修复258](baiqi-paid-barriers-native258-123.md)。

642原稿使用Lua5.1不支持的goto，编译即拒；且把pcall布尔当数据，缺归属／坐标／最后回合，凭空用E.Treasury。Owner5合同后，Core259读21阶段0API错误：两己方已建屏障Has=true/Pillaged=false，GetBuildingMaintenance(Index113)各为7；同名UI接口此前均回0，静态数据库Maintenance为1。这确认了上下文差异，123静态预算不能当有效动态维护预算通过。

未建对照首都回0；追加首都／北京／沈阳三未建城UI完整与排除CanProduce均false，Core对应CanProduce六次明确Not Implemented，独立保留异常。因此尚无“可合法新建但未建屏障”的未来维护费资格，0不能当未来免费，已建7也不能覆盖其他城未来成本。Core第一方法清单在Buildings部分输出后，未保护的CityGold组件读取报错；从原收据恢复部分输出，未重放。新独立守卫确认getmetatable可用、debug/rawget=nil，CityGold仍不可用，未调用新未知原生方法。

643先给水电只读候选，原稿竟将pcall替换成直接执行，原生读错误逃逸；正常数字区域类型又与DISTRICT_DAM字符串比较，未读即unknown。隔离反例成立，原代码拒用。Owner6合同后，首都65536@55,34、大坝53,34已完成未损；水电站114/hash-743431162早已拥有且未损，电力科技已拥有。免费电6、临时电0、需求8，当前fullyPowered与ByActiveProject皆true。两个生产模式、BUILD资格、两个购买模式全false；报价745不能授权重复购买。

初读21阶段中规则表扫描有1负责人上限错误：ModifierArguments4096不足，不能解读成不存在原版水电规则。独立32768有界跟进确认真实链接HYDROELECTRIC_DAM_FREE_POWER、MODIFIER_SINGLE_CITY_ADJUST_FREE_POWER、Amount6、SourceType FREE_POWER_SOURCE_WATER、无SubjectRequirementSetId。没有新建水电或新授供电效果；“普通评分导致首都水电一直未建”的假设被真实已有状态推翻，继续查其他持久电源。

258→260又经两普通显式END、14军队SKIP；259加拿大再见一次，世界议会特殊议程5次原版实体点击。一票反对宗教紧急状况、花费0，实际其他票15赞成8反对通过，不能把自己选择写成最终结果。原版提交代码含END请求，未设置全局计数，内部实际数未知，不重放已发END。此前“事件7”仅指GetClimateChangeForLastSeaLevelEvent观测值7，未另行资格为阶段名或事件序号。260人口无下降、11城粮食非负，上海海港207/220，工业区修复尚未授通过。

642单HTTP200/stop/DONE/VALID，8008+676=8684tokens、5890.0686ms；643同样完整，8589+827=9416、7246.4125ms。累计643／599完整／41length／3transport／673HTTP／30extra。Nov12维护1.19.5缓存复用，OpenCode原生0，未知成本null。所有诊断0游戏动作／订阅／全局替换，无Steam上线上传。全功能验收未完成。
