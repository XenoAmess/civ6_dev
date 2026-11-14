# 142原版城邦使者：实际派遣与338就绪

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-original-envoy809-ordinary338-2026-11-15.json)。BR-014／TC-035明确把城邦使者保留给玩家，本轮由TEST_PLAYER验收代理处理，后台不新增派使者自动化，也不手动补内政。

实际337有82名未派使者、原版要求派遣。目标8安条克已会面／存活／可收／原生可派／未交战，收到2名；目标6维尔纽斯3名；62自由城市明确不可收／不可派，不把GetAliveMinors成员一概当合格城邦。

一次原版OnOpenSendEnvoys后独立读回界面可见、pending分配合计0。随后原版OnMoreEnvoyTokens(8)和OnConfirmPlacement各一次，分配合计先核0→1。回调返回后独立ActionPanel读取库存82→81、安条克2→3、维尔纽斯仍3。原版OnClose一次标记本次已考虑派遣，81名保留；使者阻塞随后转为军队待命。没有直接调用发送操作、修改私有UI分配表、手写considered或派光库存。证明原版回调及实际效果，未证明物理点击或整个窗口的精确Native请求数量。

此前普通END337返回却未进338，两次只读等待TIMEOUT原件保留。后读337已active／非busy，不能据监测器WAIT_AI标签认定AI持续计算；实际原版阻塞是GIVE_INFLUENCE_TOKEN。完成上述新外交操作后，另发一个普通无REASON结束输入，新阶段独占意图、不清旧END标记；出现佩德罗二世因不同政体的谴责来访。只读当前UI文字后原版KeyHandler Esc一次关闭，独立监测确认338READY。未重发未知动作／使用UserForced／给后台外交或军令。

正常335→336→337另已读回：长沙军事学院336建成后转发电厂，武汉食品市场337建成后转项目；11城至338人口无减少，既有资产／food／vitals读取过。原807自动链在338超时终止，后续从已确认338的新阶段继续，不把原失败改写为完整五回合通过。本切点无340／保存340／功率实效授信。

807／808／809均完整stop／DONE／strictJSON，实际POST峰1。807原正例因Members数字键当单位失败，Owner修双返回迭代、超界拒绝、逐回合once map及ASCII参数，15Lua／13Python场景过。808原正例发明Player.GetPlayerConfiguration而失败，另把HasBuilding写成字符串、燃料只读一次伪成两读稳定；Owner修实际配置表／数字Index／新鲜燃料及范围，9场景过，当前仅软件准备。809核心部分采用，Owner将会面检查改为已供原版major0→minor8方向、函数类型守卫及beforetarget2，11Lua／6Python场景过；不声称反向引擎HasMet一定缺失。每例raw／修订双Lua共4次编译，0模型测试代码采用，原候选0Native。

累计809逻辑／750完整／56length／3最终transport／839HTTP／30extra，Nov15 OpenCode1.19.5成功维护缓存复用、原生工具0。Owner完整成本／缓存／净节时未知；产品142119文件与发行包不变，Steam离线，无上传或截图。全40项与旧ARMED FOUND恢复FAIL继续；[TC-036性能通过](baiqi-performance142-complete805.md)独立保持。
