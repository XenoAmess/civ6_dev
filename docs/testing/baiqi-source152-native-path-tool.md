# Source152：原生路径调用的私有计时工具

2026-11-16，BF-202609141645。[证据与871—874审核](../research/baiqi-source152-native-path-tool871874-2026-11-16.json)。[原B_plan最长76ms失败](baiqi-source152-stageA-fail.md)保持；前次[移民处理58ms诊断](baiqi-source152-coarse-native88-89.md)未证明内部原因。本工作包只改变QA构建器与测试，产品119文件未改动，此切点尚未安装或实采。

871建议的测点部分采用。实际核对KnownExpansionSupport确实调用ExpansionStable／warning.Read，选址推荐API也真实存在；拒绝半径2只有13格的说法（实际19格）、RequestCivilian调用PathStep的错误关系，且没有SettlementSites也可能是记忆目标分支，不能推断发生held／稳定性失败。872与收窄后的873分别length3800／2800，完整SSE已存，整份拒绝、0执行、0片段采用或拼接。负责人接管工具范围，再将尚未编写的行为测试交874；874虽stop／合法JSON，隔离两方法都因缺Automation等上下文提前报错，且Lua53覆盖了Lua51导入、没有返回路径／真实换函数及nil尾值检查，整拒。负责人补真实行为测试。

新增显式 `--native-path-timing`，仅支持Source152与 `--include-pre-observer`。私有Controller在唯一PathStep原生调用点传入当前GetMoveToPathEx函数，再计算原参数；不缓存或替换UnitManager绑定。12词法测点外再加Native.GetMoveToPathEx，共14绑定、根子共享4096容量。关闭／退休不再记录，返回数量、false、nil、尾nil与同一错误对象保持；撤钩逐一核身份，不覆盖他人的替换或监听。还原的是计时别名和监听，私有直通调用点保留到进程退出；不再声称原源码是完整前缀，而是去私有改动后全文逐字节恢复。原生计时包含代理开销，不授B_plan或整体性能通过。

81项相关检查全过（15.849740s），新增14项含双Lua的10项行为检查；截断返回值和缓存旧Native绑定两个反例各在Lua5.1／5.3被真实断言拒绝。28组旧默认后缀逐字节一致，实际新包119项ZIP／源核对、97Lua5.1／5.3编译，仅Controller私有变化；包SHA256 `a6a6500ca7e81510f3ff33767d20d1185691803226d45d09b47128fb54411a6d`。容量测试最初误把描述字段当成闭包容量，保留两条失败原件后改成填满真实4096预算；负责人首个反例统计器也已按Lua断言属于unittest errors修正，没有掩盖这些失败。

871／872真实POST峰值2、重叠34.185501s；873／874为后续窄任务，不凑并发。871—873本地11月15日复用成功维护缓存；874已跨11月16日并真实检查OpenCode1.19.5／registry1.19.5，无需更新。累计874／803完整／68length／3最终传输／905HTTP／30extra、0在途，新OpenCode原生生成0，未知缓存与完整成本null。下一步保护210／91／90及历史档，冷装私有v3并细分路径、安全与扩张支撑成本；正式受控采样期间不运行HTTP或重型测试。
