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

## 2026-11-06：449真实资源短缺与恢复窗口

BF-202609141645，[独立资源138→142](testing/baiqi-military-resource-shortage-77.md)。CoreIndex44先一次-1资格28→27/all54onlyNiter，再不同意图一次-27→0，其他资产计数保持，明确QAfixture非AI收益。NativeUI硝石0/3/6/9/12，141beforecall9<line10/visibletrue/fullfalse，actualCuirassier0/165/铁quote10，142linefulltrue原Cui51/165保持。完整CityManager8BUILD/4unit/2mil/0Line，0foreign/unknown/errors/resourceReadErrors/overflow；events138..141仅9record，重复社区完成通知2不算2资产，不授142events。清exactwrapper/3events，独立142save后restore主148双CoreUI一致。CoreIron27→17与10匹配，UI25→17不同上下文/回合不可独立精确扣费结论。

449raw把马25/铁27库存写成Index，未接入wrapper、漏quote、误把fullfalse单独判资源、虚构32城界限，0rawNative/product。owner14观察透明性/资源错误未知/原调用保真例通过，events8旧例复用0新credit。139首End只ACK不换回合，实际idle且5旧伟人SKIPfalse/noqueued后新普通End进亚历山大对话；141WorldCongress普通物理投票，0UserForced/手动内政。过期参考点击和过早Continue均0input，不误报产品FAIL。累计through449449/418/28/3 HTTP479/extra30；450区域盘点候选独立另记，未知人工时间/缓存/节省null。

## 2026-11-06：450区域容量与前置只读盘点

BF-202609141645，[14城252条Native盘点](testing/baiqi-district-capacity-inventory-77.md)。实际36defs选18普通非internal/trait/center，0errors/incomplete；邯郸4/4但圣地科技已解锁/geometry10/fullfalse，西安3/7但SpaceportRocketryfalse/geometry4，上海2/3但Harborgeometry0，分别保留条件，不能以fullfalse单独推因。原版CitySupport407/408两capacityAPI实际function且三城核过，Cities.GetPlotPurchaseCity(plot)第一方消费者和Native同城读回0error；两个plotinstancegetter实际nil仅读type未call。当前148growth预计不当真实恢复。

450raw未定义visibility、districtRows跨城共享上限、漏full/false/归属/前置、把settlerMinPop挪作区域门和断言无capacityAPI，拒用0rawNative/product；owner绑定实际vis、单次defs缓存、分离32city/256defs/256plotspercity、原版capacity与Tech/Civic资格、ownvisible城市关联。Lua编译是解析检查，Nativeinventory是条件盘点，均不代BACKGROUND行为/完成。累计through450450/419/28/3 HTTP480/extra30；451实际beforecall观察候选独立下一包另记，维护缓存同日复用，未知cache/owner成本/节省null。

## 2026-11-06：451—453容量增长、港口与保护地块

BF-202609141645，[77正常148→160实机](testing/baiqi-district-growth-harbors-77.md)：北京9/3/3→10/3/4、邯郸12/4/4→13/4/5。33BUILD/10unit/3mil/4district，四区域派发前zoned<allowed/dualnative/tech/civic/plotlegal均true，0foreign/unknown/errors/capacityReadErrors/overflow。沈阳Harbor3080237@9,5从1540/177→15582→156152→157complete；邯郸3145774@9,16从1560→158117→159166→160complete，各真实接续Builder。每港口重复通知2，只计同一资产。既有北京新Neighborhood2818089@14,7与旧2621478@14,3分开，前者151104/165→152133→153complete；成都Industrial1638424@8,1从153115/121→154complete。74events0error/drop。清exactwrapper/3events后160保存641388B SHA3495cc9c6cc618f01174b34a7d6f6b364853e20c61f6cecd9e4dd6d85b847bb2，正式load一次/Continue一次，15city/gold7708.4609375/两港口及新社区完成、CoreplotIDs保持，QA不存在。CorecollectionMembers/GetMembers/FindIDnil，首次只读枚举失败0writes，不伪造CoreComplete；实际CoreMapGetDistrictID/type/Owner独立匹配。

