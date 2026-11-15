# 152全脚本QA的静态writer身份修复

2026-11-16，机器BF-202609141645，Asia/Shanghai。接续[90档冷读](baiqi-source152-armed90-diagnosis878879.md)。产品仍为普通152；本工作包只修QA工具，原76ms B_plan FAIL保持，未授B_turn／N_req或建城恢复通过。

实际旧包Controller将writer捕获和Bound比较分别改为源码877、901两个不同label的P6WriteRef。Executor没有BaiqiUIGuard；旧Leaves.Static按label缓存，因而同一原生函数得到两个不同wrapper，Bound恒不相等。这个实际私有源码缺陷能在软件中直接复现。不能据此声称恢复了已中止实例的全部内部状态或排除其他问题。

修复[缓存查找](../../tools/lua/diagnostic_write_leaves.lua)：同上下文内Static按原函数身份复用wrapper，调用归第一次读取的label。Method仍按原label／receiver／fn／method隔离。maxEntries、溢出退回、nil／false／异常转发和原生调用次数保持。与未插桩的外部raw函数比较仍不保身份；这不是任意Lua程序的透明性证明。受影响捕获必须核实际消费者及丢弃／包装错误，不给旧包追授通过。

[新增4项检查](../../tests/test_observed_writer_identity.py)直接使用实际transform及真实write-leaf实现，替代旧测试中P6WriteRef直接返回原函数的无效身份见证。修复前：46个live许可场景中28个正向场景失败，静态身份断言失败；修复后46场景全过，并在两个引擎启用实际计数验证FOUND恰好1次、dropped=0。Method标签隔离亦过。

共30项相关检查通过（含以上46个双Lua场景）：21项首次相关检查过，8项bounded观察和1项实际启用计数另过。Owner首次未将tests加入导入路径，bounded模块导入失败；新增启用计数的Lua5.3夹具缺unpack别名亦失败。只修测试入口后分别验证，不归产品／模型错误，不冒称重跑完整产品测试。

模型880完整stop／DONE／严格JSON；采用Static按fn复用的窄思路，原稿同时移除Method的label隔离，违反任务合同，未原样执行。Owner保留Method原条件并完成红绿验证。每日维护仍复用本机Nov16 OpenCode1.19.5缓存；无新增OpenCode原生生成。累计880逻辑／809完整／68length／3最终传输／911HTTP尝试／30额外，0在途；本轮POST峰1，未知缓存、服务并发、Owner完整成本和净省时null。

新全脚本准备包：`c23bc80a2c3cb3cc4948755ba696ab0b202d75b2374afb58a163149ddaa6e971`，97Lua双编译、119文件、33上下文配额合计4096，AggregateZero=true。仍需以新label／新实例实采，不能续写quota152、重放其END或修改冻结预算。878—879私有结果记录器已发布但未安装；现发现实际插桩身份缺陷，下一步先验证修复后的全脚本包，无需为了使用新工具重复原85跑测。

LOCAL_ONLY原件：`.local-model/resume-20261116/writer-identity-original-red.log`、`writer-identity-fixed-related.log`、`writer-identity-remaining.log`、`writer-identity-enabled-final.log`、`observed152-identity-fixed/`及`.local-model/model880-static-writer-identity/`。原普通安装、旧QA包、中止90档和主210保持。
