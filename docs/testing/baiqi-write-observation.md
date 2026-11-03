# 执行器静态写入代理：安装与恢复

[安装器](../../tools/lua/diagnostic_write_install.lua)复用[既有计数器](../../tools/lua/diagnostic_queries.lua)，接收明确的上下文绑定表、计数器工厂和记账桶回调。它构造全部代理后才替换三个绑定：UnitManager的RequestOperation／RequestCommand、CityManager的RequestOperation、UI的RequestPlayerOperation，共四类调用。Restore只还原仍由自己持有的代理，保留别人的后续替换。安装和恢复均不调用原生操作或记账回调。

目标消费者是BaiqiExecutor：Controller、Admin和Recover均在此上下文读取这些静态API。记账桶不能以是否存在规划根回调为前提，否则仍会漏掉Recover。调用次数、接受和实际效果分别记录；资格查询、其他上下文玩家输入及核心效果不能混为同一提交，转发链也不能重复计数。

236的完整Lua主体原样采用，237测试原稿2个Lua错误、未采用。负责人11项实际模块软件检查通过，涵盖四类透传、参数与nil返回、原错误对象、回调失败后继续调用、三阶段构造失败不部分安装、外部替换保护及虚拟上下文绑定。[逐案与原始失败](../research/baiqi-p6-writeinstall236237-evidence-2026-11-03.json)。原稿首轮收集器因缩进发现0方法，不能算通过；修正后才执行明确的2方法。正常60已有完整603项检查，这11项独立工具检查不构成完整614项重跑。

60进程2376的只读查询已确认四类API的表／函数形状，同时发现_G为nil。未来安装由命名变量的显式上下文访问绑定完成，不依赖_G、getfenv或debug。软件已新增虚拟绑定的安装／恢复与构造失败消费者检查。BaiqiExecutor中的临时私有标记在WorldInput不可见，随后清除；这是一处实际作用域观察，不是所有上下文或线程隔离证明。安装器本身尚未接入游戏。

这是静态API子集机制：政体／政策等对象方法、核心层效果及属性写入、其他界面上下文、全模块耗时和匹配对照仍缺实测。不得把本工具、一次形状查询或静态清单当成N_req／TC-036通过。正常60最新调度p95约24ms超20ms，最大约42ms在50ms内，性能项仍FAIL。

交付说明：581e0d0的提交标题误沿用了59版文字，该提交的实际文件、版本及数据均为60版q16、p95失败。以[60版实机证据](../research/baiqi-p6-performance-native60-evidence-2026-11-03.json)为准；本次正常后续提交补充说明，已发布历史保持线性。

## 2026-11-03：静态写入子集实际接入，性能仍失败

60普通包同进程另行预热198.566秒、重载原始十城85后推进至90。242根回调／234纯十城：Controller143次p95约31ms、最大41ms，Admin91次p95约6ms、最大12ms，B_plan仍FAIL。25次原生寻路中23次纯十城，最大31ms；120次无该寻路调用的Controller回调仍p95约30ms，不能把超限全归因于寻路。四类静态API共80次调用，含精确标识的5次规划根外恢复请求；86—89只覆盖该UI子集的活动回合，90尚未结束，全模块N_req仍未知。两根入口与三张静态API绑定、原生寻路函数均已恢复，状态／事件已清理，0丢弃／计时／运行错误。UI／Core11城匹配、队列均非空、9条国内商路；实际519090字节存档哈希留证，未重载。[实机证据](../research/baiqi-p6-performance-native60-query-write-evidence-2026-11-03.json)。这补充此前“安装器尚未接入”的历史记录，不把当时的软件见证追认为实机结果。


## 2026-11-04：政体／政策对象方法适配器

新增[外部适配器](../../tools/lua/diagnostic_culture_write_install.lua)，复用既有NewQueryCounter，只包装选定玩家的GetCulture及RequestChangeGovernment／SetGovernmentChangeConsidered／RequestPolicyChanges。对象方法始终绑定真实原生接收者，保留getter和写入的参数、尾nil及返回值；其他玩家原样通过。缓存最多16个玩家／128个文化对象，缺接口／包装失败／溢出保留原行为并标覆盖未知，不能因此判预算通过。

Restore只替换自己拥有的Players绑定，外来替换保留；已被调用者持有的旧facade随后直通原生并停止计数，避免只让getBucket返回nil却继续累计totalCalls。9项必要行为检查0.016秒通过，真实67／90回合隔离环境只读返回原生政体4且正确恢复，未调用任何原生政体／政策写入。这补齐可接入的工具，不是完整请求账本已实机通过。[原稿拒绝、独立实现与实测边界](../research/baiqi-p6-culture-write-adapter293-evidence-2026-11-04.json)。


## 2026-11-04：只包装本模组订阅的事件入口

新增[事件适配器](../../tools/lua/diagnostic_event_facade.lua)，按实际原生事件和原始回调保留稳定包装身份，兼容重复Add、捕获Remove和考古收据模块的重载／Shutdown。默认最多128个事件、512个回调；溢出或包装失败直通原生并标覆盖未知，不改变游戏行为。未知字段、调用、只读错误和尾nil均透传。

9项行为检查通过；正常67／90回合在UI和Core各实际添加并移除一次临时空回调，添加／移除身份相同、处理器执行0次、原生Add／Remove未改。适配器按上下文存续，不能中途注销重订；原版脚本绕过适配器Remove是明确边界，需要构建器另行处理命名绑定。此工具尚未组成完整诊断包。[模型原稿拒绝、负责人实现及双上下文实证](../research/baiqi-p6-event-facade296-evidence-2026-11-04.json)。