451raw缺Read、无界append、非district行读RequiresPopulation、未守visibility/同城/XY等，owner18透明性例后Native。452raw整个复制CityManagerwrapper代只读reader，可能覆盖451binding，整段拒0rawNative；owner有界Native成员fullID/xy/IsComplete，事件行号不是fullID。453raw多变量仅赋一个table、nilcounter加法、errors永0/unknown当空/混geometry与full/fit重复，拒0rawNative；owner12保护/未知例、14city×3types实际盘点0error。成熟城三类陆地候选被改良/feature保护，不能推所有区域0可用；成都53、九江732、长沙907有自然ClearPlot，未拆资产或调用私有规划。成都153学院full1/1负条件真，但工业区当时在建，不能说空队列负分支已隔离；154长4后先Workshop，学院未授完成。

Ready不是全部回合结算原子门，159早段金币/队列旧值，晚段读回7650.3515625/Harbor166后才下结论；不抹早件。151、154先End同回合已知后新普通End，154已有settlerqueue847正常执行，非手动重发文职／UserForced。capacityBlockedRequests仅筛查，已放置续建可能满容量合法，不自动判错。累计through453453/422/28/3 HTTP483/extra30，0rawNative/product/新OpenCode，18+12是工具资格不是1064新增产品项；454净收入真实下一任务另记，成本/cache/人工节省未知null。

## 2026-11-06：454实际净收入负条件与原版外交夹具

BF-202609141645，[77低净收入证据](testing/baiqi-military-low-net-income-77.md)。独立Normal138，TEST_PLAYER原版GUI赠礼68GPT×30、一次实际确认，对方同意；确认后138rawNet仍68.777，不授通过。普通结束实际139后gold6517.75390625/yield148.77734375/total148/unit28/net.77734375，24军队<26且0军队队列，两城FieldCannon双资格true/cost165/resource0。2实际CityManagerBUILD都是HarborProject0/112，0unit/military/lowNetMilitary/foreign/unknown/errors/overflow/financeReadErrors，原项目2个未取消完成事件。Total维护+68是外交义务，不是军队费用；318行维护定义非负，内部承诺未知不用0。3旧军队实际移动、24军事SKIP、正式无REASON结束，0UserForced/手动文职生产/私有规划。

454raw finance缺pcall/unknown/附件字段，privateProcessCity/Planner/pending和直接DealManager建议全拒；Equalize隐藏误读原版消费者，条件没构成不能判产品FAIL。owner18观察器例(11旧+7新)，8事件复用0新增，0rawNative/product/产品修改/1064重跑。截图过期与动画背景ROI拒绝均在输入前；新鲜自有截图核静态控件、金额68、期限30及对方空报价文字mask后保留原60秒检查，确认v1无实际动作、v2唯一确认，不重放未知交易。

清精确wrapper/3events后正式save139600653B SHA05c917451e61e12e75f3b10dd35b8847e52b9eba0d9f9d0dd3d2e6be68f4554d。原main160hash验证正式load一次/Continue一次，15city/gold7708.4609375/net58.90625/两Harbor和新Neighborhood完成、CoreplotIDs保留，QA全nil。454stop/DONE/VALID一次0retry，累计454/423/28/3 HTTP484/extra30，Nov6OpenCode1.19.5成功缓存复用，0新原生生成，未知cache/owner成本/节省null。仅139窗口，不授阈值exact2/100、长期gift或全TC007/013/40；Steam离线0upload/Alpha74未变。

## 2026-11-06：455截断弃用与水上乐园完成

BF-202609141645，[77主线160→165证据](testing/baiqi-water-entertainment-growth-77.md)。模型455一POST200/DONE/length2500tokens，整份丢弃，不读半稿/拼接/采用，不重试同题；owner复用452成员及451透明观察器，有限3city×64/typedfinite编译，18+8旧例复用0新增产品计数。累计455/423/29/3 HTTP485/extra30，Nov6维护缓存复用/0新OpenCode/成本未知null。

