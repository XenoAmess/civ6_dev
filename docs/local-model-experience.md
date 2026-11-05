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

## 2026-11-06：438—439同演员实机闭环与下一缺口

BF-202609141645，438模型UI片段缺Read/heads/sr，未区分exactIDalias/offworld/Delayed，0rawNative。owner每上下文6身份分类用例后实际读出137Core exactoffworldDelayed、UIabsent，关联同actorFOUND与新city917516；138双absent。7项已有observer资格复用不新增独立case。77冷装87一致、正常127..137、一个FOUND、13城、正式重载保持和138原版粮仓3/32，关闭[首路占格实机FAIL](testing/baiqi-natural-settler-founded-77.md)，但训练76/移动77，其他TC015矩阵仍部分。134队列式ACK不能替代到达证明；134原生队列732留存，不清除重发。只读parser列错修owner，不记产品FAIL；未知冷启SDK量保持null。

439建议再跑同build训练全链，owner拒为优先项；无primary的“既有弓箭手/骑兵训练上限”不授验。保留TC007实际军队/队列/预算/资源资格盘点，TC009特有区域需先核文明替代、无者条件N/A。两canonical stop/DONE/VALID、同日维护缓存、0新OpenCode原生生成，0rawNative/product。截至439逻辑439/完整408/length28/finaltransport3，HTTP469/extra30，未知缓存和人工节时null；后续440不混入此切点。

## 2026-11-06：440—444实际军队资格、承诺与费用

BF-202609141645，[77两支军队真实后台入队及143进度](testing/baiqi-military-production-77.md)。440原nilrow括号错、无64队列界，owner7身份／角色检查后Native24healthy/13citycap26。441原Identity未定义／无Units界，owner扫144defs/123military*3city*2flags实际738CanProduce查询，发现当代可生产；7旧probe全false不构成功能FAIL。旧私有说明504max算术错，实际硬界256*3*2=1536，公共记录纠正。

442原noncivilian在CivilianType=true时累加语义反了，0rawNative；owner9callthrough／分类／溢出／原异常／foreigncleanup例通过，事件沿用433v2/v3八项资格、0新增独立计数。443原先读迷雾单位、漏ownterritory/fullID并printtable，拒用；owner只读安全已探明路径，TEST_PLAYER三普通军队move逐个实际settled，0civilian命令，0BACKGROUND军令。selector139and语法失败0执行、wheel缺方法0wheel均保留原件并新唯一尝试，不算产品FAIL。

444原队列／国库方法漏self软件反例拒用，ownerNative原生ResourceCost按Index、BaseMaintenance按Hash，FIELD_CANNON0/5/165、LINE_INFANTRY10硝石/5/180。25→18与扣10加3相符，煤下降不归炮兵；军费28未变，建筑区域支出另记。出生／实际军费仍未授验，HTTP和观察器安装不冒充效果。

五次canonical stop/DONE/VALID，复用Nov6成功维护缓存，0新OpenCode原生生成，0rawNative/product。累计through444逻辑444/完整413/length28/finaltransport3，HTTP474/extra30；未知缓存、人工成本与节时null。未复跑已通过1064产品检查；代码未变，实际验收继续。

## 2026-11-06：445—446新军队身份、政策过时与费用层级

BF-202609141645，[两支真实出生／控制／军费／读档](testing/baiqi-military-born-control-77.md)。445raw在后续chunk用select(...),没读取持久r.args，软件missing_event_id反例拒Native；owner6动态fullID分类及empty/absent测试后，实际146full8192051/row58、147full8257581/row94分别对应birthXY与本城Completed canceledfalse。完整ID与行号分离，不按同turn就join。UI保留4/3原生动作，TEST_PLAYER炮8,10→9,10实际settled；连续Executor177calls military0，恢复148动作7。最后清两observer与3handlers/临时QA命名空间后save，正式146政策对照和恢复148hash核。bootstrapcalls未知，0不追授。

446raw发明GetPolicies Members、nilrow括号错、无256界、printtable，拒用；owner按真实Admin GetNumPolicySlots/GetSlotPolicy读。146slot征兵/未过时，25军名义49/paid17/实际32；147征兵过时不在槽，26军名义54/实际54。Native规则每unit减1，17份旧优惠消失加新步5解释22增量，不归单兵22。Native总费提示148Unit54+City56=110，rawBuilding46+District16=62与city56差6在城市汇总层，具体修正未知，不能据残差定间谍。HTTP/代码/Native分别记录；两call完整stop/DONE/VALID、同日缓存、0rawNative/product/新OpenCode生成，累计through446446/415/28/3 HTTP476/extra30，后续447不混入。

13城queued-inclusive26持续141..146，147随后自然14城需求28，14826live+1queued属新缺额。早期148快照在ready后又遇BGbusy且数据未稳，使用late148idle+CoreUI+正式save/load实际一致，不称原子预算。九江原版粮仓146Hastrue/pillagedfalse，148纪念碑16/30，共同新证据；不为凑任务重复生产或恢复删除功能。

## 2026-11-06：447—448低储备独立实机窗口

BF-202609141645，[LowReserve独立138→139窄通过](testing/baiqi-military-low-reserve-77.md)。仅QAfixture扣6516至0.9765625，不算AI消费，普通End后69.75390625<100、24healthyarmy<cap26、FieldCannon双native资格true/cost165/resource0。两个港口项目真完成，连续CityManager2Sewer建筑请求、0unit/0mil、0foreign/unknown/error/overflow，beforecallGold69.753；不是仅看队列。精确清wrapper+3events后副本保存，再restore主148双CoreUI一致，bootstrap次数unknown。

447raw缺V/资源键Niter等错误/假GetCity，错把allunits当army，承诺140不招忽略新增收入、139资源0和fallback立刻born也错；0rawNative，owner改139低gold窗口与141资源候选窗口。448raw先读foreigntreasury且queued=0伪数、只采mil不含合法替代，拒用；owner11透明性/分类/错误转发/foreigncleanup例通过，既有8events复用0新case，全部0rawNative/product。

Core原始单位51、UI50不可混用；首fixture门在BEGIN前拒0扣，实读后新v2一次扣成功，记录不是产品FAIL。Core有Gold/Resource变更函数而UI无，Core无resourceaccumulationgetter；148CoreNiter/Horse/Iron28/31/27对UI25/25/25，差异不解释为同一库存、不能当可互换dispatch资格。此包0资源mutation，资源分支继续。447/448canonical stop/DONE/VALID、同日缓存、0新OpenCode生成，累计through448448/417/28/3 HTTP478/extra30；449独立下一任务另记，未知缓存与人工节时null。
