# 外部原生查询计数

tools/lua/diagnostic_queries.lua 返回 NewQueryCounter(original, names, prefix, getBucket)，生成继承原命名空间的代理及统计对象。它面向以点号调用的静态API表，不包装或复制返回的游戏对象，也不注册回调或提交游戏动作。

选中函数每次调用时取一次当前计数桶；桶为空表示观察范围外。有效桶按前缀和函数名累加，错误的桶、不可递增数值、getter或桶元方法异常记callbackErrors，原函数仍被调用一次并保留全部参数、返回值和错误。totalCalls是代理入口次数，包含范围外调用；不能直接当作模组游戏指令数。

本地模型187的循环、导出和直接转发结构部分采用。负责人补有限数／精确递增及整个计数访问的保护。原候选在9项基础消费者中有2项断言／异常错误；最终负责人版本9项通过，另包含大数不能精确递增的输入。两次测试的输入并非逐字相同，不把后加反例追认成原候选已跑。

原生47版UI Lua的虚拟命名空间检查通过：两个循环闭包绑定正确，保留对象引用与4个含nil／false的返回值；Infinity与桶写入异常只影响诊断，5次原调用全部发生。该检查尚未代理真实Map／Units／UnitManager，也没有新的游戏性能样本。

验证命令：

    python -m unittest discover -s tests -p test_diagnostic_queries.py -v

[证据及记录的成本片段](../research/baiqi-p6-query-counter-evidence-2026-11-02.json)保留实际采用边界。下一轮须修正激活窗口，验证真实API表的代理和恢复，再用于定位[十城超限](../research/baiqi-p6-performance-first-window47-evidence-2026-11-02.json)；计数本身不证明热点或性能通过。