Owner初装Citycalls留148guard而160拒绝，后仍在同批继续事件安装和正常turn，违反失败停链；160→161 CitySDK未知，不补0。actual161新guard接入后16BUILD/0unitmil/4district/0foreign/unknown/errors/overflow/capacityReadErrors/满容量筛查hit，四区beforecall有空位/双flag/prereq/XY资格。45events160→165无error/drop。原WuhanWater3342385@8,8：16044/177→16173→162102→163130→164159→165complete，2通知只计1资产，实际后BUILDING_SEAPORT。Chengdu153pop3/1/1学院visibletrue/fullfalse/plot53clear，160161pop4/1/2/dualtrue，Workshop162完成后actualHarbor3407922@6,3 before1/2合法，0/187→16337→16459→16576未完。162放置后nativezoned仍1/2，1632/2，不造立即原子计数，Campus162false原因未隔离。JiujiangIndustry3211311@28,16到16576/177仍未完。新胶东Commercial/长沙Industry/秀容Industry165只入队。

TestPlayer21/20/19/19/19军事SKIP，160和163普通Alex来访再见；161162原版议会一次提交0favor，自选ranged但结果melee，不能混投票和结果；MigrationB目标Alex非本方。161162第一次formalend执行既有queues仍sameactiveidle，freshpending后新普通end，0UserForced/手动文职/clearqueue。早165Ready后又busy，最终idle数据复核。精确restore/3events移除后165save652093B SHA2ae64f7fef8bebe012480c54c2c7857bcb12081b9325545b07b7f9dd2ec67d0c，正式load一次，loading期Continueguard拒0input后actualContinueonce；15cities/gold8008.64453125/Watercomplete+HarborIndustrypending/UI属性和CoreplotIDs保持，bindingsnil。0productchanges/1064重跑/Steamonline/upload，Alpha74未变。

## 2026-11-06：456—459新移民等待与同目标绕行缺口

BF-202609141645，[77实机诊断](testing/baiqi-settler-occupied-detour-gap-77.md)。160沈阳actualBUILD settler index0/dualtrue(既有451sample31)，164新9764928@11,6 type0与455event24UnitAdded、27city131073 order0 row0完成关联、13→12；南京9830465type2是Builder不能认错。165167UI/Core exacthealthy9764928@9,8moves2/nilqueue/formation1。165→167RouteSDK51/targetMOVE0/FOUND0/other2SKIP/others49/0noncivilian/unknown/errors/overflow，CitySDK2BUILD(Builder/ResearchLab)，events2/0error/drop，精确清wrapper/3events后正式save167652585B SHA068e8b9f43abe30edf1636a293411e5a9cfc33fc666e50c5b96ab43da0943f86，15city/gold8214.828125，未人工代文职/挪先知/军队。未授fullTC015。

457实际推荐2：1093@37,24 knownvisible/clearunownedland/距已知城>3；1052feature3保护。实际publicGetMoveToPathEx27points/首尾真/limit48/0hiddenforeignerrors，逐点radius2 visibleprimary+religious0threat/errors，首step404@8,9 ownProphet5111847Civilian/nativeMOVEtrue，模组正确拒占格但无samegoal绕行。6邻居除404均0primarycivilian/NativeMoveTrue，360ownwater@8,8邻接pathsuffix403；不因Native第一步可走便假授全futureedges。source77只改其他goal回退不处理samegoal。ChengduHarbor167108/187与JiujiangIndustry96/177未完，WuhanWatercomplete。

456rawpcallboolindexed/undefinedvisibility/ungatedcity/readiness混legal拒0Native；owner复用6classes×2和1新hiddenguard，V1曾SKIP后又ABSENT，V2只在实际查询可见目标时ABSENT，基线target-1无误授。457rawprivateSafe/Revealed/visibility缺定义/无bounded/城距漏、误禁已供NativePath读拒；ownerpublicNative分段采样。458actualisolatedmockglobalSettlerDetournil（helperdecl后/ctx也未定义），raw排斥unownedwater与文案矛盾、缺Nativefirsthop/rejoin、扩大builder范围；459isolatedglobalo nil/无替代拓扑/无行为断言/Manhattan不证hex，均整拒0rawNative/product。仅参考boundedneighbors/strictprogress设计方向。4×stop/DONE/VALID，458459真实独立实现/回归并行但peakduration未知，累计459/427/29/3 HTTP489/extra30；0产品修改/1064重跑/新OpenCode/Steamupload，未知cache/owner成本/节省null。下一包owner窄修复及回归/78coldNative同167，不以本报告终止。
