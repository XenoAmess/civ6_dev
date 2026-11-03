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
