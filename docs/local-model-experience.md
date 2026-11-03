# Civ6 本地模型经验入口

2026-11-02按用户要求迁入 [local-model-operations](https://github.com/XenoAmess/local-model-operations)。通用规范、能力记录和经验以后在该仓库持续维护；本项目保留游戏相关证据与业务接入，不重复维护共享传输实现和连接配置。

- [Civ6经验整理](https://github.com/XenoAmess/local-model-operations/blob/main/docs/civ6-experience-2026-11-02.md)：真实控件/调用者、跨上下文API与原生类型、身份复用、未知动作不重放、事件字段、零次数创作及诊断清理。
- [三份精确历史快照及哈希](https://github.com/XenoAmess/local-model-operations/blob/c652acd43805d6b0df333238278cc9ea870a485d/docs/history/civ6-2026-11-02/README.md)：原指南、原配置和完整经验原文，来自本项目76a41d8d2c23806a20a4d98aa3ba251d598f054b Git blob。正文和相对链接未改，历史链接在原项目固定提交解释。
- [迁移及新3项真实请求摘要](https://github.com/XenoAmess/local-model-operations/blob/main/docs/evidence/2026-11-02-civ6-migration.json)、[HTTP能力案例](https://github.com/XenoAmess/local-model-operations/blob/main/docs/capability-http.md)、[OpenCode能力案例](https://github.com/XenoAmess/local-model-operations/blob/main/docs/capability-opencode.md)：分别记录模式、错误、采用、必要验证和未知成本。
- [本项目调用指南](local-model-worker-guide.md)、[接入清单](local-model-executor-config.json)及[游戏验收记录](testing/results/2026-11-01-p6-acceptance.md)。

历史P6截止129次HTTP、124完整、5次length整丢弃、0传输重试，客户端历史峰13持续时间未知；不是模型交付成功率。此前没有共享每日维护，不能追认。迁移新增130–132实际通过共享CLI完成3个真实任务，均stop/DONE/合法JSON对象、0重试，峰3及持续时间见共享摘要。130适配架构、132测试边界部分分析参考；131分类参考，错误事实由owner重读公开证据改写，生产代码原样采用0。OpenCode只参与维护，本轮不是opencode-native生成。

本机BF-202609141645的2026-11-02维护复用同机同用户缓存，记录版本1.19.5；cached updated=true属于此前维护，本次没有执行升级。后续实际适配测试与正式采用在共享仓库追加后到回执，不回写冻结阶段。项目42版333项软件检查与原生复核分开，迁移时原生42仍待验证。新经验更新共享案例并精确链接本项目发布证据，不上传私人存档、账号、模型原件或游戏资产。

适配器实际验证：14项边界测试通过（0.492秒），包含真实共享prepare_request构造消费者、真实CLI维护失败先于dispatch，以及模拟75不重试、配置即时更新、路径空格、证据防覆盖和JSON完整性。原8项内部HTTP/SSE测试随重复实现退出，本次不是新增14项游戏测试，也未重跑已绿游戏模块。UTF-8/LF、28需求/40用例双向追溯及241条本地链接通过。

随后adapter-review133通过新的Civ6入口审阅刚写出的实际实现：1 POST、200/stop/DONE、合法JSON对象，7.649869秒，prompt13880/completion826，cached=null。其三项发现全部拒绝：误称未维护（真实共享CLI先client_preflight再dispatch）、误读已委托的原子claim及错误处理、否定已明确的Civ6提示覆盖并给半截语义说明。代码采用0，不因传输完整授审计正确。该任务实际共享提交c652acd，原件和ADAPTER-PROVENANCE只留忽略目录，待共享后到回执追加；本次共享入口迁移累计4 POST、4完整、0重试，历史P6统计不回写。

## 2026-11-03：238—239特殊文职候选查询

两次普通HTTP完整stop／DONE／JSON、峰2、0重试。两个候选均0原样采用；负责人7项实际模块检查通过，原生仅空公园集合样本，未接入运行托管。不能把操作名称当作存在的枚举成员，也不能把Lua局部变量在Python当全局读取。[采用、成本未知与Native限制](research/baiqi-p6-heritage-candidates238239-evidence-2026-11-03.json)；共享经验另加精确提交反链。
