# 138批内工作账本：软件通过，待性能复测

2026-11-14，BF-202609141645。[逐项证据](../research/baiqi-p6-source138-working-journal705-2026-11-14.json)，接[137实机未提速](baiqi-native137-cold333-batch.md)。138只在原始Inspect未被替换时使用批内工作账本：首次加载后逐项保留token与未决观察；ARM／TRANSFERRED可能持久化前仍核新鲜所有者／上下文，Observe与Persist原检查保持。返回READY前必须重新读取真实完整账本并逐字段相等、所有者／回合／绑定再核；变动、未知或回执写入未确认整批拒绝，不跨回调缓存。显式替换Inspect时保留137逐项回退路径，独立Inspect／Prepare及UI最终发令门不改。

6新方法通过：三城市只读批次实际两次属性读、下一调用再次读而非缓存；末读出现旧ARM整批无返回／0发令；读异常、损坏、回合／人类／方法变化拒绝；已观察的新克隆账本继续传递并核真；回执已写但读回异常不授结果；观察前所有者改变0写。既有66项相关回归保持。全2014项中2013通过、1SDK环境条件跳过，118.794秒；97Lua51／119包逐字核验，既有sqlite ResourceWarning不隐去。尚未实机或证明性能达标。

705完整stop/DONE／严格JSON，15329+1335=16664tokens、10200.1122ms／TTFT2170.9259ms。整稿0代码采用：丢Owner返回的key却用未声明global key读取，真实旧ARM的隔离见证错报OPEN；canonical判据只是inspect==bridge.Inspect自比，替换读者的隔离见证READY且调用0次，回退分支被绕开。Observe返回克隆也被称原地修改。批内工作账本／最终freshEqual已由Owner在请求中指定，不冒称模型独立发现。Owner单独捕获canonical引用并修正key与新鲜边界。

累计705／654完整流48length3transport735HTTP30extra，Nov14维护cache复用、OpenCode原生0、未知成本null。137已保存333，正式退出请求一次；继续残留核验（如需要）、新鲜离线冷装138及同原333实机复测。Steam0上线／上传，工坊82；137的Admin约30ms负结果保留。
