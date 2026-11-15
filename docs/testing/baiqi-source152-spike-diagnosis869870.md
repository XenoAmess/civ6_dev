# 152：十二子函数诊断准备，不覆盖76ms失败

2026-11-15，BF-202609141645。[证据](../research/baiqi-source152-spike-diagnosis869870-2026-11-15.json)；[原有效B_plan FAIL](baiqi-source152-stageA-fail.md)。正式采样已完成、导出、精确撤钩并释放互斥后才派发新任务。869／870完整源码和实际尖峰数据并行，峰值2／重叠28.875046s，均stop／DONE／合法JSON；86985656+803tokens／28898.026ms／TTFT20228.827，87088628+1283／32051.162／22307.672。

869建议的十个词法函数都真实存在。采用其建造者分阶段路线／包计时与SettlementSites测点：Tick还会直接续跑AdvanceBuilderRoute，仅测ProcessBuilder会漏掉消费者。它把Economy→RecruitAllowed写成串联不准确，实际ProcessCity分别调用两者；没有深递归或具体子函数引起76ms的证据，拒绝这部分推测，不采用产品补丁或因果结论。

870原稿Python语法合法、marker路径也与实际相同，不能把这两点记为模型错误；Owner首回执把字段命名wrong_proposed_marker，已保留原件并另写更正。整份仍拒／0执行：未调用正式空闲、未做实际CPU预留，以目录排他冒充CPU预留；未调用给定g152a安装／存档检查，只读marker而不核119文件；ZIP只查存在，没有字节与原Controller前缀证明。

Owner规范CPU预留后实际构建12个作用域词法wrapper，覆盖上下文、读回、城市、建造者／移民、持久结算、解叠、发令和路线包／选址。仅Controller变化且原全文精确前缀、119ZIP／目标／源对齐、97Lua5.1／5.3编译，v2保激活观察器之前的活跃88／89调用，容量4096共享。包SHA256 `07864e7e69e7db00a14be76711a6cfcc1d440fd50642649d3788ab87e2452457`，此切点尚未安装／实采。子计时增加开销，只用于诊断；原312样本／76ms FAIL保留。

StageA正式退出后进程已消失，清残留守卫在创建意图前NoSuchProcess停止，实际0terminate／kill，不冒称是本次终止、退出码未知。85／主210及QA91各档保持。累计870／801完整／66length／3最终传输／901HTTP／30extra，0在途、新增OpenCode原生0，未知成本null。继续新鲜离线冷启动与实际子函数计时，不因准备完成结束修复。
