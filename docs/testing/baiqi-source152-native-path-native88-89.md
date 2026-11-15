# Source152原生路径细分：此次未复现尖峰，原FAIL保持

2026-11-16，BF-202609141645。[汇总](../research/baiqi-source152-native-path-native88-89-2026-11-16.json)／[全部1313行](../research/baiqi-source152-native-path-samples-2026-11-16.json)。使用[已验证的QA工具](baiqi-source152-native-path-tool.md)，产品未修改。[原StageA有效76ms FAIL](baiqi-source152-stageA-fail.md)与[前次不同调用的70ms根／58ms移民处理](baiqi-source152-coarse-native88-89.md)都保留；本轮没有复现，不能记修复或通过。

同85冻结档，12词法子函数加唯一PathStep原生调用，14绑定、共享4096预算；当前Native函数按原求值顺序传入，不改全局API。新鲜Steam后台离线证明后冷启动，CPU1—8，实际预热72.611秒、规范互斥先于正式重载；普通END85—89各一次，独立激活86—90，87原版告别一次，90收尾不结束。0人工文职／生产／研究、UserForced或后台军令。首次离线查询不可用时尚无启动意图；正式菜单导航后再独立证明，不把导航当离线证据。

83根／1313行全部导出，0错误／丢样／无效时钟／元数据错误。最大根root11@88约14.999866ms，其中ProcessSettler12.000084ms、SettlementSites5.000114、KnownExpansionSupport及PathStep各3.999949、RequestCivilian1.999855、原生GetMoveToPathEx1.000166。全例Safe／GetVisibleUnits／CivilianMoveTarget各最大约1.000166ms；SettlementHeld0。实际4次ProcessSettler。重叠样本不能相加，未包裹的根内工作也不能推断免费；此原生计时仅覆盖PathStep的唯一调用点，不泛指所有路径API消费者。

这些是本轮独立调用，不能与前次最大值相减成因果残差，不能因本轮原生路径小于约1ms就排除它在其他调用中的代价。下一步审核未覆盖的根内工作及其余未完成验收，不重复采样换掉原FAIL。

实际到90后城市由10增至11。停记录、14身份核对还原与精确观察器撤除，保存518764字节／SHA256 `fe11209dbfee6b236a8e58401171c89420fc90b64a196e6b7d54a5e596538036`，正式退出一次；私有直通调用点到进程退出才消失，未冒称恢复普通安装包。规范互斥在导出／撤钩后释放，期间0HTTP或重型测试。上一轮a实例正式退出后仍留静止残留，通过无窗口／监听及2秒CPU不变检查后仅terminate一次、exit15、0kill升级；与他人／远端游戏无关，未冒称自然退出。主210／StageA91／coarse90及历史档保持，无上线上传。
