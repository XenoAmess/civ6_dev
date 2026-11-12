# 283：煤到货后十城仍靠项目，供电路线中断

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-native128-coal-power-gap283-model663664-2026-11-12.json)，[128首次前置选择](baiqi-power-path-native278-279-128.md)。仍源／安装／运行128，实际283已保存，未发送END283。

279→283四个普通END、28次测试玩家军队SKIP、0UserForced／新NPC点击，每回合food／vitals通过；核裂变进度280270.75390625→281432.82421875→282600.39453125，283自然完成。但煤由282的0增至2，原emptyFuel门不再成立，后台普通研究选择合成材料57／0/664，而非海上路线下一项。五滑雪场保持；原版队列与建设没有人工补做。

Owner只读实测三燃料24个getter、11城电力、33项实际电厂HasBuilding均取得资格，0未知。煤库存2／cap25／reserved0、accumulation3／imports0／bonus0／unitDemand0／powerDemand1。四座煤电厂和北京一座燃油厂实际存在；邢州free6／temporary3／required9、fullytrue／byProjectfalse，其余10城均fullytrue／byProjecttrue。不能把当前净积累或一城供电当作全部城市已持续供电，也没有预测项目结束后总燃耗。煤的具体来源未归因。

原版Expansion2_Buildings.xml:7—8、14—15、18—24给出真实煤／油／核电厂类型为BUILDING_COAL_POWER_PLANT／BUILDING_FOSSIL_FUEL_POWER_PLANT／BUILDING_POWER_PLANT。663完整13575tokens／14688.1073ms却含continue，Lua51编译失败；还把bool电力结果送numeric validator、错误city:HasBuilding、接受负资源、257前缀break后仍KNOWN、缺最后重核，油／核别名也不实。整份拒用，Owner重写7组后上述实际只读。

664完整22047tokens／9749.2921ms。Admin hunk隔离见证3错误：正无穷燃料资格、free==required仍因projecttrue授需求、fullyfalse却忽略project未知；该部分拒用。Planner hunk按当前真实Policy.Number在完整原模块内验证12种已知／未知／负值／非有限／powered场景通过，批准后续窄采用，当前尚未改产品。Owner首次把hunk直接在模块外执行，缺词法local number而报错；改为替换完整原模块后才通过，非模型hunk行为失败。

给模型的提示曾把建造者6946852的formation列1误读成次数下降；完整278—283快照和日志纠正为charges一直2，且该实例日志0个新BUILD_IMPROVEMENT。此错误线索未用于归因，不能据此称煤矿新建。两HTTP实际峰值2、重叠9.748355秒，原件保留。

下一包129将把已知非负燃料与实际城市电力状态结合：仍缺电或只由项目供电的free<required城市继续可落地新能源路径，已有真实非project供电的城市不抢研究；实际未供满城市可用临时项目，正储量不再一刀切禁用。保留未知拒绝、原队列、正研究进度、洪灾和pending-before-writer，不新增journal或手动入口。

283档2264453字节，SHA-256 f578259263668a9b4edbff86e3823dabec16702edec61d1c85a56fedf6922d13。累计664／618完整／43length／3transport／694HTTP／30extra，维护缓存复用、OpenCode原生0，未知缓存／成本／净收益null；Steam离线、工坊82。持续供电与粮食／旧完整矩阵仍开放，继续修复。
