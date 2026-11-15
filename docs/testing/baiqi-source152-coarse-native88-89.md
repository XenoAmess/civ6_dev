# 152子函数实采：移民处理58ms，继续细分

2026-11-15，BF-202609141645。[汇总](../research/baiqi-source152-coarse-native88-89-2026-11-15.json)／[全部1236条](../research/baiqi-source152-coarse-native-samples-2026-11-15.json)；[原有效B_plan FAIL](baiqi-source152-stageA-fail.md)保持。此次是独立诊断副本，不替换原76ms，也不能当正式性能通过。

同85冻结档，当前152原Controller完整前缀、12个作用域子函数、13绑定、共享4096容量。取得新鲜后台Steam离线证明，CPU1—8，预热544.433秒后正式互斥、重载及日志核验／原版继续。首次后台模式查询不可用发生在启动意图前；正式菜单导航与独立证明分开，无上线上传。驱动起初缺仓库sys.path，import即停；独立证实85／未启用／0根0样本／Driver nil、无捕获意图后补路径，原失败保留，未重放读档或游戏动作。

| 本次实测项 | 最大值 ms |
| --- | ---: |
| Controller.RunNow | 70.000172 |
| ProcessSettler | 58.000088 |
| ProcessBuilder | 14.000177 |
| ProcessCity／RequestCivilian | 各7.000208 |
| SettlementSites | 5.000114 |
| AdvanceBuilderRoute | 3.000021 |
| RetryCivilianOverlap | 1.999855 |
| PlayerContext／ReadBack／RefreshSettlement | 各约1.000166 |

最长根为89回合root60／十城，移民处理58ms位于同一70ms根内；其RequestCivilian约7ms，SettlementSites没有在这个根出现（全例最大5ms来自其他根）。不能把重叠子调用相加、把跨根最大值相减成“剩余”，也不能断言与原88回合76ms同因。PathStep、Safe、KnownExpansionSupport和原生GetMoveToPathEx仍未分别计时，下一步补这些边界；没有据此修改产品或放宽安全条件。

完整保留80根／1236行、0错误／丢弃／无效时钟／元数据错误，激活观察器前的活跃条目也保留并按实际观察锚点归类。普通END85—89各一次，独立激活86—90；90只收尾，11城。军队SKIP和87原版告别由TEST_PLAYER执行，0人工文职／生产／研究、UserForced或后台军令。退出前停记录、13处身份核对还原、撤精确监听；90保存518762字节／SHA256 `69b0dfe68ec9794c2d928732a3564d112c79acca3071b2db67f20318c0c34d8e`，正式退出一次，不冒称自然结束。规范正式互斥在原件导出／撤钩后释放，期间0HTTP或重型测试。

主线210、StageA91和全部旧档保持。新871／872／873任务均在正式释放后派发；当前152B_plan仍FAIL，其余当前版本性能及完整功能矩阵不授通过。继续细分与修复，不靠重复采样换掉尖峰。
