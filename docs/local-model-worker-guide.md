# 本地模型使用指南

更新：2026-10-31。先读[唯一配置](local-model-executor-config.json)和[经验记录](local-model-experience.md)。本文从 CK3 参考项目提炼通用做法，来源见经验记录；机器路径和游戏权限按本项目实际情况处理。

## 连接

| 项目 | 值 |
| --- | --- |
| Base URL | `http://192.168.1.11:8080/v1` |
| 接口 | `POST /chat/completions`，SSE |
| 模型 | `qwen38-coder` |
| 认证 | 不需要；其他兼容客户端强制要求 key 时填 `local` |
| 地址策略 | 不自动回退旧 IP 或 `8000` 端口 |

`tools/local_model.py` 使用 Python 3.10+ 标准库，默认读取仓库内配置，不依赖 CK3 的 D 盘脚本、Java 环境或运行协调器。该局域网服务需要执行机器实际可达。只在排障时查询模型列表，不给每项任务增加探测前置：

```bat
curl --connect-timeout 10 --max-time 30 --fail-with-body --silent --show-error --noproxy 192.168.1.11 http://192.168.1.11:8080/v1/models
```

## 真实任务与请求

先选尚未完成、输入齐全且能独立验收的任务。先让模型给候选，再由负责人审阅、必要编测；不要先写完整实现后让模型复述。

在 `.local-model/` 中准备 UTF-8 任务文件，写清实际问题、输出 JSON 对象约定、当前合同与验收条件。通过 `--source` 提供真实文件正文，而非仅列一个模型无法访问的路径。以下命令仅在任务文件与源码已真实准备好后运行，命令本身不会生成演示请求：

```bat
python tools\local_model.py --task .local-model\task.txt --source tools\local_model.py --source docs\local-model-executor-config.json --output-dir .local-model\task-001 --max-tokens 4000
```

替换为本次任务实际相关文件；每次逻辑任务使用新的输出目录。重复 `--source` 会去重并按路径排序。`--max-tokens` 必须为 `1..16000`，这是工具边界，不是模型能力上限。`--timeout` 默认 900 秒，为 socket I/O 超时，不是整个任务的总时限；可按真实任务调整。

工具固定三消息布局：配置中逐字 system 模板、按确定顺序的当前源码/合同、变化的真实任务/诊断。真实源码变化就正常更新。配置默认值为 temperature 0、`enable_thinking=false`、JSON 对象输出；发出的 `request.json` 才是参数执行事实。

开启 `stream=true` 和 `stream_options.include_usage=true`。工具直接连接本地地址，不继承 HTTP 代理。返回候选不会被执行、写入源码或当作游戏指令提交。

## 并发与分工

- 有完整上下文的独立真实任务直接并行 HTTP，不等待中央封包、ACK 或整波完成；准备下一项、审阅及必要编测与其他 HTTP 重叠。
- 参考项目的 12–16 实际在途是有真实积压时的初始运营目标。按服务 running/waiting、错误、可见 KV 使用、TTFT、总耗时和当前需求调整，不设每岗调用配额。
- 本项目初始化首波只有 3 项真实任务并行；目标不等于实测，更不代表服务容量上限。单进程调用器不自带跨机器调度器；独立任务由执行者并行启动，各用独占输出目录。
- 不重投已完成任务、不发空探针凑数，不让多个执行者无协调地覆盖同一源码。多轮失败后负责人接管该范围，继续让模型承担另一个真正未完成的窄方法。

## 完整性、重试与记录

成功必须同时满足完整 SSE、choice 的 `finish_reason=stop`、`[DONE]`、内容可解析为 JSON 对象；HTTP 200 本身不够。`length`、永久 schema/认证错误、非法 UTF-8/JSON 不盲重试。模型候选中的 API 与语义仍要另外审阅。

配置指定瞬时 HTTP `429/502/503/504`、连接拒绝/重置、超时或不完整流最多尝试 6 次，按 `10/20/40/60/60` 秒加 20% 抖动退避。每次重发完整相同请求，不拼接部分候选。只重试模型 HTTP，绝不重放游戏动作。等待期间推进独立任务。

每个输出目录保存：

- `request.json`：真实完整请求。
- `events.jsonl`：每次 BEGIN/END、UTC 时间和退避事件。
- `attempt-N.headers.json`、`attempt-N.sse`、`attempt-N.content.txt`：每次原件，失败流也保留。
- `attempt-N.result.json` 与 `result.json`：每次与最终传输结果、候选、错误、用量和 `adopted=null`。

分别记录 headers 延迟、首个非空 content delta 的 TTFT、总耗时、服务实际 usage 与缓存 token。headers 时间不等于内容 TTFT；缺失 usage/cache 保持 null，不能用耗时反推命中。客户端 POST 区间不等于服务器实际推理并发。

原件放被忽略的 `.local-model/` 或执行机器自己的外置数据根。共享[经验记录](local-model-experience.md)只记录可公开事实、真实机器 ID、来源、负责人修正、测试和采用范围，不发布密钥、Steam 账号数据、私人存档或第三方游戏资产。

## 采用与能力边界

源码解释、精确 API、实际失败诊断和输出范围越清楚，候选越易验收。只给文件路径、含糊占位符或完整闭环缺口时，不能把模型猜测当成已经实现。服务工具解析器未配置时的 HTTP 400 也不能当成模型推理失败。

HTTP 成功、JSON 完整、源码采用、软件验证、正式提交和游戏效果分别记录。输入 token/文件数量不是实际改写规模。参考项目曾有窄方法成功与跨文件 ABI/运行恢复失败，详见经验记录中的固定提交链接；这些历史结果不构成 Civ6 的功能或性能结论。
