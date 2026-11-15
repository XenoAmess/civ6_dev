# 152性能：计时与配对包已准备，尚未实测

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-source152-performance-preparation867868-2026-11-15.json)。[152主线210已保护](baiqi-source152-native208-210-865866.md)，正式退出一次后自有进程仍残留；超过180秒、0全部窗口／监听、两秒CPU不变后单次terminate退出15，无kill升级，不称自然退出。全旧档及210完成档保持，Steam0上线上传。

两个真实未完成任务并行POST峰值2、重叠11.377067秒。867为规划计时包，18375+782=19157tokens，11370.190ms／TTFT3790.532ms，完整stop／DONE／JSON。其正确使用规范构建器、区分源和instrumented哈希、校验119目标／ZIP、97双Lua及4096容量；但仅import而未调用assert_no_model_activity，安装与存档只在构建后检查，limits却声称已检查。Owner在预留前补正式空闲／无HTTP／安装及存档预检，部分采用其余主体；原稿不直接执行，修改后的准备器真实执行，0Native／安装。

868为配对包，22901+1717=24618tokens，17552.878ms／TTFT5705.763ms，完整stop／DONE／JSON；Python非法`.local-model`导入直接语法错误，整份拒／0执行。独立把真实modinfo交给其json.loads也报错；未执行的其他静态缺陷是缺119ZIP／目标校验、只把编译及render身份写在limits、修改集合不符分支pass、receipt用w覆盖。编译／原生结果均不追授。

Owner另用现有构建器准备启用／对照副本：各119文件，分别仅Executor与12文件变更，逐文件目标／ZIP字节一致，97Lua5.1／5.3编译。相同前缀`c80f6c48…`与152结束桥`d4ca8ddd…`，启用版移除计时前缀／激活别名后恢复原Executor全文。规划包SHA256 `503a6e8be3d90be9df1f64e4df6db839cc5bfcd2c5ed32d46130476a789c0ff9`；配对启用`31ad0999f79dd7cc692af18349d8deca4270b8120073a9d7d51fb21116bacf88`，对照`b3cfb74bbd2852b446c52cf973cb1ea173fd0b23580dec7009aece505c137bea`。构建期间规范CPU预留、原包和存档检查均完成，未安装、未实采；不把私有对照变成产品开关。

当前152的B_plan／B_turn／N_req／B_delta及两类压力矩阵仍未测；142已通过仅保原精确范围，151旧计时包不复用为152。产品与前一包的62相关／原全测基线未改，不再虚报新全测。累计868／799完整／66length／3最终传输／899HTTP／30额外，0在途、新增OpenCode原生0；每日维护缓存复用，缓存量／服务并发／完整Owner主动成本／净省时null。继续新鲜离线冷启动、85夹具预热及正式重载，在正式测量开始前取得互斥预留。


后续：[152正式十城B_plan有效采样但max76ms未过](baiqi-source152-stageA-fail.md)；本篇“未实测”仅指准备切点，不代表当前状态。
