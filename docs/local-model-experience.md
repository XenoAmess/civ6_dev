# 本地模型经验与采用记录

更新：2026-10-31。执行机器 ID：`BF-202609141645`。使用方法见[指南](local-model-worker-guide.md)，参数见[配置](local-model-executor-config.json)。

## 参考项目来源

首次参考前已将 `../ck3_eternal_recurrence` 快进更新至远端 `master`，两者 HEAD 均为 `70bb3de383adf0547bac8af0c487387d9da63160`，工作区干净。以下链接固定该提交，便于跨机器复核：

- [AGENTS.md](https://github.com/XenoAmess/ck3_eternal_recurrence/blob/70bb3de383adf0547bac8af0c487387d9da63160/AGENTS.md)：工作包完成即 commit/push、线性历史和本地模型优先。
- [模型配置](https://github.com/XenoAmess/ck3_eternal_recurrence/blob/70bb3de383adf0547bac8af0c487387d9da63160/docs/local-model-executor-config.json)：连接、默认参数、三消息布局、重试策略。
- [跨机器指南](https://github.com/XenoAmess/ck3_eternal_recurrence/blob/70bb3de383adf0547bac8af0c487387d9da63160/docs/local-model-worker-guide.md)：实际派发、流式完整性与采用边界。
- [可行性记录](https://github.com/XenoAmess/ck3_eternal_recurrence/blob/70bb3de383adf0547bac8af0c487387d9da63160/docs/local-model-executor-feasibility-2026-10-28.md)和[能力边界](https://github.com/XenoAmess/ck3_eternal_recurrence/blob/70bb3de383adf0547bac8af0c487387d9da63160/docs/local-model-capability-boundary-2026-10-28.md)：历史实验与负责人修正成本。

本项目保留连接 `192.168.1.11:8080/v1`、`qwen38-coder`、无需密钥、默认参数及瞬时错误重试策略；system 模板改为项目中立的工程协作提示。原 CK3 的 Java 迁移、D 盘调用器、任务总线、机器 ID、Game PID 和运行权限均不继承。许可证文本随适配资料保留于根目录。

## 可复用的历史经验

- 当前源码、实际 API、生产者/消费者和精确诊断比仅给文件路径更有用；完整上下文不代表模型已自主实现所有输入文件。
- 模型曾能提出可用的窄方法或局部合同修改；完整 ABI、跨文件恢复图仍可能需要负责人接管。成功与失败只能支持对应任务条件下的分工判断。
- 先让模型实现真实待办，审阅期间继续派其他独立任务；不为刷数量重发已完成实现。
- 实际 `request.json` 决定参数是否发送；请求 thinking 开关不证明服务实际内部模式。不能根据耗时推断缓存命中。
- 半截 SSE、输出 length、接口缺 tool parser、候选逻辑错误分别记录；不把传输错误计作模型推理能力上限。

这些均来自上述 CK3 固定版本资料，不是本项目已取得的 Civ6 运行、性能或玩法验证。

## 本项目初始化实测

2026-10-31 UTC `04:34:01` 起，先并行发出 3 项真实任务；之后 2 项纠错请求并行，再单独派一个窄解析函数。最终通过本项目新调用器发出第 7 项真实文档任务。

总计 **7 次实际 HTTP 请求**，无自动传输重试；本次客户端实际在途峰值 **3**。配置的 12–16 是有真实积压时的运营目标，未声称本次达到，也不据此推断服务上限。

| 请求标识 | 传输结果 | 审阅与采用 |
| --- | --- | --- |
| `agents` | HTTP 200，`finish_reason=length` | 截断，拒绝；没有自动盲重试，改为更窄请求 |
| `guide` | 完整 stop/SSE/JSON | 复述 CK3 原文，含旧机器事实与链接；拒绝直接采用，负责人改写项目指南 |
| `caller` | 完整 stop/SSE/JSON | finish_reason 层级错误、缺 DONE 校验、吞解析异常及缺记录，拒绝 |
| `agents-narrow` | 完整 stop/SSE/JSON | 部分结构采用；负责人移除任务回显、模型自行添加的永久多 Agent 禁令和语言约束，并重写细则 |
| `caller-correct` | 完整 stop/SSE/JSON | 仍吞异常、无 DONE 状态、替换非法 UTF-8、配置根路径错误且 headers 当 TTFT；拒绝，负责人实现传输与 CLI |
| `sse-parser` | 完整 stop/SSE/JSON | 部分采用事件累积和字段拆分；负责人修正 `all()` 提前耗尽迭代器、无冒号 data 字段与严格解码 |
| `experience-draft` | 完整 stop/SSE/JSON | 部分采用表格与分段；负责人修正相对链接、证据目录、重试范围，并补实测第 7 轮回执 |

两次完整调用器候选都未达到合同，所以缩小模型任务并由负责人接管整段；没有将负责人完成的实现再交模型复述来追认采用。

### 新调用器的真实服务验证

`experience-draft` 使用已写入仓库的 `tools/local_model.py`，输入是当前规则、配置、指南及真实前六轮回执，任务为尚未完成的本页初稿。

| 指标 | 实际值 |
| --- | --- |
| HTTP 开始 | `2026-10-31T04:41:24.614815+00:00` |
| HTTP 状态 / finish / DONE | `200 / stop / true` |
| headers 延迟 | `1986.288 ms` |
| 首非空 content TTFT | `2204.367 ms` |
| 总耗时 | `11043.188 ms` |
| prompt / completion / total tokens | `5638 / 1321 / 6959` |
| cached tokens | 未报告，`null` |

这些只证明本次配置与调用器完成了一个真实生成请求，不证明生成内容可直接采用、所有异常场景已在线出现或任何游戏功能已经完成。

## 必要验证及负责人错误

`python -m unittest discover -s tests -v` 最终 **8 项测试方法通过**。用本地 HTTP 测试服务覆盖完整 SSE、一次性迭代器、多行 data、严格 UTF-8、截断重试不拼接、503 与 401、length/非法候选不重试、记录字段、三消息与参数透传、输出目录防覆盖。

首轮为 7 通过、1 失败：负责人测试错误地要求非法 UTF-8 首行失败后仍保存尚未读取的后续空行。修正测试为核对实际读取的原件前缀；没有因此改动产品代码。这不是模型源码缺陷，也不将测试修改计作模型纠错成功。

## 原件与后续记录

本机完整原件在 `.local-model/bootstrap/<请求标识>/`；第 7 项在 `.local-model/experience-draft/`，前六轮汇总为 `.local-model/bootstrap-notes.json`。这些路径已被 Git 忽略，仅表示本机现场，不要求其他机器先取得原件才能调用服务。

后续记录真实任务、当前输入范围、实际参数、各轮失败、负责人提示与修正、必要验证、最终采用范围。客户端峰值、服务端推理数、累计请求、正式提交与游戏实际效果分别记录；缺失值保持未知。
