# 152中止90档冷读与建城许可诊断

2026-11-16，机器`BF-202609141645`，Asia/Shanghai；接续[交接](../handoff-2026-11-16.md)。普通152产品源码未改，119个安装文件匹配源码和安装清单，既有保护档全部复核。新增结果不覆盖B_plan最大76ms的FAIL，也不授B_turn／N_req或旧8650807恢复通过。

## 实机冷读

新鲜后台只读确认当前Steam实例offline后，启动独立普通152实例PID14616／birth1794764106.4807303，CPU1—8；只载入一次原中止90档，原SHA256仍为`a5c25a5a568fbcaa54b3505af402ef855c5f16666150aa9f3c78867b29f7e044`。当前加载日志就绪后，向自有窗口发送一次Continue的Esc键对；没有END90、人工文职／生产／研究操作或后台军令。

后台自行记录`settler_intent_restored`及一次`entrusted_standby`的SKIP_TURN；随后独立只读取得：

| 项目 | 当前读值 |
| --- | --- |
| 移民4390940 | `(16,18)`、2行动、owner0、未死亡／未延迟死亡 |
| 建城记录 | ARMED、token`settle:0:1`、requestID`0:90:50`、turn90、plot808、empty=true、conflictingCity=false |
| 行军计划 | READY、plot808、`(16,18)`，与当前落点一致 |
| 原生状态 | HOLD=75236491；ReadyToSelect／ReadyToMove=false，HasPendingOperations=false，QueuedDestination=nil |
| 回合门 | blocking=0=NO_ENDTURN_BLOCKING；单位／城防检查false，HasSentTurnComplete=false，本地active，busy／processing=false |
| 私有状态 | 游戏debug=nil，不能用getupvalue读取旧实例闭包或证明其曾进入writer |

这是重载后由BACKGROUND待命的窄实效。新演员在本分支自己持有ARMED记录；不能与另一分支8650807混淆，不能倒推原失败瞬间的活动状态或原因。没有重发FOUND、清理记录或判定建城结果。

另存`Baiqi_P6_20261116_V152_ColdArmedHold90.Civ6Save`，513008字节，SHA256`4579dae0d8449de3a76257a9043bd97e0515a2dc0a94d11e4a5cdc55e7efd67d`。官方退出一次后仍有自有残留；超过218秒、全部窗口／监听0、两秒CPU不变后，仅terminate一次，未kill升级，不冒称自然退出。原210、原中止90及其他保护档不覆盖，Steam0上线／上传。

## 下一测点与工具

当前`pending.dispatch`仅在新鲜Commit ACK后建立；未进入writer前可重检同一许可。它存在时待命入口明确拒绝；现有用例要求瞬时拒绝恢复后仍能且只能提交一次。因此不能靠超时清除许可／ARMED或直接代做待命来解堵。冷读没有旧闭包，原实例实际遇到哪一门仍UNKNOWN。

[私有构建器](../../tools/build_found_dispatch_diagnostic.py)和[纯Lua记录器](../../tools/lua/diagnostic_found_dispatch.lua)只在新私有目录复制119文件，修改Controller声明及dispatch分支，并可逐字节逆还原。每次dispatch记录一个结果、当前／许可回合、演员／请求号、资格错误和writer进入／异常，保留最后32条及total／dropped。Snapshot返回标量副本；不新增原生getter／桥接调用，不改原调用实参、短路求值或许可，不包装全局Native绑定。

32条故障环形记录不是性能函数样本，不授冻结性能协议通过。准备包SHA256`c186dfc3b552f20446f0510709552c51cb07a5b143ed56c1470531be621cfaa3`，97Lua双编译、119文件ZIP；本工作包仅准备，尚未安装／实采。后续从原85以新label复现，不能续写quota152或重放其END。

[5项工具检查](../../tests/test_found_dispatch_diagnostic.py)通过，包含23个实际live-dispatch用例分别在Lua5.1／5.3运行，共46个场景；另核false／error／绑定变化／writer throw、环形容量／副本隔离、源逆还原及ZIP字节。首轮Owner测试误调被替换的RunNow而非缓存的原入口，2个error场景失败；修正入口后5项全过，未重放游戏。没有重跑产品完整测试总数。

## 本地模型与原件

878／879均固定三消息、完整stop／DONE、严格JSON对象；每日维护命中本机2026-11-16的OpenCode1.19.5成功缓存。878引文不精确、误称SettlementHeld阻止待命、部分分支解释错误，整稿不采用。其输入未含全部警告／配置模块，不授闭包完整；已供Controller中可反证的错误另计。

879提供完整Controller及实际live-dispatch／receipt夹具；仅采有界复制记录思路，未执行原代码。候选在Bound内多次记initial，可能一次dispatch多条；漏entered／checking短路入口，未区分pcall错误。Owner保留Bound原样并独立实现、编测。0原候选Native执行，产品修复及原捕获因果未证明。

累计879逻辑调用／808完整／68length／3最终传输／910HTTP尝试／30额外；当前0在途，本轮POST峰值1。新增OpenCode原生生成0，缓存tokens、服务并发、完整Owner主动成本和净省时均null。

LOCAL_ONLY原件在`.local-model/resume-20261116/`、两个`model878-*`／`model879-*`目录及`acceptance-p6-20261101/resume152-hold90-save-*`。载入期端点拒绝／超时／重置、Continue就绪前拒绝和原样日志都保留；没有重发载入或Continue。准备清单最初把“模型空闲”放在已知878在途时校验，Owner移除无关的只读清单准入，正式启动仍检查模型空闲；不归产品或模型错误。
