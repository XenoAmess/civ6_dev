# 匹配对照普通END合同／725审阅

2026-11-14，BF-202609141645。[实际输入与候选审阅](../research/baiqi-paired-normal-contract725-2026-11-14.json)。这是尚未实现的B_delta迁移任务，与正在修复的独立Stage A分开：`run_paired_acceptance.py`仍在action中发送UserForced，结果source_version还固定67；实际静态对照构建器已允许140。不能把旧驱动叫作当前普通END匹配验证。

下一步必须在原版TEST_PLAYER军事SKIP准备之后、真正普通RequestAction之前开始计时，避免把选军队停留计成END耗时。计时器在BaiqiExecutor、已验证普通END入口在ActionPanel，跨上下文的自有QA桥及身份恢复尚待实现／实测。静态对照若被真实内政门阻止，不能强制结束或手工补装内政冒充匹配成功；须记录并继续解决对照可执行性。原五组交替顺序、25段及500ms／10%预算保持。

725完整7890tokens／3293.0225ms／TTFT1331.3672ms，单次stop／DONE／合法JSON。候选仍把时钟放在UserForced前，所指action中没有军事准备循环；回执仅“尝试”且声明没有执行Native动作，不满足requested=true／forced=false的实际发行凭证，也没有实现自有桥。0原代码采用、0新增软件测试或匹配Native，不授B_delta。Owner继续接管迁移，不以建议文本替代实现。

累计through725：725逻辑／672完整流（含历史一次严格JSON拒绝）／50length／3transport／755HTTP／30extra，新峰1；Nov14维护成功缓存复用，OpenCode原生0、未知成本null。沙箱兼容修正版及其冷验属于[独立记录](baiqi-stageA-sandbox-correction.md)，不是725产出。
