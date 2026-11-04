# civ6_dev

《文明 VI》新领袖【白绮】，能力【为我前驱】：内政、生产、建造与和平扩张强制由 AI 执行，玩家查看城市、指挥军队、处理全部外交并结束回合。外交来访、世界议会、城邦使者及宣战议和均由玩家决定。没有托管开关、手动接管或地块保留入口。已完成风云变幻五城二十回合的少操作实机窗口；开发原型仍在验证，尚未完成全功能验收。

征城改为选中军队后直接右键与敌城互动，满足条件时确认金币代价；可继续普通进攻或取消。粮仓经营权已按用户要求删除，旧版效果须清理。

- [最新开发与验收交接（2026-11-05）](docs/handoff/2026-11-05.md)：当前构建、游戏／存档现场、已验范围、剩余任务及本地模型续接。
- [全部功能状态快照](docs/testing/baiqi-feature-status-2026-11-01.md)、[安装与当前实现](docs/implementation/baiqi-prototype.md)、[持续验收](docs/testing/results/2026-11-01-p6-acceptance.md)、[P5 历史记录](docs/testing/results/2026-11-01-p5-acceptance.md)。
- [74版建筑财政重验](docs/testing/baiqi-building-budget-74.md)：修复规划后收入／承诺变化仍提交建筑，8项回归及完整1029项通过；74已离线冷启并恢复114，[财政压力实机待验](docs/testing/baiqi-cold-start-74.md)。
- [74版财政观察与副本](docs/testing/baiqi-financial-observer-74.md)：独立诊断工具10测及实机接入，当前正在财政QA分支，完整压力结果待验。
- [73版排队移动核对](docs/testing/baiqi-queued-move-observation-73.md)：1017项软件通过；旧排队跨回合保持、实际抵达及114自动农场／次数扣除窄实机通过。
- [72版建造者失败目标记忆](docs/testing/baiqi-builder-rejected-goals-72.md)：1013项软件通过；离线推进至112仍未改良，继续修复跨回合排队移动。
- [71版文职占格修复](docs/testing/baiqi-civilian-stack-71.md)：1005项软件通过；离线实机已避开原占格，后续往返耗行动失败正在修复。
- [70版先知与待验范围](docs/testing/baiqi-prophet-bootstrap-recovery-70.md)：999项软件及真实故障冷恢复、Debug新人物执行、完成记录重载和旧未知记录保留的窄样本通过。
- [城邦自然征城与随城资产](docs/testing/baiqi-minor-city-capture-73.md)：地图右键确认后恰扣1100、转城一次，8栋建筑与文物保留，已恢复正常存档；完整特殊矩阵待验。[资产读取工具](docs/testing/baiqi-special-city-assets-73.md)。
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
