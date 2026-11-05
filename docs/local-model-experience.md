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

## 2026-11-03：240—241数据行Hash解析

240主体加一处负责人类型守卫后采用；241的14条JSON数据原样采用，6项实际模块检查通过、原生只读解析成功。Lua字符串可借元表索引读库字段，所以pcall索引成功不等于提供者满足table／userdata合同；保留这个原稿反例和未知成本。[逐案](research/baiqi-p6-heritage-actions240241-evidence-2026-11-03.json)。

## 2026-11-03：242—243重试与待选文物阶段

242最终完整stop／DONE／合法外层JSON，Lua仍语法失败；243最终传输失败，不能算JSON或模型语义失败。重试按每次POST_BEGIN至ATTEMPT_END计在途，排除退避；截至243为253次HTTP尝试、10次额外重试。负责人7项软件和原生none／零详情查询样本通过，未接入完整自动考古。[逐案与未知成本](research/baiqi-p6-pending-artifact242243-evidence-2026-11-03.json)。

## 2026-11-03：244—245传输失败接管与客户端路由

两任务各6次传输失败无候选，负责人并行实现核心快照／元数据／回执消费者，15项软件通过、原生仅只读绑定。系统代理未绕过配置中的LAN主机，直接同地址models查询返回配置模型；后续只对模型子进程添加NO_PROXY，并保留其他路由。不能据此追认历史重置原因或生成恢复。[逐案、未知成本与下一步](research/baiqi-p6-naturalist-core244245-evidence-2026-11-03.json)。

## 2026-11-06：新日维护与旗帜冷验429

BF-202609141645，canonical CLI在Nov6首个真实POST前检查OpenCode，installed=registry_latest=1.19.5、updated=false；普通HTTP和0新OpenCode原生生成分账。429完整stop/DONE/VALID，但原观察器把函数当计数表、没有持久namespace且丢nil参数，隔离替身首调用拦断转发，拒进Native。owner改后8项诊断资格验证，再做[76旗帜三选冷验](testing/baiqi-garrison-flag-native-76.md)。

Native回执要按上下文分前缀；碰撞应在动作前中止，不覆盖原件。端点脚本退出0仍可能qualified=false，后续门需核语义值。战斗Core先结算、UI在回放中仍旧值，等结束后再两边读回，不能把动画HUD当最终结果；续行计数和全局Native API次数继续分开。缓存tokens、节时和人工成本未知仍null。

## 2026-11-06：430读回与431归因审阅

BF-202609141645，430／431均canonical普通HTTP完整stop/DONE/VALID，复用Nov6成功每日维护，0新OpenCode原生生成。430原读回用#计数字典得0而真实为1、未区分结果缺失／畸形；owner Core／Flag各8资格后才用，实际[城旗UNKNOWN提示与恢复](testing/baiqi-flag-unknown-recovery-76.md)通过窄样本。旧observer和故障资格复用，不重新计功；界面请求、账本余额与底层Native计数分账，加载期间次数未知。

431只采用缺少快照的描述性发现，拒绝单位消失与目标地块状态即可确认消耗的推断；逻辑反例不是实机故障。Index／Hash不可混用。已有农场效果保持通过，不改产品或重放动作。[归因审阅](testing/baiqi-builder-final-charge-attribution-review.md)。截至431逻辑431／完整400／length28／finaltransport3，HTTP461／extra30；432另发候选不在该快照，未知缓存和人工节时null。

## 2026-11-06：432—435正常训练与事件归因

BF-202609141645，四个真实任务均canonical普通HTTP完整stop/DONE/VALID，复用Nov6成功维护；0新OpenCode原生生成。432原读回端口／集合形状拒用，owner真实Religion端口修正后Core/UI各6例；433原观察器跨命令局部变量失效、元数据不受保护，owner8例，Native读取table.unpack缺失后仅改标量读出并做3例，事件未丢；434原候选捏造总督状态、把food余额当surplus／175生产成本当人口成本，拒用，owner5例和实际规则／晋升读回。435只采用解读分阶段结构，修正扣人口发生125而非121—124、单位Index与队列概念及禁止功能，不照搬混杂术语。

[76正常训练实机](testing/baiqi-natural-settler-training-76.md)证明175训练与新演员，人口10→9→10，重复9通知不是扣两次，净值不等成本。模型HTTP、诊断资格、软件基线和Native作用域继续分账；已有7例路线观察器只复用不重计。本包截至435逻辑435／完整404／length28／finaltransport3，HTTP465／extra30；未知缓存tokens和人工节时null。

## 2026-11-06：436—437首路占格漏试替代

BF-202609141645，436原诊断引用不可见lexical函数且只定义不执行，拒Native；owner只读证实776全路安全但next有ownbuilder6291501，846安全且next空。77采用437经审阅的一项PathStep条件，把builder规划占格检查用于settler，沿用more继续搜索；不改派发复核。437测试语法混杂／withCityfalse即本地建城且期待远程FOUND，0采用；owner6例在76有2FAIL、77全过，1064全套通过。软件不能关闭[实际扩张FAIL](testing/baiqi-settler-occupied-route-77.md)，冷验继续。NativeCanStarttrue仍会被模组占格门正确拦住，不替代完整合法性。

436／437均canonical stop/DONE/VALID、同日成功缓存、0新OpenCode原生生成；截至437逻辑437／完整406／length28／finaltransport3，HTTP467／extra30。未知缓存、人工成本和节时null。诊断快照不是派发授权，不搬阻挡者制造通过。
