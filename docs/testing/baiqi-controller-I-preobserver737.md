# I未重现尖峰与显式v2覆盖／737

2026-11-14，BF-202609141645。[实机、原值与软件证据](../research/baiqi-controller-I-preobserver737-2026-11-14.json)。H超时后在同一已预热实例、同一v1细分包重新正式载入原85。普通END85—89到90／11城，原版Escape测试玩家回调恰一次返回，2.110秒后独立读到外交隐藏及实际88。H失败不追改，I独立65根／190行通过父子区间和计数核对，0错误／丢弃／坏时钟。

本轮未重现G／F尖峰：根最大约12ms、ProcessSettler约8ms、SettlementSites／KnownExpansionSupport约3ms、PathStep／Safe／RequestCivilian约1ms。没有产品源码优化，不能称提速或修复；未观测调用数量、具体未重现原因、缓存命中均未知，不根据耗时推缓存。v1明确跳过自身Native通知观察之前的active入口，这是已知覆盖边界；不能断言I确实在那里丢了哪次尖峰。

I90已存518799字节，SHA256 `8e63dc77df22787f513ad1220e530d8c51f793d10a5bd2555b52121d7526a5d4`；七绑定／自有监听撤下，原版退出一次，自有进程已消失。正式F最大90ms的B_plan FAIL保持，I两个窗口、65根也不构成正式采样达标。

下一包显式升诊断source为`baiqi140-controller-children-v2`：保留全部active88／89、尚未看到自身通知的入口，再继续保留通知后原十秒窗的入口，完整尾部不截断。按最后实际观察锚点将完整区间列为通知前／跨通知／通知后，不伪造事件或补旧行。仍只有一个4096池，六个内部目标及游戏正文保持；它是诊断覆盖扩展，不能授正式B_plan。旧v1默认生成的粗／细两份Controller字节与冻结G／H包精确一致。

737完整predicate函数体原样采用，8个实际canonical constructor／profile合同检查全部通过：早期true／false／nil调用保留且不造anchor、已知窗口截止、时钟／锚点／城市／active／player未知均由原工厂保护，不阻断原函数。3新／9相关构建方法通过，全97Lua51／53、119文件包已准备，SHA256 `8710ca0194fb6faf4e34d1eb6165749d2370e21b1a0ccc7096e6ad79833486a9`；新Native尚未执行。范围方向为Owner事前合同，不记模型独立发现未捕获尖峰。

737单attempt／stop／DONE／合法JSON：5186总tokens（188输出），1898.0289ms／TTFT818.0491ms。累计737／684完整流（含历史严格JSON拒绝）／50length／3最终transport／767HTTP／30extra，本次峰1；维护成功缓存复用、OpenCode原生0、未知成本null。继续新冷实例诊断，匹配B_delta和完整验收仍开放。
