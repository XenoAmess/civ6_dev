# 普通END配对驱动／731软件验证

2026-11-14，BF-202609141645。`run_paired_acceptance.run` 默认要求测试玩家的 `request_normal_end(turn,token)` 回调。驱动先写独占动作凭证，再在Native中验证140、既有时钟和计时桥，保留READY；回调在完成普通军队准备后，须紧接原版无参数END调用前启动桥。返回凭证严格为turn、token、requested=true、forced=false。随后独立读回pending或已完成的原生时钟记录，实际换回合仍由原生激活事件证明。

旧UserForced路径只在显式`legacy_forced=True`时可用，结果明确标记LEGACY_USER_FORCED；未验证产品版本保持null，不再硬填67。正常结果明确source140／ORDINARY_CALLBACK。未知READY、发行回执、外交关闭或动作后断线均不重发；只读轮询可重连。桥和时钟的退出回执分别记录，桥退出未知不能由时钟退出成功替代。修正了Owner迁移时普通字符串中多余一层Lua表括号，并用真实单位baseline读回覆盖。

8个新软件方法及9个显式旧模式方法通过。使用实际canonical Lua时钟和140桥，确认每次5秒测试玩家准备不计入五段各2秒，85—89各END一次、无END90；覆盖动作后OSError、畸形凭证、READY执行后ACK丢失、漏桥、END后外交、只读故障和未知关闭。ActionPanel到Executor的映射仅是软件夹具，不证明真实跨UI调用或引擎接受。

731单次完整stop／DONE／合法JSON，11625总tokens（686输出），5782.6554ms、TTFT1941.3602ms。原样两方法运行产生1失败、1错误：第一项在85直接读取不存在的record[0]，没有准备、Begin或END；第二项未发动作就抛异常，且期待未约定的RuntimeError转换。候选0语义代码采用；夹具搭建方向和API来自Owner事前完整合同，不能算候选独立发现。原件不改，实际仓库tests命名空间仅用于隔离第三方同名包。

累计through731：731逻辑／678完整流（含历史一次严格JSON拒绝）／50length／3最终transport／761HTTP／30extra，本次峰1。Nov14 OpenCode1.19.5成功缓存复用，原生生成会话0；缓存tokens、Owner主动成本、净节省保持null。仍需真实跨UI计时起点、原版普通END和五组25段匹配实机证据；本包不授B_delta、B_plan或整例通过。此前构建产物的driver_ready=false保留其准备时点含义。
