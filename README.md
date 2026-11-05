# civ6_dev

《文明 VI》新领袖【白绮】，能力【为我前驱】：内政、生产、建造与和平扩张强制由 AI 执行，玩家查看城市、指挥军队、处理全部外交并结束回合。外交来访、世界议会、城邦使者及宣战议和均由玩家决定。没有托管开关、手动接管或地块保留入口。已完成风云变幻五城二十回合的少操作实机窗口；开发原型仍在验证，尚未完成全功能验收。

征城改为选中军队后直接右键与敌城互动，满足条件时确认金币代价；可继续普通进攻或取消。粮仓经营权已按用户要求删除，旧版效果须清理。

**公开Alpha：** [v0.1.0-alpha.1下载](https://github.com/XenoAmess/civ6_dev/releases/tag/v0.1.0-alpha.1)，内部构建74。先读[安装与真实实机图](docs/releases/v0.1.0-alpha.1/README.zh-CN.md)和[已知问题／未验收风险](docs/releases/v0.1.0-alpha.1/KNOWN_ISSUES.zh-CN.md)。这是预发布版，建议独立新局，不承诺长期主档可靠性。

**Steam工坊：** [白绮 Alpha 1](https://steamcommunity.com/sharedfiles/filedetails/?id=3833805495)已公开，介绍按实际玩法重写，7张真实实机图已内嵌正文，宣传封面与已知风险另有标注。[图文／BBCode／上传源码](docs/workshop/v0.1.0-alpha.1/README.md)及[发布回执](docs/workshop/v0.1.0-alpha.1/publication-status.json)已入库；实际工坊下载的87个文件与Alpha哈希一致。上传前检查账号占用，禁止顶号。

白绮接管研究、政策、排产、建设和移民扩张。你用手头的军队和国库处理前线，决定外交，并结束回合；城市可以查看，但没有临时接管。

![74版局内总览：军队由玩家指挥](docs/releases/v0.1.0-alpha.1/screenshots/overview.png)

![74版城市查看：允许查看，不能手动改生产](docs/releases/v0.1.0-alpha.1/screenshots/city-readonly.png)

![27版QA场景：地图右键后的征城、正常进攻与取消选项](docs/workshop/v0.1.0-alpha.1/screenshots/requisition-confirmation.png)

征城图为27版QA敌城场景，人口1、报价300金币；不是74版重拍。[完整玩法介绍与7张实机图](docs/workshop/v0.1.0-alpha.1/README.md)逐图注明版本与场景。

- [最新开发与验收交接（2026-11-06）](docs/handoff/2026-11-06.md)：当前构建、游戏／存档现场、已验范围、剩余任务及本地模型续接。
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
