# 142：TC-036实测性能通过

2026-11-15，BF-202609141645。源码142在已测GS单人环境通过[TC-036](baiqi-test-cases.md#tc-036)：[原85四项](baiqi-performance142-frozen760.md)、[MANY四项](baiqi-pressure-many-complete.md)和下表NO_SITE四项均满足冻结合同。只授这些精确夹具、设置与机器；完整40项功能、旧ARMED恢复FAIL及其他兼容范围继续验收。[结构化汇总与来源指纹](../research/baiqi-performance142-complete805-2026-11-15.json)。

| NO_SITE冻结项 | 实际结果 | 判定／来源 |
| --- | --- | --- |
| B_plan：各≥100纯十城，p95≤20／max≤50ms | Admin138，p95 9.000063／max20.999908ms；Controller155，p95 2.000093／max6.999969ms | PASS，[J完整分布](baiqi-pressure-nosite-stageA-J.md) |
| B_turn：五个10秒窗各≤1000ms | 142.000675／181.001425／171.998262／144.001722／164.999008ms；p50 164.999008，p95=max181.001425，>1000为0 | PASS，[K](baiqi-pressure-nosite-fullscript-K.md) |
| N_req：五完整回合各≤64 | 2／2／2／3／2；p50 2、p95=max3、>64为0，收尾7的4次另列 | PASS，[K](baiqi-pressure-nosite-fullscript-K.md) |
| B_delta：25段差值中位≤500ms且逐段比例中位≤10% | 中位11.999846ms／2.020176%，所有分母非0 | PASS，[五组原值](baiqi-pressure-nosite-pairN-group5.md) |

NO_SITE差值p95 431.999922／max651.999950ms，严格>500共1段；比例p95 81.818149%／max95.601177%，严格>10%共8段。正负值、尖峰和AI世界差异全保留；冻结门是总体中位数，不临时添加逐段、逐组或p95门，不宣称独占CPU或因果提速。

J规划保留296行，已验证窗前3行单列，0丢弃／无效时钟／资格错误。K覆盖实际33上下文，1180保留行／16845聚合零调用，198校准与396切换完整，4096总容量不变；全脚本固定窗去重累计与完整回合原生提交分开统计。精确92f43e9c…T1夹具完整可见1144格，1133水域／11城／0裸陆地；MANY的459a46e5…T6另有两次自然去重入池各12的资格证据，额外census不混入计时。

NO_SITE有10个有效独立冷进程、5组25段：每侧新鲜当前Steam后台离线证明、同EXE／CPU1—8／三设置指纹，预热≥60秒后正式重载同一92f副本。普通END1—5各一次、实际激活2—6，最后固定窗后停止、无END6；逐回合军队ID／类型有序输入匹配，无重复、UserForced或人工内政。各侧保存并核对自有进程结束。

第4组启用侧的公开文件`baiqi-pressure-nosite-pairN-4-enabled-2026-11-15.json`实际是新鲜R4：`pressurepair142r4-4-enabled`、PID24492／birth1794687370.927157，与原有效N4对照配对。原`pressurepair142n-4-enabled`因Owner803HTTP与正式测量重叠而整侧五段排除，原值全部另存；判废持久化晚于capture完成，不冒称预先落盘。实际共11冷侧，使用10侧；R4首段1333.999872ms也完整保留，没有择优重跑。[失效与互斥修复](baiqi-pressure-N4-invalid-admission804.md)。

805只审实际报告元数据，完整stop／DONE／JSON；数值复核作为笔记采用。其“CRITICAL来源歧义”被实际侧label／replacement字段消解，本汇总仍显式映射以便阅读；其把全40项／未测规则集当TC-036额外门的建议拒绝。历史阶段PARTIAL是当时快照，不改原件，也不阻碍本次按完整合同裁定。无新游戏采样或测试来自805，缓存与净节时未知。累计805逻辑／746完整／56length／3最终transport／835HTTP／30extra，OpenCode原生工具0。

产品119文件、97Lua和发行ZIP2457efba…不变；Steam无上线／上传，无截图。普通包及受保护主334的恢复与后续正常验收另记。
