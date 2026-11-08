# civ6_dev

当前源码／安装／冷实机91。[总督自动调派与三回合回升（3图）](docs/testing/baiqi-governor-loyalty-native-91.md)：成都压力转正，125忠诚13.28；产能仍0，长期恢复继续验。软件1306通过／1SDK跳过，104文件／82Lua5.1；扩张保护540仅候选未接线。其他设备占用Steam，禁止上线／上传，公开Alpha2仍82／12图。

[Alpha 2已在GitHub预发布](https://github.com/XenoAmess/civ6_dev/releases/tag/v0.1.0-alpha.2)，[安装与风险](docs/releases/v0.1.0-alpha.2/README.zh-CN.md)，含[12张实机的逐图解读](docs/workshop/v0.1.0-alpha.2/screenshot-commentary.md)、BBCode、独立宣传封面与明确风险。**Steam已同步Alpha2内部82／12图**，93个文件实际下载核对一致，客户端已恢复并只读确认离线。下列开发条目保留各历史切点，旧“尚未开始／当前”不能覆盖最新记录。

- [82全新开局首都与两张实机图](docs/testing/baiqi-newgame-first-capital-82.md)：false新局标志、自动建西安、纪念碑0→4/60及第2回合正式重载窄通过。中途保存续建与旧档扩张缺口仍在，工坊Alpha74未更新。

- [82自然建城与中途保存失败窗口（3张实机图）](docs/testing/baiqi-settlement-lifecycle-recovery-82.md)：156建成太原、157粮仓7/32；非空ARMED确实入档，但重载后的存活移民经过两个普通回合仍未续建，完整恢复未通过。

- [82冷启动、空日志与两张实机图](docs/testing/baiqi-settlement-native-init-82.md)：UI／Core完整读回及普通保存／重载后世界核对；空日志可能重建，尚不能授持久意图或未决建城恢复通过。

- [82建城持久授权软件](docs/testing/baiqi-settlement-persistent-82.md)：Core一次授权、读档恢复枚举、前端授权后复核已接线；完整1153项软件通过，93文件包。82冷实机尚未通过；未知移民继续等待。

- [81日志与Core存储组件](docs/testing/baiqi-settlement-storage-81.md)：45个合同子场景、完整1132项软件通过、89文件包；尚未接实际发令／恢复入口，实机仍80，不能称中途恢复通过。

- [建城中途恢复的Core／UI接口核对](docs/testing/baiqi-settlement-recovery-boundaries-80.md)：Core可读已知城址与可见性，但没有IsSavedGame；两份候选已拒，持久协议仍未实现，不将完成后读档升级为中途恢复通过。

- [80同一名新移民完整窄链：长沙、初期生产与148正式重载](docs/testing/baiqi-natural-settler-founded-80.md)：147一次建城，148粮仓3/32与忠诚100／+20保持，三张新原图；未决动作持久恢复、长期质量及完整40项仍未闭，工坊仍Alpha74。

- [80正常训练与实际人口成本，三张原图](docs/testing/baiqi-natural-settler-training-80.md)：益阳自动训练190产能，142新移民7929900出生、人口14→13并接续下水道；安全路线与建城继续验，工坊仍Alpha74。

- [80双场景实机与三张原图](docs/testing/baiqi-known-border-native-80.md)：坏城址保留移民等待，有己方支撑处自动建九江，138粮仓3/32与正式重载保持；保守筛选及短窗口不等于长期保城，工坊仍Alpha74。

- [80保守边境筛选的软件修复](docs/testing/baiqi-known-border-screen-80.md)：22新增回归、完整1130通过；原坏目标与有支撑目标冷实机待做，不能据此关闭忠诚失城FAIL，工坊仍Alpha74。

- [79同档建城回执、生产与175正式重载](docs/testing/baiqi-found-city-receipt-native-79.md)：实际1次建城正确observed，附2张新实机图；忠诚54／每回合−23及选址缺口仍在，工坊仍Alpha74。

- [79建城回执软件修复](docs/testing/baiqi-found-city-receipt-79.md)：24新增回归、完整1108项通过；冷启动实机待做，忠诚选址缺口仍开放，工坊仍Alpha74。

- [78临淄178实际叛离，两张实机图](docs/testing/baiqi-new-city-loyalty-loss-78.md)：173建城、175忠诚54、177为8、178实际变为自由城市。扩张选址质量记FAIL，继续修复；工坊仍Alpha74。

- [78同档绕行建城、六张实机图与忠诚风险](docs/testing/baiqi-settler-detour-native-78.md)：173建第16城、粮仓自然产能和175正式重载保持；成都港口／九江工业区已完成。新城每回合忠诚−23及建城回执缺口仍未关闭，工坊仍Alpha74。

《文明 VI》新领袖【白绮】，能力【为我前驱】：内政、生产、建造与和平扩张强制由 AI 执行，玩家查看城市、指挥军队、处理全部外交并结束回合。外交来访、世界议会、城邦使者及宣战议和均由玩家决定。没有托管开关、手动接管或地块保留入口。已完成风云变幻五城二十回合的少操作实机窗口；开发原型仍在验证，尚未完成全功能验收。

征城改为选中军队后直接右键与敌城互动，满足条件时确认金币代价；可继续普通进攻或取消。粮仓经营权已按用户要求删除，旧版效果须清理。

**公开Alpha：** [v0.1.0-alpha.1下载](https://github.com/XenoAmess/civ6_dev/releases/tag/v0.1.0-alpha.1)，内部构建74。先读[安装与真实实机图](docs/releases/v0.1.0-alpha.1/README.zh-CN.md)和[已知问题／未验收风险](docs/releases/v0.1.0-alpha.1/KNOWN_ISSUES.zh-CN.md)。这是预发布版，建议独立新局，不承诺长期主档可靠性。

**Steam工坊：** [白绮 Alpha 2](https://steamcommunity.com/sharedfiles/filedetails/?id=3833805495)已公开，12张真实实机图已内嵌正文，新封面与恢复风险明确标注。[图文／BBCode／上传源码](docs/workshop/v0.1.0-alpha.2/README.md)及[发布回执](docs/workshop/v0.1.0-alpha.2/publication-status.json)已入库；实际工坊下载的93个文件与82版pin一致。上传前检查账号占用，禁止顶号。

白绮接管研究、政策、排产、建设和移民扩张。你用手头的军队和国库处理前线，决定外交，并结束回合；城市可以查看，但没有临时接管。

![74版局内总览：军队由玩家指挥](docs/releases/v0.1.0-alpha.1/screenshots/overview.png)

![74版城市查看：允许查看，不能手动改生产](docs/releases/v0.1.0-alpha.1/screenshots/city-readonly.png)

![27版QA场景：地图右键后的征城、正常进攻与取消选项](docs/workshop/v0.1.0-alpha.1/screenshots/requisition-confirmation.png)

征城图为27版QA敌城场景，人口1、报价300金币；不是74版重拍。[完整玩法介绍与7张实机图](docs/workshop/v0.1.0-alpha.1/README.md)逐图注明版本与场景。

- [最新开发与验收交接（2026-11-08）](docs/handoff/2026-11-08.md)：当前构建、游戏／存档现场、已验范围、剩余任务及本地模型续接。
- [全部功能状态快照](docs/testing/baiqi-feature-status-2026-11-01.md)、[安装与当前实现](docs/implementation/baiqi-prototype.md)、[持续验收](docs/testing/results/2026-11-01-p6-acceptance.md)、[P5 历史记录](docs/testing/results/2026-11-01-p5-acceptance.md)。
- [74版建筑财政重验](docs/testing/baiqi-building-budget-74.md)：修复规划后收入／承诺变化仍提交建筑，8项回归及完整1029项通过；74已离线冷启并恢复114，[财政压力实机待验](docs/testing/baiqi-cold-start-74.md)。
- [74版财政观察与副本](docs/testing/baiqi-financial-observer-74.md)：独立诊断工具10测及实机接入；测试后已清理观察器并恢复正常114存档。
- [74版财政储备实机对照](docs/testing/baiqi-finance-native-pair-74.md)：相同准备档低库存拒绝、高库存追加1名建造者后在数量上限停止，24支军队对照保持。
- [74版负收入及恢复](docs/testing/baiqi-finance-pressure-recovery-74.md)：合成维护负担下有需求仍拒绝招募，119移除负担后恢复资格与生产；原有移民自然建第12城。完整资源／外部冲击矩阵仍待验。
- [73版排队移动核对](docs/testing/baiqi-queued-move-observation-73.md)：1017项软件通过；旧排队跨回合保持、实际抵达及114自动农场／次数扣除窄实机通过。
- [72版建造者失败目标记忆](docs/testing/baiqi-builder-rejected-goals-72.md)：1013项软件通过；离线推进至112仍未改良，继续修复跨回合排队移动。
- [71版文职占格修复](docs/testing/baiqi-civilian-stack-71.md)：1005项软件通过；离线实机已避开原占格，后续往返耗行动失败正在修复。
- [70版先知与待验范围](docs/testing/baiqi-prophet-bootstrap-recovery-70.md)：999项软件及真实故障冷恢复、Debug新人物执行、完成记录重载和旧未知记录保留的窄样本通过。
- [自由城市QA征城与随城资产](docs/testing/baiqi-minor-city-capture-73.md)：地图右键确认后恰扣1100、转城一次，8栋建筑与文物保留，已恢复正常存档；完整特殊矩阵待验。[资产读取工具](docs/testing/baiqi-special-city-assets-73.md)。
- [74版埃特曼安吉城征取](docs/testing/baiqi-etemenanki-capture-74.md)：1300金币、1次转城；未完工校园及87点进度撤去，后台建成纪念碑。正常114→118后城成自由城市，奇观／巨作随城转走，未重复收费或退款；含确认与叛离实机图。
- [74版既有驻军城市征取](docs/testing/baiqi-garrison-city-74.md)：实际右键／确认300，转城及结束行动各1次；原守军完整ID／敌方归属／37伤害保持，被移到相邻水格并登船。含两张74版原图，完整驻军矩阵未闭。
- [74版扣费后、结束行动前恢复](docs/testing/baiqi-finish-interruption-recovery-74.md)：实际FINISHING中断保存／加载后自动完成，未再扣300；完成后两次Recover均0转城／0Finish，其他恢复窗口待验。
- [74版扣款凭证缺失冻结](docs/testing/baiqi-debit-unknown-recovery-74.md)：实际扣300后停CHARGING，清理钩子、存读档及四次Recover仍冻结，未再收费／退款；费用与行动未假装结清。
- [74版第三方归属与未知态](docs/testing/baiqi-third-party-unknown-74.md)：受控转给第三方后不误认成功、不扣款／退款，正式存读档保持冻结；真实第三方作战及完整中断矩阵仍待验。
- [73版队列第二项右键](docs/testing/baiqi-queue-right-click-73.md)：普通领袖实际删除、白绮拦截，完整队列／费用核验并恢复114正常现场。
- [70版两项生产队列换序](docs/testing/baiqi-two-item-queue-70.md)：普通领袖生效、白绮拦截的真实点击对照，完整队列／费用核验及原档恢复。
- [需求](docs/requirements/baiqi-requirements.md)、[验收方案](docs/testing/baiqi-acceptance-plan.md)、[40 项用例](docs/testing/baiqi-test-cases.md)。
- [能力设计](docs/design/baiqi-delegate-execution.md)、[征城设计](docs/design/baiqi-requisition.md)。
- [协作规则](AGENTS.md)、[Steam 离线流程](docs/steam-offline-workflow.md)：每个完整改动提交推送，普通开发与实测保持 Steam 离线。
- [本地模型指南](docs/local-model-worker-guide.md)、[接入清单](docs/local-model-executor-config.json)、[采用经验](docs/local-model-experience.md)。开发必须使用 [local-model-operations](https://github.com/XenoAmess/local-model-operations) 的共享规范、配置、调用器和每日维护；玩家运行不需要模型服务。

在仓库根目录通过 CMD 执行：

```bat
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools\build_mod.py --install
```

生成的 `dist/Baiqi.zip` 与本机安装内容不入库。游戏、私人存档、账号资料和模型原件均不公开。协作资料参考 [ck3_eternal_recurrence](https://github.com/XenoAmess/ck3_eternal_recurrence)，遵循 [GPL v3](LICENSE)。[P1](docs/testing/results/2026-10-31-p1-smoke.md)／[P2](docs/testing/results/2026-10-31-p2-requisition.md)报告是历史证据，其中旧面板、接管与经营权已撤销。

- [74版冷进程恢复补证](docs/testing/baiqi-cold-recovery-74.md)：完整退出后，正凭证FINISHING自动完成，缺肯定扣款回执的CHARGING继续冻结；两组完成后探针均0额外转城／Finish，TC-029／030仍部分。

- [74版未知扣款正常114→115](docs/testing/baiqi-debit-unknown-normal-turn-74.md)：仍UNKNOWN、冲突冻结，新回合骑手4行动；跨回合及两次Recover原生转城／Finish计数0，资金差值限制明说。

- [74版建造者最后一次改良](docs/testing/baiqi-builder-final-charge-74.md)：独立114／115存档证明538新增农场、1次劳动建造者消失，日志确认缺口保留；原正常114已恢复。

- [74版移民资格拒绝与恢复](docs/testing/baiqi-settler-qualification-recovery-74.md)：115原地一次待命，其他内政继续；撤故障后116自动三步移动，尚未建城，不授完整压力矩阵。

- [74版恢复移民实际建城](docs/testing/baiqi-settler-recovery-founded-74.md)：119胶东新城、原移民延迟移除、自动粮仓及119重载均有独立证据；测试玩家处理一次外交来访，原正常114已恢复。

- [74版地图外军队恢复的软件反例](docs/testing/baiqi-capture-removed-actor-software-74.md)：CHARGED／FINISHING对同ID、延迟销毁形状仍调用动作并完成；实机军队情景未验，守卫修复中。

- [75版征城军队可用性检查](docs/testing/baiqi-capture-actor-guard-75.md)：已修复74的软件反例，新增回归及完整软件检查通过；75安装和实机复测继续进行，工坊仍74。

- [75版征城恢复实机复测](docs/testing/baiqi-capture-native-recovery-75.md)：旧FINISHING恢复、未知扣款冻结、实际军队移除及重载已有窄样本和3张原图；同ID延迟销毁的军队实机窗口仍未验，正常114已恢复。

- [75版过期FINISHING正常跨回合](docs/testing/baiqi-expired-finishing-75.md)：114正扣款中断到115，撤故障及存读档后骑手仍4行动，两组Recover均0转城／Finish；正常114已恢复。

- [75版转城后、扣款前恢复](docs/testing/baiqi-transferred-before-debit-75.md)：真实TRANSFERRED保存点同进程／新进程恢复完成；附前后实机图。新进程前出现一次退出收尾残留，已如实记录，不授干净关机通过。

- [75版已扣款、未写军队冷却恢复](docs/testing/baiqi-charged-before-cooldown-75.md)：真实CHARGED保存点重载后金币保持、军队行动结清，附前后两张原图；正常114已恢复。

- [75版动作已生效后的异常恢复](docs/testing/baiqi-finish-applied-recovery-75.md)：实际Finish1后异常，撤故障两次LiveRecover连续观察仍Finish1；保存点重载及前后两图另列，正常114已恢复。

- [73样本身份更正](docs/testing/baiqi-free-city-classification-audit-75.md)：原“城邦62”实际为自由城市；保留已发生的1100扣费及资产数据，撤回该样本的城邦验收结论。

- [75版真正城邦征取](docs/testing/baiqi-vilnius-city-state-capture-75.md)：维尔纽斯最后一城300金币，实际右键／确认、一次转城与结束行动、存读档及三张实机图。宫殿移除、灭亡敌军Core延迟对象与未验范围均单列；Alpha74未更新。

- [75城邦征取后的正常生产](docs/testing/baiqi-vilnius-production-turn3-75.md)：后台自动排纪念碑，正常2→3后进度0→1／60；忠诚100、金币按净收入增加、军队恢复待命。单回合证据与实机图入库，未授建筑完工或长期稳定。

- [75执行军队升级后的中断恢复](docs/testing/baiqi-upgraded-actor-recovery-75.md)：实际Core保留离图旧骑手完整ID，撤故障与存读档均冻结、无误补Finish；三张图入库。另确认驻军旗帜可绕过城市征取弹窗，记FAIL并继续修复。

- [76驻军旗帜确认修复](docs/testing/baiqi-garrison-flag-confirmation-76.md)：复用已有征取弹窗，新增10回归及完整1058项软件检查通过；安装／冷启实机复测待做，原75旗帜FAIL尚未关闭。

- [76驻军旗帜冷启实机三选](docs/testing/baiqi-garrison-flag-native-76.md)：取消不扣费／不战斗，确认300只结算一次，继续进攻才发生原版战斗；四张原始实机图和存读档证据入库，关闭同一75入口的窄FAIL，Alpha74未更新。

- [76正常训练新移民与人口成本](docs/testing/baiqi-natural-settler-training-76.md)：后台选生产、0→153／175进度、125回合新单位与人口10→9→10的有序事件，三张原始实机图已内嵌；新移民的完整建城链仍在继续。

- [77移民占格后切换城址](docs/testing/baiqi-settler-occupied-route-77.md)：76实机暴露有安全替代却直接待命，77补规划检查；新增6回归、完整1064软件通过，同一正常移民保存点冷验继续。

- [77实机：新移民绕路建成九江，读档后新城继续生产](docs/testing/baiqi-natural-settler-founded-77.md)：5张内嵌原始实机图；同一正常训练演员闭合76→77窄链，明确区分版本、未完成建筑和完整矩阵。

- [77军队训练实机跟踪](docs/testing/baiqi-military-production-77.md)：武汉炮兵109/165、北京步兵77/180，两张内嵌实机图；24现有加2在训符合13城需求26，出生／军费及上限持续观察继续。

- [77新兵实际完成、玩家指挥与军费对账](docs/testing/baiqi-military-born-control-77.md)：炮兵146、步兵147出生，玩家移动炮兵实效与148正式读档通过；解释征兵政策淘汰带来的全军费用变化，新增3张内嵌实机图。低财政／缺资源分支继续。

- [77低金币独立实机分支](docs/testing/baiqi-military-low-reserve-77.md)：69.754低于100储备、有缺兵且炮兵原生合法时，后台0单位请求、两座城继续合法建筑；受控夹具和主148恢复明确记录，资源不足分支继续。

- [77资源短缺独立实机分支](docs/testing/baiqi-military-resource-shortage-77.md)：硝石9不足步兵费用10时改排胸甲骑兵；142自然恢复12后保留原队列51/165。3张实机图、派发前库存和主148恢复证据齐全，完整验收仍部分。

- [77区域容量盘点](docs/testing/baiqi-district-capacity-inventory-77.md)：14城、18普通区域、252条Native记录，找出容量满／缺科技／缺地块的独立样本；只是夹具条件，后台行为和恢复建设继续验。

- [77自然增长与两个新港口完整实机链](docs/testing/baiqi-district-growth-harbors-77.md)：容量恢复、真实坐标派发、正常进度、157／160建成和正式存读档保持，新增7张内嵌实机图；其他区域与完整矩阵继续。

- [77低净收入时暂停扩军](docs/testing/baiqi-military-low-net-income-77.md)：余额6517、军队有缺额且原版炮兵合法，实际净收入0.777时后台继续项目；新增3张内嵌实机图，测试后已恢复主线160。

- [77水上乐园完工、成都增长后新放港口](docs/testing/baiqi-water-entertainment-growth-77.md)：正常165完成并正式重载，4张内嵌实机图；成都港口和九江工业区仍在建。

- [77新发现：移民同一城址绕行缺口](docs/testing/baiqi-settler-occupied-detour-gap-77.md)：77正常训练及出生已核，167因己方先知挡住原生首步而等待；完整绕行／建城未授通过，已保存复现现场并继续修复。

- [78版移民同城址绕行的软件修复](docs/testing/baiqi-settler-detour-78.md)：20新增回归、完整1084项通过，87文件包已生成；安装／冷启动实机仍待核，不授建城通过。

- [83已选城址连续性修复](docs/testing/baiqi-settler-target-continuity-83.md)：原生推荐变化后继续重检旧目标，9项新增回归／全量1172通过、1环境跳过／93文件包；83尚未安装实测，不含冷读目标持久化。Steam与GitHub Alpha2仍82。

- [83离线实机第二城与存读档](docs/testing/baiqi-settler-continuity-native-83.md)：61出城、64到址、65自主建立北京、66粮仓5/65，正式重载保持；3张原图。人口成本、行军计划持久化及未决恢复仍未闭，公开Alpha2仍82。

- [84独立行军计划持久化](docs/testing/baiqi-settler-goals-persistence-84.md)：读档后恢复提案再重检，30新增软件方法，全量1202通过／1环境跳过、96文件包，尚未安装冷验。旧未决建城与旧档等待FAIL仍保留。

- [84真实在途计划／85原生队列守卫](docs/testing/baiqi-settler-queued-goal-85.md)：61真实写入目标1983并正式保存原队列2132，1111447B／1张原图；85软件1210通过／1环境跳过，待冷读同档，不授未决恢复或完整40项。

- [85读档后自动行军、建城与计划清理](docs/testing/baiqi-settler-goals-native-85.md)：84排队61档升级冷读，65建立北京、66粮仓5/65，完成态正式重载保持；3张原始实机图。恢复FAIL、人口成本和完整40项仍开放，公开Alpha2仍82。

- [85移民训练扣人口的事件实证](docs/testing/baiqi-settler-population-cost-native-85.md)：实际4→3→4、粮食33→2，解释两帧4→4；自动接续建造者，51正式重载保持，3张原图。只授该成本样本，恢复FAIL／完整40项仍开放。

- [85读取旧ARMED失败档及接口资格](docs/testing/baiqi-armed-upgrade-and-native-api-85.md)：旧日志保留，恢复仍FAIL；宗教四类实际演员为0，权限待验。缺失属性实际0返回，撤回function误读；1张原始实机图。

- [86先知资格修复](docs/testing/baiqi-prophet-ownership-86.md)：原版“拥有先知”含义纠正，17项Lua5.1对照由旧版11失败到修订全过；完整1213通过／1环境跳过，待冷实机。旧LEGACY保护不清除，公开Alpha2仍82。

- [86古典新局实机与4张内嵌图](docs/testing/baiqi-classical-native-86.md)：26普通回合、自动生产／五处改良／寡头四卡及66正式重载已核；先知点0、激活仍未验收，被俘提示与斥候受伤如实记录。公开Alpha2仍82。

- [87区域经济改良修复与86后续3图](docs/testing/baiqi-district-improvements-87.md)：74实机发现合法农场地块被旧筛选排除；修订9项Lua5.1对照通过，完整1222通过／1环境跳过、96文件包待冷实机。玩家近战及议会提交／恢复已补，文职损失与无新先知如实记录。

- [87冷加载与玩家城防实机3图](docs/testing/baiqi-cold-city-range-87.md)：74→78普通推进、商业中心后转移民、玩家两次城防伤害读回；区域农场消耗与新先知仍未触发。78已撤钩备份，接续正式无野蛮人对照，围城风险保留。

- [87无蛮族对照：三城、加载保持与5张实机图](docs/testing/baiqi-nobarb-three-cities-87.md)：40→85普通推进，71/78自行移民建城，原版保存加载后3城7单位保持；区域观察首都限定已纠正，农场替换／新先知仍待正案。

- [87五城二十回合与5张实机图](docs/testing/baiqi-five-city-twenty-turns-87.md)：99→119零人工内政，5→7城、6栋建筑、4个特色区、19处改良；矿山替代工业区实际完工。战略资源逐回合库存漏采，TC-037仍未整项通过；验收工具已上库。

- [87五城资源补测通过及5张实机图](docs/testing/baiqi-five-city-resource-complete-87.md)：从正式99档独立重测20回合，21份资源／147行齐全、6建筑4特色区19改良，零人工内政；TC-037仅该GS无蛮族夹具通过。Steam有其他设备占用，继续暂停上线与上传。

- [88传教士报价／日志组件](docs/testing/baiqi-missionary-purchase-components-88.md)：新增17软件方法与7清单检查通过、76Lua5.1编译、98文件包一致；采购需求、Core许可与发令尚未接通。安装／实机仍87，不授88实机通过，Steam占用期间保持不上线。

- [89传教士Core采购许可](docs/testing/baiqi-missionary-purchase-storage-89.md)：补持久许可、传播日志初始化与共用信仰检查；完整1268通过／1SDK环境跳过、79Lua5.1、101包一致。需求和发令未接，未安装，实机仍87；Steam占用期间继续不上线。

- [90传教士自动采购软件链](docs/testing/baiqi-missionary-purchase-flow-90.md)：安全国内需求、一次信仰购买及回执后传播交接已接通；1287软件通过／1SDK跳过、81Lua5.1／103文件一致。未安装／实测90，安装及实机仍87，Steam占用期间不上线。
