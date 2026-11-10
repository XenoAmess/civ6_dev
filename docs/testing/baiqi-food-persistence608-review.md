# 救粮未知请求的持久化：608候选审阅

2026-11-11，BF-202609141645，源码／安装／运行111、210十城，Steam离线。110救粮及111界面冷验分别通过其限定窗口，但救粮Runner只有当前UI上下文的local pending，读档后可能丢失。这里开始补持久化，尚未实现或授验。

先对当前BaiqiGameplay做只读资格：玩家GetProperty／SetProperty为function（未写属性）；城市Growth.GetFoodSurplus实际读0。Core的Map.GetCityPlots为nil，不能搬用UI购买集合。按原版CityPanel.lua:620的Cities.GetPlotPurchaseCity(plot)消费者另查，Core确有该函数，owned2277实际返回完整邢州458758／owner0／59,32。仅一次真实读，不把方法类型或旧自然学家桥当新桥已经成功。

608获得完整当前救粮策略／Runner、既有Gameplay持久桥／Journal／Snapshot及真实UI消费者。单次HTTP完整stop／DONE／合法外JSON，14474+907=15381tokens，8193.5603ms、有效首内容2077.2999ms、峰1，复用Nov11成功1.19.5缓存，0OpenCode原生生成。

候选选ARMED持久方向，但整份协议不采用：记录缺目标城坐标；转换边全标不能发送、另一个列表却直接发送，缺少“本次UI新鲜许可”与“旧ARMED只观察”的闭合边；UNKNOWN没有后续观察转换，迟到成功无法闭合；TurnMismatch的Reject没有说明保留未知记录；strict schema只是标签，没有上界／有限数／唯一性／容量；持久化后最终UI资格与原写API重检未列明；负例只有20个标题，没有状态和预期。没有代码执行，不把文字含混说成真实删除或Native失败。正确承认的Cities端口与队列／保存非原子性来自已提供合同，不追授新代码采用。

负责人接手的最小方向：ARMED／OBSERVED，两城完整ID与坐标、owner、plot身份、单调串号／token与严格有界schema；所有不明回包继续保留ARMED，后续回合／读档仍可观察实际归属及粮食，不能重发。只有本次UI新Prepare确实持久写读回成功才可能在最后UI重检后提交一次。旧ARMED不是新许可。写前持久化后若资格变化而没发送，可能保守长期保持，代价必须单列，不能用超时或新token绕过。

待写软件与故障用例的实际预期包括：

| 场景 | 必须保持的边界 |
| --- | --- |
| 属性读抛错／未知schema | 不当成空新账本，不授权城市命令 |
| 属性写后读回不明／Prepare回包未知 | 0城市命令，只再读取实际账本 |
| 已ARMED后原写API或城市身份变化 | 0本次城市命令，持久未知不被丢弃 |
| Request false／void／throw | 同一请求后续回合及重载0重发 |
| 旧ARMED没有实际地块效果 | 不发新token绕过、不清空等待 |
| 迟到地块效果且真实food非负 | 可观察并持久闭合，不重复发送 |
| 地块已归目标但food仍负 | 不用预计值宣称救粮通过 |
| 目标完整ID／owner／坐标不符 | 不用槽位对象冒旧城，不写他城 |
| turn变了但旧请求未知 | 旧记录继续保持，不能按过期删除 |
| 记录或串号达上界 | 关闭新申请，不裁掉未知历史 |

这些是待实现／待验预期，不是已执行通过。608准备wall记录被111冷验打断，主动工时、缓存tokens、净节时保持null。累计608任务／568完整／37length／3transport／638HTTP／30extra，0原稿Native或新属性写。旧恢复FAIL、水坝／队列／性能／全矩阵及武汉冷读产出差异仍开。

[模型采用分账、实际Core端口与累计](../research/baiqi-p6-food608-persistence-review-evidence-2026-11-11.json)。
