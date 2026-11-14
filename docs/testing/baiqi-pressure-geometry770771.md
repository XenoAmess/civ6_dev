# 独立压力地形生成与核验／770—771

2026-11-14，BF-202609141645。[结构化记录](../research/baiqi-pressure-geometry770771-2026-11-14.json)。只增加外部工具／自制布局，发布142的119文件哈希与前次构建完全一致，主334未查询／操作。当前没有地图入口、安装、Native新世界或压力实测，完整TC036仍PARTIAL。

布局`tools/fixtures/pressure_layout_v1.json`固定44×26、不横向环绕，11个唯一地块分配10个人类城市及1个对手城市，双方各一个起点。`tools/lua/pressure_fixture_geometry.lua`返回函数`Generate(E,layout,variant)`：只用于未来新地图回调，先完整检查布局、全部端口与1144个地块，再各写一次地形，最后区域／咽喉／大陆及双方起点。NO_SITE只留11个草原城市预定地，其余海洋；MANY除11草原外全草原丘陵。城市仍未创建，不能凭生成结果判无合法落点。异常原样传播，不重试或续写。`E.in_generation`是私有调用者合同，不是Native权限或事实证据。

`tools.qualify_pressure_geometry.qualify_pressure_geometry(data,layout)`纯函数核对实际快照的严格schema／类型、全部1144可见地块、11城位置／归属、每玩家城市ID唯一和城市地块一致性。城市ID跨玩家可重复。非法或不可见数据抛ValueError，完整但地形不符为NOT_QUALIFIED；NO_SITE必须每一非城地块都是水，只证明当前Controller必要的非水／非城市几何门没有候选。MANY全陆地仅报READY_MANY_GEOMETRY_ONLY，多候选压力永远null，必须另读自然调用的实际入池数量≥12。

12项Owner软件方法通过；Lua51／53两种地形均执行假端口，验证1144次写入及顺序、最后一个地块失败仍零写入、setter异常立即停止；Python验证错误类型／缺失额外字段、ID命名空间、可见性和地块覆盖／归属。均为合成数据，无Native效果。Owner第一次测试有1处Lua代理表内容相同却直接比较失败，改为逐字段／全部11slot比较后12通过；未因该失败修改实现。

两个模型候选完整stop／DONE／strictJSON，但代码与测试均0采用。770原稿Lua51解析失败（//），全局Generate无返回模块、缺变更端口预检与严格有限整数校验；7测试全在不存在的lupa.lua51.Lua处错误，另有JSON直接嵌Lua、缺StampContinents及空顺序测试。771合法输入KeyError4，误把坐标集合解包为坐标／owner，其他ID唯一／城市地块和bool类型检查不足；212行实现超180、8方法超请求<8，原8测试3通过5错误。负责人独立重写，并保留全部原件和失败。

实际POST在途峰2，共同22.162093秒；770为3001input／2866output、22165.765ms，771为3002／3900、27720.327ms，各1attempt。累计771逻辑／717完整流／51length／3最终transport／801HTTP／30extra；服务端并行、缓存、有效Owner成本和净节省未知null。Nov14 OpenCode1.19.5维护成功缓存复用，原生生成／工具0。后续继续核实地图注册和普通场景夹具准备，Steam未联网或上传。
