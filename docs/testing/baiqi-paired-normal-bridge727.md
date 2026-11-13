# 匹配对照普通END计时桥／727软件

2026-11-14，BF-202609141645。[软件、候选审阅与两包哈希](../research/baiqi-paired-normal-bridge727-2026-11-14.json)。这是[725普通END迁移](baiqi-paired-normal-contract725.md)的组件实现：秒表仍在BaiqiExecutor时钟域，未来测试玩家在ActionPanel完成原版军事SKIP及新鲜许可后，立即调用自有桥Begin，再发送不带UserForced的原版END。桥自身只操作QA计时器，不发送游戏动作，不补写内政／授权标记。

仅明确source140的新`--normal-end-bridge`选项发布固定自有桥：要求现有READY保留、normal_end=true、source_version=140、正确token／当前回合／本地0、原秒表身份及精确既有记录数。调用秒表前独立保留该回合尝试，异常／后验未知不可重试；不覆盖外来桥，身份被换或退休后的缓存入口拒绝。读取／后验／清理异常受保护，不修改Stage来制造资格。

同包在实际Activate入口先停表、再执行原回调，以避免把先执行的规划耗时混入停表之前；Add／Shutdown Remove同别名，游戏回调参数／nil返回保持。启用与静态对照前缀逐字相同，旧默认构建接口保留。97Lua51／53、119文件的两个新候选包已准备，尚未安装。普通callback驱动、跨UI上下文调用及控制组原版END门仍待真实验证，元数据明确driver_ready与Native验证false。

7桥、3新真实配对构建、3旧配对构建、9 canonical秒表，共22个不同方法通过。软件涵盖真实canonical clock五段、准备停留不计入秒表、合法READY不被改写、异常后不恢复／不重试、外来身份及退休缓存、两包相同前缀和逆序派发下回调前停表。尚未取得五组25段匹配Native，不授B_delta或完整性能PASS。

727完整6359tokens／5927.2550ms／TTFT880.2418ms，单次stop／DONE／合法JSON。6探针中5失败：把合法ends[turn]=true反向拒绝、自行补normal_end／版本、getter异常逃逸、外来发布仍active、缓存入口未校验身份；保留外来项的退休检查通过。0原代码采用，Owner重写并接入实际私有构建器；不把候选完整或Lua版本相同当作Civ6跨上下文实效。

累计through727：727逻辑／674完整流（含历史一次严格JSON拒绝）／50length／3transport／757HTTP／30extra，新峰1。Nov14维护成功缓存复用，OpenCode原生0、未知成本null。当前独立Stage A冷测继续，B_plan与普通匹配驱动仍未完成，预算不降低。
