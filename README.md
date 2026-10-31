# civ6_dev

《文明 VI》新领袖【白绮】开发仓库。领袖能力【为我前驱】负责自动生产、自动建造与自动扩张，并加入玩家指挥军队支付代价夺取他人资产的设计。玩家保留军队指挥权；已有可安装的自动内政原型和部分实机证据，完整功能验收尚未完成，有偿夺取尚未开放。

- [原型安装与当前实现](docs/implementation/baiqi-prototype.md)：构建安装、操作、参数、实机结果与尚待完成的范围。

- [协作与提交规则](AGENTS.md)：每个工作包验证完成后立即 commit + push。
- [本地模型指南](docs/local-model-worker-guide.md)：连接、真实任务派发、并发与候选验收。
- [本地模型唯一配置](docs/local-model-executor-config.json)：`qwen38-coder`，无需密钥。
- [经验与采用记录](docs/local-model-experience.md)：参考项目来源、本项目实际调用与能力边界。
- [白绮需求清单](docs/requirements/baiqi-requirements.md)：28 条需求、来源、待定规则与用例追踪。
- [测试验收方案](docs/testing/baiqi-acceptance-plan.md)与[40 项测试用例](docs/testing/baiqi-test-cases.md)：环境、夹具、步骤、通过条件、证据和结果模板；首轮原型实测见[运行记录](docs/testing/results/2026-10-31-p1-smoke.md)。
- [白绮与为我前驱设计规格](docs/design/baiqi-delegate-execution.md)：确定的名称、自动生产／建造／扩张范围，以及军队指挥权的实现边界。
- [有偿夺取设计](docs/design/baiqi-requisition.md)：新增军队主动能力的触发、代价、城市与设施范围，以及待验证的归属转移。
- [战斗领袖与自动建设预研](docs/design/custom-leader-autobuild-research-2026-10-31.md)：领袖玩法、自动化范围、原版源码依据与最小原型验收。

本地模型和模组打包工具仅依赖 Python 3.10+ 标准库；Lua 软件测试使用 `requirements-dev.txt` 中的开发依赖。在仓库根目录通过 CMD 执行：

```bat
python tools\local_model.py --help
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools\build_mod.py --install
```

真实任务的调用方法见指南。工具保存完整请求、每次流式响应和结果，候选始终需要人工或主执行者审阅，不会自动执行返回代码。

协作规则和本地模型资料改编自 [XenoAmess/ck3_eternal_recurrence](https://github.com/XenoAmess/ck3_eternal_recurrence/tree/70bb3de383adf0547bac8af0c487387d9da63160)，保留 [GPL v3 许可证](LICENSE)。历史 CK3 实测不代表本项目的 Civ6 功能已验证。

游戏通过本机 Steam 安装，游戏文件、账号资料、私人存档、模型请求原件与截图不进入公开仓库。
