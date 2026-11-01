# Civ6 本地模型接入

2026-11-02起必须使用 [local-model-operations](https://github.com/XenoAmess/local-model-operations) 的共享规范。本页只描述 Civ6 业务适配；现行调用和维护规则分别见共享 [AGENTS](https://github.com/XenoAmess/local-model-operations/blob/main/AGENTS.md)、[指南](https://github.com/XenoAmess/local-model-operations/blob/main/docs/usage.md)、[每日维护](https://github.com/XenoAmess/local-model-operations/blob/main/docs/client-maintenance.md)与[长期运营prompt](https://github.com/XenoAmess/local-model-operations/blob/main/prompts/capability-operations.md)。

共享仓库放在本项目同级的 local-model-operations；已有正确仓库先检查工作区和 fetch，不覆盖已有目录。其它布局使用环境变量 LOCAL_MODEL_OPERATIONS_ROOT。接入基线为共享 c652acd，实际调用每次读取当前共享 config/executor.json，不把地址、模型或重试策略复制回本项目。[接入清单](local-model-executor-config.json)保留来源、Civ6 system提示及真实任务调度要求；只将共享默认的Java上下文改为本项目工程上下文。

在仓库根目录通过 CMD，对已经准备好的真实任务调用：

```bat
python -X utf8 tools\local_model.py --task .local-model\task.txt --source path\current-source.lua --output-dir .local-model\unique-task --max-tokens 4000 --owner civ6-root
```

命令是参数形状，先替换成当前实际任务和完整相关声明、生产者、消费者，不为演示或配额发请求。--source去重并按给定路径排序，正文实际装入固定三消息；--task-id、--machine-id、--owner、--stop-file可显式指定，身份缺省由共享CLI按环境变量/主机/用户选择。--config现在接受Civ6接入清单，不再接受旧版独立HTTP配置。

tools/local_model.py只准备输入、委托共享CLI并检查候选JSON对象，不执行模型代码或游戏动作。共享CLI先执行每日OpenCode维护，再进入HTTP；同机同用户同日成功缓存复用。维护失败保留75和修复诊断，由负责人自主修复、真实复查后恢复任务。不要直接导入底层dispatch绕过维护；其它直接HTTP或嵌入客户端先运行共享 scripts/check_opencode.py 或调用ensure_current。Windows仅使用CMD，子进程argv不经过shell。

--max-tokens为1..16000；默认timeouts直接来自共享配置。--timeout只有显式传入时覆盖共享read_seconds（有限、0到3600秒之间），不修改total_seconds。总耗时是共享调用器的行间检查，不能当硬总截止；停止文件也不即时打断在途HTTP/退避。传输重试由共享实现唯一管理，只重发模型请求，绝不重放游戏动作；length整份丢弃不自动重试。

每个任务必须使用尚不存在的独占证据目录。规范原件为 REQUEST.json、EVENTS.jsonl、ATTEMPT*-RESPONSE.sse、ATTEMPT*-CONTENT.txt、ATTEMPT*-RESULT.json、SUMMARY.json；不再生成旧的lowercase传输原件。ADAPTER-PROVENANCE.json记录实际共享commit、caller/config/本项目清单哈希与显式覆盖。兼容result.json只是最后一次结果投影：success表示完整stop/DONE、共享成功且JSON对象合法；adopted永远为null，需人工审阅。length/半流不读取为候选，不拼接；非法JSON、数组、NaN及重复键均拒绝。原始证据不改写。旧内部execute/iter_sse_data/retry_kind不再是接口，HTTP/SSE回归由共享仓库负责，本项目只测适配边界和真实prepare_request消费者。

独立真实任务优先并行，准备、POST、审阅、必要验证重叠；12–16是有真实积压时的初始目标，不是调用配额。记录真实POST区间峰值及持续时间、当前在途、累计请求；服务并发和缓存未知保留null。候选完整、源审采用、软件检查、正式发布、真实游戏效果分别记录，不能从传输成功推出能力或节时。

普通HTTP候选与OpenCode原生工具模式分别更新共享能力案例；OpenCode每日检查不算原生工具生成任务。通用经验写共享仓库，游戏证据保留本项目公开反链；原始请求、SSE、候选和机器日志只留被忽略的.local-model/。维护共享仓库也遵循精确stage、main、每个完整单元验证后提交推送。

原指南、配置及截至76a41d8的完整经验已[精确归档](https://github.com/XenoAmess/local-model-operations/tree/c652acd43805d6b0df333238278cc9ea870a485d/docs/history/civ6-2026-11-02)，迁移来源、哈希和限定见[经验入口](local-model-experience.md)。
