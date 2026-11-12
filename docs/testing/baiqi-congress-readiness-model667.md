# 292：世界议会阻挡的实际识别

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-congress-readiness-model667-2026-11-12.json)。源／安装／运行仍129；只新增证据工具与私有验收驱动。

END290后两个context仍290、LeaderScene隐藏、UI active true／allowed false／busy false／messages false。截图实证普通世界议会，不能把WAIT_AI状态当成正在计算的原因证明。测试玩家按原版UI投政体A民主主义、移民A加拿大、外交胜利A白绮各1免费票、0外交支持，提交一次，关闭“全部已提交”后独立实际291。END291后又遇针对巴西占罗马的军事紧急议程，投1免费反对票、0外交支持，不加入紧急状况或宣战；提交一次、原版关闭后独立确认292。两个普通END／14军SKIP／0UserForced，没有重发END，也没有后台外交。移民票不是本方内政补装，投票不计托管实效。

667先提供完整3116+1136=4252tokens／7129.3645ms／stop／DONE／合法JSON候选。原件对UI/scene为None或缺字段共4个见证仍在base UNKNOWN后继续索引，抛TypeError／KeyError。Owner窄采用分类并在base UNKNOWN时跳过不安全的基础字段索引，同时继续完整验证每个modal字段。原候选0Native。

[扩展分类器](../../tools/modal_readiness_evidence.py)要求WorldCongressPopup／WorldCongressBetweenTurns／WorldCongressIntro恰好各1，三者与UI／LeaderScene同scope、实际玩家0及实际turn，所有字段严格类型。缺项／重复／未知context／末项未知，即使首项可见也为UNKNOWN；不能凭可见前缀授阻挡或READY。[10项新测试](../../tests/test_modal_readiness_evidence.py)全部通过，包括坏base不抛出、巨大整数、全体字段、对齐、状态优先级和输入不变。前次11项与旧产品1858项不合并冒充新全套。

实际特殊议程291时，5个串行context均实际291／玩家0／同资格scope；LeaderScene隐藏、WorldCongressPopup隐藏、BetweenTurns隐藏、Intro可见，2.523995秒明确返回MODAL_BLOCKED、qualified false，0自发游戏动作。测试玩家处理后新独立监视实际292 READY。原帧解析保持严格，不自动点击、没有动作重试；READY不是结束权限。

292的11城food／vitals通过，邢州仍11人，原曼哈顿计划497/500未改。控制论291为184.4453125、292为374.58984375/1100；后续科技、实际海上施工与持续供电、粮食历史矩阵继续。累计667／621完整／43length／3transport／697HTTP／30extra；同机同用户每日维护成功缓存复用，OpenCode原生0，未知成本null，Steam离线／工坊82。


后到纠正：[668操作与人口记录](baiqi-shanghai294-population-model668.md)确认特殊291提交后关闭坐标后来打开菜单，不能把坐标点击计为成功关闭该页的证明；293已依新图恢复。原独立292 READY证据保持。
