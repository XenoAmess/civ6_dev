# 294上海人口损失与668跨回合守卫

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-shanghai294-population-model668-2026-11-12.json)。源／安装／运行129；这是新人口损失样本及验收工具修正，尚未修复或解释游戏损失。

293→294上海655369@59,28从15变14，295仍14。UI库存42.93359375→46.76171875→50.86328125、净粮17→15→15，均无当前饥饿倒计时；端点粮食正常不能证明中间没有损失。原sample只验当前food/vitals，没有跨回合人口对比，输出complete后自动runner已再发一次END294才被Owner发现，不能称294无人口损失。292—294共3个普通END／21军SKIP／0UserForced；END294后的使者视图守卫在实际状态变化后断言失败，0视图或第二次END输入。独立确认295后未发END295。

正式295现场2298790字节，SHA-256 3157b2a0bd40296d34db812249693a639a62549c3f4ea41a2ada4a9f2df3432f。原292—295四份自动存档已私有逐字节复制保全，未改内容，接续293独立复现。核聚变／曼哈顿计划自然完成、当前控制论进展等窄证据保留，不据此关闭粮食完整验收。

Owner最初历史筛选要求起点和当前位置都已揭示，严于原版气候页，因而把有关风暴过滤掉。补读完整消费者ClimateScreen.lua 622—640后改按原版Global或CurrentLocation已揭示规则：292龙卷风至295累计PopLost1、TilesDamaged4、UnitsLost0，当前位置2055靠近上海，起点1914。损失是整场总数，仍没有上海逐城伤亡回执，当前本城GetCurrentTurnEventAtPlot为nil也不能否定过去受灾。这里只保留天气线索，不认定因果。

668先提供跨回合人口纯比较候选，完整3524+1401=4925tokens／8558.3264ms／stop／DONE／合法JSON。before/after四个cityID/x/y/population巨大整数共8处OverflowError见证；Owner只加保护有限数helper后窄采用，其余全集合／身份／损失分类方向保留，0rawNative。[纯工具](../../tools/population_interval_evidence.py)和[10项新测试](../../tests/test_population_interval_evidence.py)通过；原始合格11城快照重放明确293→294 POPULATION_LOSS、294→295 NO_LOSS，因果固定null。qualified true只代表损失证据有效，不可作为下一END许可。

私有sample接入后，未来296起只接受同scope、恰一回合、完整集合且status NO_LOSS；新损失或UNKNOWN先保存结果、创建原驱动stop标记并非零退出，不能输出完成后继续END。295显式基线仍携带已知293→294未归因损失，未清除旧FAIL，也不授权现在END295。产品文件不变，10针对测试不冒充重跑旧1858项产品全套。

补记操作纠正：特殊291提交页面可能自动收起，随后点击右上关闭位置打开了原版菜单；293新图确认后点“返回游戏”一次，再在议会结果页点“返回游戏”一次并独立READY。此前667把该坐标点击记为成功原版关闭的说法已修正；PID／几何／新鲜截图守卫不能原子保证动态页面在点击前仍存在。

累计668／622完整／43length／3transport／698HTTP／30extra，同机同用户每日维护缓存复用、OpenCode原生0，未知成本null。Steam离线／工坊82；继续复现归因和海上科技／施工／持续供电，旧213／222与完整矩阵保持开放。
