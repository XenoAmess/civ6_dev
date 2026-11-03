# 全模组观测入口：67版接入边界

这是诊断包的接入清单，不是完整运行覆盖证明。[冻结预算](baiqi-performance-protocol.md)中的B_turn、全模组N_req和配对B_delta仍待验收。正常67版没有加入玩家可操作的暂停或接管开关。

| 范围 | 真实入口与身份要求 | 接入边界 |
| --- | --- | --- |
| 执行器 | BaiqiExecutor的Update、OnViewReady、Activate、OnPlayback及Shutdown | Recover不依赖规划根，也必须计入；ContextPtr回调与Events订阅均覆盖 |
| Core事件 | BaiqiGameplay的三类GameEvents；伟人、创作、自然学家、宗教的Protected闭包 | 计时必须包装实际注册对象，不能在Add之后另改同名变量 |
| Core考古／购买收据 | ArchaeologyReceiptEvents与NaturalistPurchaseIntentGameplay捕获的Add／Remove | 包装身份稳定，Shutdown移除同一对象；不能注销再注册改变顺序 |
| Core公开桥 | GreatPersonIntent、CreativeIntent、ReligiousIntent、NaturalistIntent、NaturalistPurchase、Archaeology六个ExposedMembers命名空间 | 记录真实方法调用与下游事件的重叠；校验桥身份的语句不是新增导出 |
| UI命名覆盖 | ChooseArtifact.OnOpen、CityPanel.ViewMain、CivicsChooser.OnChooseCivic、DedicationPopup.OnConfirm、DiplomacyActionView.ShowLeader、LeaderScene.GenerateLayers等 | 多数是变量赋值匿名函数，不能只搜索行首function声明；保留原版捕获及Add／Remove配对 |
| UI生成闭包 | UIGuard的对象／静态代理、UILoader.ReadOnly、Actions.WrapMove及弹窗确认回调 | 这些函数也会被原版调用；只包装本项目定义，不重写include加载的原版脚本 |
| UI事件替换 | GreatWorkShowcase、HistoricMoments、NaturalWonderPopup、NotificationPanel | 分清原版函数引用与本项目新增函数，保持Native移除和重订身份 |

UIGuard只替换导入它的UI上下文绑定。执行器明确不导入它；不能把它说成跨上下文、更不能说成Core全局代理。Actions实际位于Lua/BaiqiActions.lua；UnitPanel和WorldInput都调用其WrapMove。

只在订阅处使用事件facade，无法覆盖公开桥、原版回调调用的命名覆盖及动态生成代理。诊断构建器将研究在本项目函数定义处包装，避免原版Remove绕过翻译；源码词法变换必须正确处理字符串、注释、嵌套函数、局部递归及冒号接收者，编译与真实消费者检查后才可安装。此方案仍是待验证实现，不能把清单、候选或普通67的旧实证记为诊断包通过。

局部根的包含式墙钟会覆盖其中的原生／原版调用，跨UI与Core还会重叠。它可以提供保守包络，不能直接称为本项目独占CPU时间，也不能将嵌套样本相加。时钟偏移需要实际括号采样，观测精度和稳定性未知时保留未知项。

本地模型294／295只部分采用入口家族分析。294返回24条却自称22条，且将捕获别名的订阅写成直接Add、把桥校验混作导出；295的主要UI名称经负责人逐文件核实确实存在，拒绝的是Actions路径、跨Core代理的错误解释和未证明的泄漏结论。[逐项审阅与源文件摘要](../research/baiqi-p6-stageb-entry-review294295-evidence-2026-11-04.json)。


## 函数定义观测组件已交付，尚未安装

[源码变换器](../../tools/lua_function_instrument.py)只改本项目函数定义；本地递归、命名／匿名覆盖、冒号self及原版Add／Remove可见的绑定均在定义时完成包装。[外层入口门](../../tools/lua/diagnostic_owned_roots.lua)复用既有计时器，关闭记录或处于同上下文嵌套时直接透传，错误后恢复入口状态。没有重写原版include或新增游戏控制开关。

9项变换检查和6项入口检查通过；全部当前Lua原稿／变换稿经实际Lua53编译，另在启用真实计时门的变换稿上运行原有6个消费者模块，83项通过，实际458次加载涉及12份源码。这些是软件见证，独立诊断包及实机预算仍待完成。[模型298截断弃用、299拒绝及负责人实现](../research/baiqi-p6-owned-definition298299-evidence-2026-11-04.json)。


## 叶子写入观测组件已交付，尚未安装

[写入引用变换器](../../tools/lua_write_instrument.py)覆盖实际静态API引用及六类对象写方法，包含pcall／别名传递；对象调用保持先取方法再求实参、真实self不变。[叶子观测器](../../tools/lua/diagnostic_write_leaves.lua)复用既有计数器，关闭记录直接透传，缓存最多512项，缺方法、元数据错误或溢出标未知。Guard存在时只计其Native转发；执行器没有Guard，直接计原生调用。

63份源码中得到58个引用／调用位置，包含资格检查，不能当实际请求数。新增5项变换、6项叶子检查通过；组合函数／写入变换后原有83项消费者再次通过，12份源码实际加载458次。300仅采用方法类别，301／302代码拒绝，由负责人独立实现。[准确位置、原稿反例及软件边界](../research/baiqi-p6-write-leaves300302-evidence-2026-11-04.json)。


## q19独立诊断包已构建，等待完整包实机

[构建器](../../tools/build_observed_mod.py)从正常67复制85份受管文件，只改63份本项目Lua：507个函数定义、63个完整顶层块与58个写入位置。顶层块保留提前return／变参，覆盖后续延迟加载的初始化；原版include不重写。录制开关只存在于独立诊断包的外部观测注册表，不控制AI或游戏权限。

[上下文组件](../../tools/lua/diagnostic_context.lua)复用既有计时门与计数器，按真实原生回合记账，在本项目事件注册前添加观测锚点，按同一身份移除。注册表最多80项、回合桶与锚点各128，缺接口／异常／溢出均留未知标记；保留外来命名空间与替换。8项上下文和4项组装检查通过，最终组装消费者83项通过；最终63份Lua已全部编译。

完整组件还在正常67的UI／Core各执行一次只读生命周期见证：真实临时Add／Remove、一次回合读取计时、Reset及命名空间清理均完成；0原生游戏写入／0事件触发。模型303代码因递归溢出、缺失注册表及错误时钟／profile绑定全拒绝。完整包的预算与运行覆盖仍待实际安装。[最终包哈希、软件检查与双上下文回执](../research/baiqi-p6-diagnostic-assembly303-evidence-2026-11-04.json)。
