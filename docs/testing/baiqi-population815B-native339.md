# 815B人口复现：沙尘暴累计新增3，逐城原因仍未闭合

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-population815B-native339-2026-11-15.json)。受保护338自动档备份另克隆、正式载入及当前日志资格后Continue各一次，原339与已完成自动修复的342档保留。仅一次普通END338、实际339READY；0END339／军令／人工内政／UserForced。

两城再次327684长沙16→15、393221广州19→18。UI事件仍标338、Core已标339，粮食库存及缺失字段分别保留。两上下文各28seen／25ignored／3retained、0callback errors／drops；保留两人口和一个火山9的Occurred事件，未观察到Started记录，不推广为该事件API不存在。

新增证据是338沙尘暴14历史累计：基线PopLost=0／TilesDamaged=7，两人口回调时已为3／21，Start338／End341不变。两次回调都已读到总损失3，不能把累计变化分配给具体城市，也不能用最新global事件9替代历史14。原先0→3累计增量现在有前后证据；逐城因果仍开。

UI分别取得两城7／6个区域，基线与对应人口回调共26次at-plot查询均ABSENT_THIS_QUERY；长沙51,29社区基线就已损坏。缺少当前查询结果不排除此前灾害影响。Core有GetDistricts但集合Members=nil，明确PARTIAL且保留已知历史，未补区域或借UI数据。UI四个上下文读数KNOWN／0contextErrors；Core四个PARTIAL／contextErrors4，与callback errors0分列。

第一版实机在END之前就发现合同错误并撤下两处监听：Owner把GetEventsForTurn当密集数组，实际UI和Core均返回单条14字段记录，未来339为nil；Core区域Members缺失亦未在原合同覆盖。这些是Owner错误，不归模型。新的B版本按单记录、64键上限和future ABSENT处理，Core缺区域仍继续历史；新增15组件＋24观察器场景各在Lua5.1／5.3通过，再实机安装。新旧两版每处三个自有订阅都已精确撤，cleanupKnown/restored=true、cleanupErrors0；全部自己的QA句柄及已结束动作标记已清。

Owner还纠正END封装的旧Core2回执名称；该前置断言在任何意图或Native调用前失败，改为实际Core后才发出唯一END338。815最初给模型的快照源码只到包装层，实际区域API以文字合同给出；底层真实生产者后来由Owner核读，不能追认请求已包含完整消费者。模型原稿的双Lua语法错误等独立问题和0采用保持。

复现339另存2475573字节，SHA256 `a98ade4c167b97ef04f0ecafd0f048fc52264bf1e4b18b6fe6abfb9591713480`，未重载。清理并保存后另取完整自有快照，只作为补充，不称原子存档全等。产品142／119文件不变。累计815／756完整／56length／3最终transport／845HTTP／30extra，0在途／新增OpenCode原生工具，未知成本null。

Steam持续离线、0上线／上传／截图。不会仅为相同结果重复本实验；保留逐城未知，继续其他可执行验收。TC-036限定实测PASS、旧ARMED恢复FAIL及完整40项状态保持。
