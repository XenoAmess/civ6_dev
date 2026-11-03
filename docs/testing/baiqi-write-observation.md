# 执行器静态写入代理：安装与恢复

[安装器](../../tools/lua/diagnostic_write_install.lua)复用[既有计数器](../../tools/lua/diagnostic_queries.lua)，接收明确的上下文绑定表、计数器工厂和记账桶回调。它构造全部代理后才替换三个绑定：UnitManager的RequestOperation／RequestCommand、CityManager的RequestOperation、UI的RequestPlayerOperation，共四类调用。Restore只还原仍由自己持有的代理，保留别人的后续替换。安装和恢复均不调用原生操作或记账回调。

目标消费者是BaiqiExecutor：Controller、Admin和Recover均在此上下文读取这些静态API。记账桶不能以是否存在规划根回调为前提，否则仍会漏掉Recover。调用次数、接受和实际效果分别记录；资格查询、其他上下文玩家输入及核心效果不能混为同一提交，转发链也不能重复计数。

236的完整Lua主体原样采用，237测试原稿2个Lua错误、未采用。负责人11项实际模块软件检查通过，涵盖四类透传、参数与nil返回、原错误对象、回调失败后继续调用、三阶段构造失败不部分安装、外部替换保护及虚拟上下文绑定。[逐案与原始失败](../research/baiqi-p6-writeinstall236237-evidence-2026-11-03.json)。原稿首轮收集器因缩进发现0方法，不能算通过；修正后才执行明确的2方法。正常60已有完整603项检查，这11项独立工具检查不构成完整614项重跑。

60进程2376的只读查询已确认四类API的表／函数形状，同时发现_G为nil。未来安装由命名变量的显式上下文访问绑定完成，不依赖_G、getfenv或debug。软件已新增虚拟绑定的安装／恢复与构造失败消费者检查。BaiqiExecutor中的临时私有标记在WorldInput不可见，随后清除；这是一处实际作用域观察，不是所有上下文或线程隔离证明。安装器本身尚未接入游戏。

这是静态API子集机制：政体／政策等对象方法、核心层效果及属性写入、其他界面上下文、全模块耗时和匹配对照仍缺实测。不得把本工具、一次形状查询或静态清单当成N_req／TC-036通过。正常60最新调度p95约24ms超20ms，最大约42ms在50ms内，性能项仍FAIL。

交付说明：581e0d0的提交标题误沿用了59版文字，该提交的实际文件、版本及数据均为60版q16、p95失败。以[60版实机证据](../research/baiqi-p6-performance-native60-evidence-2026-11-03.json)为准；本次正常后续提交补充说明，已发布历史保持线性。
