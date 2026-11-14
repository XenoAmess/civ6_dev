# L的Admin分项未重现正式超限

2026-11-14，BF-202609141645。[L实际分项与保存原值](../research/baiqi-admin141-L-2026-11-14.json)。独立冻结141 Admin包，SHA256 `63db2d52b80e69ba8a9b7c6a5face0f0b5e387e515a819e07d5f1fa2ef563048`；原85初载预热92.817秒再正式重载。普通END85—89各一次到90／11城，90活动十秒后停止，不END90。根与12子项共4096池，87—89保留82根／904行，0错误／丢弃／坏时钟／元数据错误，全部父子区间／根编号／原生锚点审计过，区间分类{'whole_before_observer': 0, 'overlaps_observer': 0, 'observed_window': 82, 'outside_window_started': 0}。

最大Admin18.000126ms（88根31），其中FoodTileRescueRunner约8.000135ms、FloodPurchase约5.000114ms、Governors约1.999855ms；下一根15ms，其他根最大约12ms。全轮Research／FoodFocus／Religion／GovernorDemand／Rescue／GreatPeople／Government约各1ms以内（浮点约1.000166ms），PowerResearchChoice只观测到0ms，不据此断言没有成本或不用再看。嵌套值不能相加。

L没有重现正式141的Adminp95 21ms／max27ms，原因未知。它只有三个诊断窗／82根，未达到正式五窗且每目标纯十城至少100要求，不授B_plan通过、缓存命中或源码提速；正式141 FAIL保持。所选执行器里FoodTile／Flood相对较大，但不足以单凭本轮18ms根再改游戏逻辑。

744完整helper经Owner构建器接入实际Admin，真实标签、父子关联、单池计数和十三原身份恢复有Native证据；参数／nil／错误对象仍仅软件证据，不扩授候选独立发现瓶颈。运行和安装始终冻结141，仓库期间已前进142也不能混记142验收。

90已存518724字节，SHA256 `bc4b79a87444aca49d06f9c20bdb7e9645449a9de8e0c558ff32ec5f1f5d9214`；十三绑定／自有监听撤下，原版退出一次。自有退出残留无窗口／监听／CPU活动，在239.350017秒后清理，Steam零上线／上传动作。下一正式142 M包已准备，继续独立冷实例复测；HTTP仍累计746，没有新模型调用。
