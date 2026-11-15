# 152匹配配对包只读复核

2026-11-16，BF-202609141645。接续[B_turn／N_req实采](baiqi-source152-stageB-identity-fixed.md)，下一项为当前版本的匹配B_delta。

[只读核验器](../../tools/verify_paired_artifact.py)重新读取当前152源码、已有启用／对照副本及ZIP：各119文件，源码／目标／归档字节、mode、普通END桥、激活入口与Lua5.1构建标记匹配。既有包SHA256仍为启用`31ad0999f79dd7cc692af18349d8deca4270b8120073a9d7d51fb21116bacf88`、对照`b3cfb74bbd2852b446c52cf973cb1ea173fd0b23580dec7009aece505c137bea`；相同计时前缀`c80f6c48367aedd22c88f6a7e4398958d0a2c0a0a3c0d66e99c3ea063b454e6d`与渲染结束桥`d4ca8dddefde8932680a17c1fa2bb5f5093ce0d1c73994c79fa4bd547b1e1e30`保持。

不仅核清单：启用唯一变更与对照12文件分别逐字节匹配当前规范变换；即使修改错误内容后重算目标／ZIP哈希，也不能绕过实际前缀、激活别名和静态关闭代码检查。ZIP重复条目拒绝，布尔标记必须为true。此工具无写文件、构建、安装、子进程或游戏动作；运行负责人仍须取得新鲜离线确认、保护存档、准入互斥和校验实际实例。

[5项测试](../../tests/test_verify_paired_artifact.py)通过：真实两包的只读字节不变、对照代码／前缀伪造、错误标记／variant／当前helper SHA、归档损坏与重复项。实际旧包再次只读通过，未因HTTP计数器修复重建无关配对包。现有152 B_delta仍是0个实测配对；准备／核验不授性能通过。

模型881完整stop／DONE／严格JSON，12851+1430tokens，10207.8988ms／TTFT1847.5757ms；仅部分采用。其manifest／哈希／ZIP及启用逆变换框架有效，但control未检查实际前缀和静态关闭正文、依赖当前工作目录找helper、标记仅truthy且ZIP集合忽略重复。Owner改为复用规范transform逐字节核全部变更，固定工具自身ROOT及严格标记／归档条目，并完成上述正负检查。没有执行原候选或Native动作；AST独核其换行anchor正确，不错报字符串转义问题。

每日维护命中本机Nov16 OpenCode1.19.5缓存；881只在quota152r正式释放后派发。累计881逻辑／810完整／68length／3最终传输／912HTTP尝试／30额外，0在途，新增OpenCode原生生成0；未知缓存tokens、服务并发、完整Owner成本及净省时null。原件LOCAL_ONLY：`.local-model/model881-paired152-preflight/`、`.local-model/resume-20261116/pair881-*`。
