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

## 2026-11-06：78负责人绕行修复与460工具消费者

[78软件证据](testing/baiqi-settler-detour-78.md)。仅UNIT_SETTLER/明确civilian_target_occupied触发，原Nativegoal整路探索归属威胁验证保持；已有NeighborhoodGeometry radius1<=7(含center)有限6候选，visible/revealed/own-or-unowned/knownmetadata/Safe/CivilianMoveTarget、严格同goal距离减少及suffix>=3重接线索，真实NativeGetMoveToPathEx到候选恰2节点/原生MOVE true，前后FreshfullID/type/position/unescorted与独立wholeoriginalpath安全刷新，最终RequestCivilian原守卫不变。只授当前首步，未保证全futureedges或所有绕远障碍；builder/GP/naturalist不扩大。

20真实RunNow回归：原77初10正例2FAIL/负8PASS0.133s，owner78初10PASS0.132s，扩20PASS0.296s；源码.patch后大套1084第一次18ERROR均static-control工具版本拒78，原件保留。460canonical一次stop/DONE/VALID0retry，完整给4Python消费者/build_mod，4exact替换经审采用，显式tuple+type(bool拒)保持，独立Lua67..70dump合同未扩大。二次full1084PASS140.522s/outer144.9002197s，实际sourceSHA c0c899efb0804f3d812c24348e5583a3c8353ea34229bd00334888e3e0e4719c；pack87 SHAA2a0bf083cd8ff01637721f95e7e56621d7d0586ced40585d70aaea2d72bdf36。未安装/冷验，不能授Native78或建城通过。model458459raw拒仍0Native/product，owner逻辑非raw采用；4604替换工具采用非游戏Native动作。累计460/428/29/3 HTTP490/extra30，0新OpenCode/未知cache成本节省null。

owned77/18360birth1793907267.1851747在hash核167后正式OnExitGame一次，窗口消失但进程仍清理，不重复退出或盲启动。Steam背景point查询unavailable0input/focus/shot，未认offline，78启动前须fresh proof；0online/upload/Alpha74未变。

## 2026-11-06：461／462与78真实建城、忠诚反例

[78同档实机证据](testing/baiqi-settler-detour-native-78.md)。77自然训练164出生9764928，在78冷载原167占格档后自行走8,8，173一次FOUND建1114127临淄，175普通粮仓1/32与正式重载保持；两个跨版本新区域172Harbor3407922／174Industry3211311完成接续、UI完成＋Coreplot身份＋重复event只计一对象。启动SDK计数未知；后两透明窗口34/6MOVE和180/18MOVE/1FOUND/0noncivilian等限定Executor。城市23BUILD/5unit/2military-production，不把军队生产误作后台军令。events43/0error/drop，精确恢复与reload QA nil。

实际新城不等于mod observed：FOUND0:173:193仍unit_unavailable，未重放。461stop/valid但原稿kindMOVE_TO/operation字符串FOUND_CITY与actualkindFOUND_CITY/numericoperation矛盾，隔离条件false；文字勘误不等于patch已修正，且缺request-before无城、alias与异步资格，整patch拒绝0Native/product。462stop/valid只参考installed原版CulturalIdentity方法；原probe无owner/player/visible/bounds/finite检查且Round全局未验证，owner改成自有fullID/coords/visible-first的有限读取。首次16bound实17有overflow1保持原件，再32bound实际17/0err/0overflow，54/100/-23/3turns。Nearbycitizen-20/happiness-3，不能靠新城和少量产能掩盖长期丢城风险。模组显式忠诚门缺失；Native推荐内部opaque，不断言所有AI逻辑无忠诚考量。

Owner新Core只读probe两次因UI GetUnitType接口错用失败，第一次误判movementmeta后仍failed；随后依既有qualifiedCoreGetType更正，UI/Core175和重载175均PASS。0gamecommands，失败后无依赖写入。Continue加载窗口health/glyph各拒一次0input，后freshglyph才Esc一次。旧77正式退出关窗441.68s残留后hash核167、只终止exactowned18360 once，Steam/othergame0kill，不授干净退出。冷78前fresh只读offline age0.002295s；0online/upload。逻辑累计462/430/29/3，HTTP492/extra30；本包新增461462各1次HTTPstop无retry，0新OpenCode-native/unknowncachecostsnull。

## 2026-11-06：463编译通过仍违反实际回执合同

[78忠诚实际失城](testing/baiqi-new-city-loyalty-loss-78.md)：175→178普通回合后Native忠诚54/31/8，178实际UI/Core自有15，原1114127不在自有清单；当前visible37,24新fullID131072 owner62，配置LEADER_FREE_CITIES/CIVILIZATION_FREE_CITIES。173建立与175生产/重载仍真，长期保城FAIL。没有manGovernor/army/map/citytransfer rescue，不能用前者掩盖后者。178private save685221 SHA0fbb18e834cbcc1b642272635f8c627e0352b55ff7a8f1330f119ff7a412623f；未授178reload。

463canonical一次stop/DONE/VALID0retry，raw3替换exact/fullLua编译成功；isolated actual missingunit+latecity清pending not_observed，以及healthyunit+existingcity竟observed，两反例失败，wholepatch拒0rawNative/product。设计承诺retainmissing但patch仍clear，资格前empty没有writefreshwitness，不能因语法可编译或描述正确授采用。累计463/431/29/3 HTTP493extra30/0newOpenCode/unknownnull。

Owner175cycle实际176后末尾读已删CityCalls断言失败；从清观察器后的消费范围修正，去掉末尾失效audit，只推进下一176/177并实际177/178，不重放175任何动作。无新productcheck必要；0online/upload/Alpha74未变。

## 2026-11-06：负责人79建城回执与完整1108

[79软件修复](testing/baiqi-found-city-receipt-79.md)。463wholepatch拒绝后owner实现FOUND专用memorywitness/receipt，不是raw采用。CanStart与既有latest之后，当前visible/revealed、NativeIsCityfalse＋CityManager.GetCityAt成功nil、own/unowned＋freshSafe，再freshContext/idle/fullunitID/type/CanCivilianunescorted/position。pending存unitID/type/player/index/xy/emptytrue；后rawlookup必须nil且有限512unitinventory无原ID，别名／未知不算消耗；同可见格Nativecitytrue/plotownerown，newcityfullID/xy/owner+ownFindID相符才observed。missing/citylate/moveschange/healthy/foreign/alias/error均retainpending，timeout只一次unresolved不重发，已见foreigncity阻断后capture倒认。仍纯memory、无durablejournal，exactoffworld对象不当absence，只授软件。

原78新15tests9FAIL6PASS0error0.173s；owner15PASS0.845s，23PASS0.252s，final24PASS0.303s；full1108PASS76.529s/outer78.7108701s。无因旧耗时不同声称性能加速。2Python工具显式79+2消费者同步（参考已验证460模式），独立Lua67..70不扩；baseMock只补actualIsCity/GetCityAt。包87 SHA002021932d19871a5d1b69c8ec6cbf06ea6273e168503a4be0de1f1fc0622fa3，尚未安装；Native仍owned78/178实际失城已保存，不热注入，不授Native79／忠诚修复。0newHTTP，累计463/431/29/3 HTTP493extra30，0newOpenCode-native／unknowncachecostnull。

## 2026-11-06：79真实FOUND回执与464边境诊断

[79Native证据](testing/baiqi-found-city-receipt-native-79.md)。87文件pin e7ca335c6aa23b3e7bb885d5a7037d109d211fe5安装冷新10184birth1793941710.405207，freshbackgroundoffline05:08:30.397231Z/age0.004626后launch。旧78officialexit一次、actualprocessabsent0terminate；earlyMainMenucontextguard/ingameConnectionRefused0CMD后fresh126contexts。Original77Blocked167再load一次，1678,8/moves0，1684,13，171MOVE1093queued/1726moves不重发，1730:173:194一FOUND与newcity1114127/owner0/16cityactualUI-Core，actualobservedproofnew_owned_city_at_empty_site_and_absent_settler，关闭78unit_unavailable样本。175GRANARY1/32food3.40625，formal675630B SHA6b8b5d6128d9ebc0ab8744963d6523d0d18f1cdc07de1e08e03e52fb2c62a6a5一次save/load/Continue后worldcity/gold9229.44921875/twoNativecompleteDistricts及same3retainedunits保持；Executorobservernil＋ActionPanel3trackingglobalsnil已读回。只完成后reload，不授memorypending durablejournal。

一postbootstrapUnitwindow214/24targetMOVE/1FOUND/other189/unknownnoncivilianerrors等0，cap32实际25无溢；bootSDKunknown，7旧qualcase复用0newcredit。City23build/unit5/milproduction2非军令，events43err0drop0/3handlers移除。169/171freshknownactiveidle后普通progressEND各once；172select1view后step1在首guard忙拒0SKIP/end，fresh172后seq2..20/resume19skips/end一次；173actualAlexcomplaintTestPlayerrefuse+goodbyeonce各后174，无BACKGROUNDdiplo/UserForced。Ready后16是邯郸人口，不是帝国城数；actualState17315早于laterfound16，已独立核。legacyloghelpermetadataActual77是旧文本，rawcurrent79log保留，新owned79logfingerprint确认0BAIQIerror及同FOUND/observed，非SDKcounts。

464canonical一次stop/DONE/VALID0retry；raw只改SettlementSites，一oldexact/fullLua compile，isolated初有2foreign/1own会挡新goal，但已选旧goal后foreign出现仍发FOUND，hiddenforeignGetX guard抛脚本错，源码旧遍历foreignroster先读xy后Revealed缺口继承，wholepatch拒0rawNative/product。不能把原生推荐内部未知评分说无忠诚权重，也不能把已有城市GetLoyalty冒充空地预测。OwnerNative169已知visible1093empty扫描361boundedoffset/max271cell，实际163cell/15owncity/5visibleforeign/nearestown12/foreign4/error0，0foreignroster/gamecommands。这只是保守启发式夹具，不是公式。79Native175忠诚54/-23/3仍未改善；78actual178lossFAIL继续。累计464/432/29/3 HTTP494extra30，0newOpenCode-native、cache/costsnull；本包0产品变更/0repeat1108suite/Steam0online/upload/Alpha74不变。

## 2026-11-06：465候选反例与负责人80有界边境筛选

[80软件证据](testing/baiqi-known-border-screen-80.md)。465canonical一次stop/DONE/VALID0retry，helper隔离5反例：own5/foreign2仍true，typedCitytrue但lookupniltrue，IsCityniltrue，GetCount1/Members0用999假距离true，Nativeexception直抛。整helper拒0rawNative/product，只参考ownnearest/visibleboundedscan方向。Owner新KnownExpansionSupport放在RequestCivilian之前避免lexicalnil，typedfiniteID/owner/xy/FindID/Count一致自有<=128，firstcity豁免；ownnear<=9 scan3否则9，复用qualified immutableNeighborhoodGeometry/max37/271，freshindexxy，typedReveal/Visible之后typedIsCity+CityManagerGetCityAt，cityID/xy/owner与Nativeplotowner/distance一致，异常unknown nil等待，无foreignroster。Own/visiblecity<=3拒，visibleforeignwithin9且ownnearest>9拒，不是精准压力。移除旧allforeigncoords-before-Revealed；旧goal释放自己reservation并重规划，两FOUNDshortcut和NativeCanStart后再次helper→79emptywitness/Safe/finalunitmeta。NoGamearmy/diplo/governor/grant/territory/rescue开关。

新initial19在原79为18FAIL/1PASS0.231s，主要foreign-roster guard，不冒称18Nativebugs；owner19PASS0.257s，扩22PASS2.110s（visibility/revealunknown与ownsupportqualificationrace）。另把alternativeNativepathfixture补全相邻边，非只测跳边。full1130初1FAIL172.551s/outer177.0105277：旧生产者硬计Map.GetPlot(cityxy)一次，新实现0；替为禁PlayerManager.GetAliveIDs spy同时仍断言全部3合法hints46/47/48，4producerchecksPASS0.078s，最终full1130PASS152.753s/outer157.5973207。没有按耗时比推性能。2Python工具显式80/2消费者同步、独立Lua67..70不扩。包87 SHAf692255b24e89d1a2f438bbd0792876681ffe4254582d6e8a9aba2d257f41ea5未安装，Native仍79owned10184/175无hooks；80冷负/正分别取原167坏场景和旧136抵达档，结果未授。累计465/433/29/3 HTTP495extra30/0newOpenCode/unknowncachecostnull/Steam0online-upload/Alpha74不变。

## 2026-11-06：80双案Native，0新HTTP

[实际负／正与138重载](testing/baiqi-known-border-native-80.md)。87exact/9a6265bf/owned25132birth1793947593.606357，freshbackgroundoffline06:46:33.599085Z age0.00454。旧79formalExit后427.181049s无窗口仍残留，只终止精确自有10184一次，保存175SHA6b8核验、tuplegone，Steam/others0，cleanexit未授。负案original77blocked167→168target9764928仍9,8/2moves/15city，1093ownnearest12/5visibleforeign/nearest4/163cells0err，Unit29/targetMOVE0/FOUND0/SKIP1/other28，其余errunknownnoncivilianoverflow0；City3build/0units/events5err0drop0，精准cleanup；168official652443B SHAe1c9ffdd66cd7d4758ab3ee0b4f1d99f092b73cb3672e9e4fef3687771e8f8c7未reload。

独立136arrived actor7274546@28,17/moves0/12city，currenthint776rank2、own胶东85197925,15 distance4，37visible3ring/0foreign/err。普通136外交来访TESTPLAYER拒pearls/Amphora交易+Goodbye各once，137actualnew917516/13city/1FOUND0:137:14，correctobservedempty-site+absentsettler。138granary3/32food0.8515625，137/138loyalty100/+1.84375。Unit39/targetFOUND1/0MOVE/other38/errunknownnoncivilianoverflow0，City6BUILD/unit3(1settler2builders)/mil0/events11err0drop0；allrestored/3handlersgone。138officialsave600429B SHA25f1cfd8e6825cc1dc38041e91d43d66eb5dd3d5991ca5a9b5a7d333b200447d/loadonce/Continueonce、actualUI/Core13/gold6516.9765625/city/queue/food/loyaltykeep、sixobservernil及3ActionPaneltrackingnil。完成后worldreload不授pendingmemoryjournal durable。

Owner诊断改137routeread旧167guard拒0CMD；Coreprobe旧37,24误报absent，修正a:GetX/Y28,17独立confirm；早137ready12早于laterFOUND13，ready非quiescence。136额外progressguard因diploactivefalse拒0action，137freshactiveidlequeuedbuilders后ordinaryprogressENDonceactual138。reload第一次capturehungguard和一次loadingglyph拒0input，后freshContinue一次，Load不重复。三原图内嵌与BBCode入库，0产品修改／不重跑已过1130。0newHTTP，465沿用已拒候选账、不追授模型Native功效；累计465/433/29/3 HTTP495extra30/OpenCode新0/unknowncachecostnull。Steam0online/upload/Alpha74不变。

## 2026-11-06：80自然训练成本Native，0新模型请求

[80同版本训练](testing/baiqi-natural-settler-training-80.md)：owned25132同进程/源码9a6265bf，138后台0:138:29 city458758@19,6选settler，progress0/13976/140121/141165、cost190/pop14/food11.28515625threshold82、Merchantestablished/HasPromotion201364422false。142event14new7929900type0@19,6healthy；15/16pop13均native13且209/190；17一次ProductionCompletedtype0row0/canceledfalse/native13/nextcost205，不把重复通知说两扣或205当原成本。actualUI/Core20,7/healthy，UI0moves/form1/queuednil，后台接Sewer；登船UI0/5不是0/2。Futureevents20err0drop0，City8BUILD/unit4/milproduction2，精确cleanup/3handlersgone；初始UnitSDKunknown，不将文本MOVE计数冒充SDK或训练军队误当军令。141save601766B cb848524c3d1def5da30a70cd5c7871d31df5ecf06dfed8bf4e71b1af4c4f2e7，142600691B c1fab613aa7b8d327983d1d50f48158b2a24f37981cc8c11faa827a43c112db9，两均未reload。3原图内嵌，0产品修改不重复1130。

139同回合freshpending后普通progressEND一次，实际AlexreligionagendaGoodbye一次到140。141WorldCongress需4免费票各A1：luxurySILK/espionageGAINTECH/diploBaiqi/fairapprove，reviewdecision/competition0，一submit一Return；actualUI结果luxuryDYES/espionageSABOTAGEDAM非本方choices，diploactual未读UNKNOWN，fairannouncement142确认一次。未用强制END/代文职。初139UIstatebusyguard0CMD后freshread，promotionwrongnamesnil按未知保留后hashlookupfalse；初142截图被fairnotification挡住私留，普通确认后重拍未编辑图。UI/Core总units瞬态差不代settler精确fullID。0newHTTP，累计465/433/29/3 HTTP495extra30/新OpenCode0/unknownnull，Steam0online-upload/Alpha74未改。路线／建城继续，不在训练子项交付后停止。

## 2026-11-06：80新7929900完整窄链与466文案候选

[80route/found/reload](testing/baiqi-natural-settler-founded-80.md)：14323,12、14423,17、14525,19moves2queued906、146moves5stillqueued/targetMOVE14未重发；147原0:145:139MOVEobserved后1FOUND0:147:173/new983053@26,20/14city/正确observed。147UIrawnil/fullinventory0，Core同7929900offmap-9999/delayedtrue/inventory1；148UI/CoreFindID(7929900)都alias8388652UNIT_TRADER@11,7，full792inventory0，不说nil/复活。147GRANARY0/32food0loyalty100/+17，1483/32food1/100/+20。未来Unitwindow108/14MOVE/1FOUND/93other/非文职未知错溢matcher0、32cap15actual，142initialSDKunknown；精确restore。148official618017B feeb426ca41edf66e1e274c579f204c5eb548894978080b6f55df3a609e6c585/save-load-Continue各once，actualUI/Core14/gold7107.87109375/cityqueuefoodloyalty及samealiasfullabsence保持、9Executor/3ActionPaneltrackingnil。不是pendingmemoryjournal durable。142Alex政体谴责Bye一次；143/145freshpending后ordinaryprogressEND各once；146ready147后stateUIbusyguard0CMD再fresh独读，普通军队SKIPs142-145各20/14619/14718，无UserForced/文职救场。3原图、BBCode入库，0产品不重复1130。

466实际在报告未写前canonicalPOST，shared363d4132/caller0fdf09/config75b5a，1attempt/stop/DONE/VALID，9079+316=9395tokens/TTFT1493.3314ms/total3703.3131ms/0retry/cachednull。Native148原件已给，但caption误沿用147+17、误称UI/Core生产忠诚一致（Core只city/alias），limits148只按raw漏alias；拒该稿，145/147事实顺序仅提纲参考，负责人中文全重写、0原样文案/Native/产品。Save/reload在POST后独立完成，不授模型实效。累计466/434/29/3 HTTP496extra30，Nov6canonical维护入口/同日成功1.19.5缓存、OpenCode新0、未知成本null。Steam0online-upload/Alpha74不变。

## 2026-11-06：467恢复协议／468Core探针，原稿均拒

[接口及合同记录](testing/baiqi-settlement-recovery-boundaries-80.md)。467完整59027+2030/61057tokens/TTFT7712.4215ms/total21208.6634ms、46816302+2142/18444/2274.4897ms/15764.5590ms，各1POSTstop/DONE/VALID0retry。467把cityexists OR actorremoved当观察、缺empty-witness/foreignconflict/缺失actor枚举/旧80无日志迁移及freshgrant边界；只提GP既有方向，wholeprotocol0adopt。468Lua53compile但rawisolatedmissingunpack和missingVisibilityglobal抛错，strictstaticdotfixture6misreceiver/0IsCitycalls；拒userdata本地对象、unguardedmethodindex及recursiveoutput亦缺陷，whole0Native/product。非Native错误参数实测。首467prep因taskfile缩进NameError在0task/intent/outputdir/POST前失败，owner修正再真请求一次，不算模型HTTPretry；实际468先完467才POST，pairpeak1而非拟并发2。

Owner独立probe当前sameowned80/25132/14814city，UI先fresh确认25,19及26,20visible/revealed；Core18scalar0errunknown，861owner0IsCityfalse/GetCityAtnil，906owner0IsCitytrue/GetCityAt983053fullownxy，两格Corevis/revealtrue/Native返回table。0foreignroster/propertywrite/eventregistration/gamecommands。Core商人8388652moves0/form1、MapGetPlotByIndex906可用；CityAddedToMap/CityInitialized存在不授signature。CoreGameConfigIsSavedGame type nil，pcallUNKNOWN/errorcaught；UI实际function/true仅当前loaded148，非freshfalse证明。持久协议未实现，0产品不重复1130/Steam0online-upload/Alpha74未改。

截至468累计468/436/29/3 HTTP498extra30/OpenCode新0/unknownnull；随后469新纯数据helper候选已另发完整stop/VALID，累计当前469/437/29/3 HTTP499extra30，尚未采用，不混本包Native功效。

## 2026-11-06：469／470到81未接线组件

[81组件软件](testing/baiqi-settlement-storage-81.md)：469完整2665+1349/4014tokens/TTFT519.744ms/total8273.0141ms0retry；raw6合同反例（finite/typedmax3、metatable3），ownerfinite-max/type+Plain(state/ops/op)+privateRequestID修正后18通过，主体部分采用。首ownerLua执行器漏return导致结果None误判，已在真实计数前改回，不能把18None当模型失败。470完整8450+1685/10135/1418.408ms/11511.2946ms0retry，rawwhole拒：全局C/J/KEY捕获未用E、无globals加载错、字面dotconsumer保护外抛；其余6coloncompat隔离案例显示validbankflag/alias/dupID/nil-race/unknownmulti/ignoredE，非认可接口变化。Owner新独立Corefactory27合同通过；加leaderfixture后原exclusive26review拒覆盖，v2保留27，不重复算26新场景。

source81新增J和StateCoreVFS/Files及reservedConfigKEY，无Controller/Gameplay/Executor接线、无实际Prepare/Commit/Observe，Native仍80。公共2unittest/45subcases0.678s，完整1132PASS136.515s/outer141.0803131s；2工具显式81/2消费者期望81，Lua67..70不扩。89包逐项bytesmatch但未装，Controller仍9d35f3...。Core80既有GPproperty只读shape top/operations/firstop metatablenil，不授新Settlement存储Native。累计470/438/29/3 HTTP500extra30，0newOpenCode/unknownnull；Steam0online-upload/Alpha74不变。下一步接持久桥及UI最终守卫并冷实机，不能在组件push后停下。

## 2026-11-06：471—474与82持久建城接线

[82软件](testing/baiqi-settlement-persistent-82.md)：471length3200/3928+3200=7128/24.6938734s未拼接；472stop3879+1796=5675/14.6821443s，raw缺end编译错，syntax-only仍2fail(-1owner/reason)，owner补end/-1/thirdreturn/Jinput后部分body采用30通过。473explicitredo4010+1407=5417/9.4607618s stop，rawliteral9fail，另兼容receiver-only3反例缺/抛Members和抛FindID误ABSENT，whole0采用；owner独立单位reader32通过。471472实际POST重叠peak2，473是新逻辑任务不是transportretry。474真实review20961+1210=22171/11.0714632s stop，validJSON内第二fix语义半句、两建议timeoutrelease/缺city放宽均拒绝0采用，不得按length记账。累计474/441/30/3 HTTP504extra30，0newOpenCode/unknownnull。

Owner成本：fixturefalse-and-or丢false先修再计模型；UIimportTestCase别名重复discover24旧test先改moduleimport实际16新；城市fixturewithCity不生效按真实cityEffect改；版本indent子串guard在写前停，newlineanchor后成功；80原生退出只读preflight用了缺失_G，0action后改显式hooks核，正式Exit仅一次，37.506633s后tuplegone0terminate。首次full1151/109.486s errors14全Executorstub缺新setter，补stub+2来源method后full1153/60.371s/outer62.06728880002629PASS。new21method（world2/Core1/UI16/Executor2）、62+43合同子场景不作Nativecredits。Core原生Grid44x26 getteronly，0新桥Native／尚未安装82。继续冷验证，Steam0online-upload/Alpha74不变。

## 2026-11-06：82原生初始化与475保存观察器审阅

[82冷实机](testing/baiqi-settlement-native-init-82.md)：first82 PID23684，owner只读query误把productionHash传UnitIndexgetter，已打印J0/READY但随后Timeout无CMDterminal；之后ownexceptiondialogEXCEPTION_ACCESS_VIOLATION。原件保留，native内部因果未独立证明，不能记model或productbug；owned窗口close后inactiveBM_CLICK未关，freshforeground正式OK后tuplegone11:18:39，0terminate/Steam-otherclose，不是cleanexitPASS。Same82pin8d6b901/93files boot2PID1468birth1793963972.9648132，freshoffline11:19:32.952436Z age0.006927s后启动；精简Jmeta与正确Index消费者Native完整返回。UI/Core55units0settler14citiesgold7107.87109375，Jplainv1owner0serial0ops0/跨contextSnapshotREADYexisting/typedUIIsSavedGametrue，Coregetter仍nil。普通Save617488B SHA3dfa0bd...→Loadtrue/Continueonce→双方读回J0和世界；不能排除空bankreinit，不授deserialize/pending。Normal14818militarySKIP+ordinaryEND→149，65536西安settler85/205，旧handoffBeijing误名已纠；Native2images。0Steamonline-uploadAlpha74不变。

475真实未写的普通Savewatcher候选stop4903+1018=5921tokens/TTFT3384.6505999ms/total34386.6954ms/0retry；rawcompile但7actualisolatedcounterexamples全部失败：void门、returnholes、throwmessage、saveerror、niloptions、missingSnapshot、invalidJ。Whole0Native/0codeadopt，outline后Saveonce和reloadARMED证据要求保留；准备owner透明版本。累计475/442/30/3 HTTP505extra30，0OpenCode原生新/unknownnull。

## 2026-11-06：82自然链通过，真实中途存档暴露未续建

[3图与完整边界](testing/baiqi-settlement-lifecycle-recovery-82.md)。Source82 unchanged8d6b901/93files；1153软件不因docs重跑。152实出生8650807@16,14，西安65536pop16→15（2通知同15非双扣），151181/205→152233/205/Completed row0 canceledfalse→next220。Late152SDK未来5MOVE+1FOUND，156request0:156:173/token settle:0:1/plot846xy10,19/city1048590太原14→15；157UI/CoreOBSERVED/原idrawnil+inventory0，granary7/32food2/loyalty100+24。UnitSDK106/5move/1found/100other/noncivilunknownerrOverflow0；City21BUILD/4builder0mil/events53errdrop0。正常151/153/154首次END已ACK但队列执行留原turn，freshpending读后新普通progress，0UserForced/文职输入。

Owner Savewatcher实际Native table.unpacknil/globalunpackfunction/_VERSION2013.2.0r13768，birthInstall依赖拒0wrapper-save，精确remove后explicitUnpackv2 35contracts(33+2非68)/birth12checks，direct真实8650807安装，475raw0Native-codeadopt。AfteractualNativeFOUNDreturn+CoreSnapshotARMED一次TEST_PLAYERSaveACKtrue，file630077B SHA6273f4...。正式Load156Core14cities/live865@10,19/1move/form1/ARMEDtoken同、cityIDnil；preContinue新logrestoredARMED证明真入档，不靠文件名。普通两round158仍14/live/ARMEDserial1，后装SDK48/0MOVE0FOUND2SKIP46other/安全计数0；缺口记录boundedFAIL自动续建，不定性永久卡死/Nativequeue已丢，0清journal/ready或重发。完成157638028B SHA6ab27...与失败158630355B SHAed4f...独立保存；3rawimages。

476真实新gap诊断stop8197+549=8746tokens/TTFT1439.2557ms/total5554.6311ms/0retry，whole修复0adopt：one-turn→definite lost与OwnCity-only proof均拒，观察outline使用。Core实RequestOperation/CanStartOperation nil，event表存在不授签名/因果。累计476/443/30/3 HTTP506extra30/OpenCode原生新0/unknownnull。Owner误用city:GetLoyalty→实际CulturalIdentitygetter只读Lua错修正；首次loadedprobe假设city存在，实际世界14被泛化reader揭示。Timed8read结束在过渡busy，链停后独立freshReady合格，无END重放。一次progress漏label写前失败，cleanup期待REMOVED实际CLEARED在链尾停、无需重清。Steam0online-upload/工坊Alpha74不变。

## 2026-11-06：477真实Core操作getter资格

[操作状态证据](research/baiqi-p6-settlement477-operation-read-evidence-2026-11-06.json)。CoreUnitManager反射18functions无Request/CanStart；ownunitmetatable.__index70functions实际含HasPendingOperations/GetOperationType/GetOperationParameter。仅类型枚举0调用被列函数，后owner独立typedreader16contracts，Native当前158/own8650807读false/-1、KNOWN，ARMED仍在，0命令／属性改变；GetOperationParameter和Name映射不调用。没有正向queued对照，不授网络输入队列空或重发许可，继续恢复缺口调查。

477rawcompile但16合同中11失败：rowtable与字面string比较导致正常单位永远拒、缺pcall、UNKNOWN造false/-1并带无效objectid、漏floor。Whole0Native-codeadopt，owner独立reader完整16pass；真实Native从source实际暴露方法发现后提出真实候选，不是假API探针。complete stop/DONE/VALID/0retry；累计477/444/30/3 HTTP507extra30/OpenCode新0/unknownnull。产品82不变，既有1153不为诊断重复计通过。Steam0online-upload/Alpha74不变。

## 2026-11-06：478自然队列正例与上下文边界

[UI/Core对照证据](research/baiqi-p6-settlement478-positive-queue-evidence-2026-11-06.json)。478为尚未实现的双上下文只读器候选，完整stop/DONE/VALID，2311+754=3065 tokens，5.0592618秒，0重试。原稿在方法值检查使用非法冒号语法，编译拒绝；还把UI路径写成Core的GetType。整稿未采用、未进实机，不把语法修补当作原稿通过。负责人独立只读器22个隔离合同通过后，实机按UI→Core读取同一回合的6名自有文职。8519734自然已有排队目的地，Core pending=true／op1477390184；另外5名为false／-1。该数字未做未知域名称映射，不自动推定网络输入队列已空，也不授重发许可。

累计478逻辑任务／445完整／30截断／3最终传输失败，HTTP508／额外重试30，OpenCode原生生成新增0，未知成本与缓存保持null。源码82未改，1153是先前产品全套结果，22是忽略目录内诊断合同，分别计数。Steam联网／上传0，工坊Alpha74不变。

## 2026-11-06：旧档迁移以跨回合创建时间验证持久化

[原生证据](research/baiqi-p6-settlement82-legacy-migration-evidence-2026-11-06.json)：Source82正式加载77版136、自然已有7274546@28,17，自动LEGACY_UNKNOWN／settle:0:1／recordturn136。20军事SKIP＋普通END，TEST_PLAYER拒交易／告别后到137，12城／同移民2moves。正式593519B保存、load／continue后UI+Core仍recordturn136，区别于缺bank在137重建；迁移与记录持久化窄PASS，扩张仍受阻。无QA属性写、私有恢复调用、SDK代理或手工文职输入。1张原图已内嵌。

负责人错误单列：preflight结尾与helper拼成双分号，Lua53允许而游戏整段解析拒绝，0动作；原intent保留，Lua51编译＋原flag nil后新load尝试一次。UI读档getter误写UI.IsSavedGame，只读有效前缀后错误，独立反射／真实消费者确认应为GameConfiguration.IsSavedGame，产品一直正确；修正读回true。END ACK后8轮未ready是外交来访，停止依赖动作，普通拒绝／告别后独立ready，0END重放。新HTTP／OpenCode原生生成均0，累计仍478/445/30/3 HTTP508extra30，未知成本null。产品82／先前1153不重算，Steam0online-upload／Alpha74不变。

## 2026-11-07：479新局源审与首都实际验收

[新局证据](research/baiqi-p6-newgame82-first-capital-evidence-2026-11-07.json)。共享先同步cb5d75e，仅新增其他业务文档；Nov7同机同用户00:36成功1.19.5维护缓存复用，非本轮更新／原生生成。479完整stop/DONE/VALID，53252+1495=54747 tokens，TTFT6.8882885秒／总21.7580344秒，0retry。三个finding无新缺陷采用：条件式缺依赖安全拒绝且有日志、忽略Initialize既有bank提前分支、暂不可用误推永久hold；原引文含!=而真实Lua~=。whole0补丁／0模型Native，保留事件时序未知。累计479/446/30/3 HTTP509extra30，OpenCode新0，未知缓存／成本null；PREP阶段记录交错UI工作，不称独占人工收益。

Source82新PID624/birth1794037522.685621，93filesmatch；Steam后台独立offline07:45:22.681802Z、age0.002195秒，0切换／上传。原版新局UIflagfalse，1回合自动city65536西安60,30与OBSERVED65536/token settle:0:1/request0:1:1；UI只warrior131073，Core原settler离图delayedtrue，区别活单位。1军队TEST_PLAYER SKIP＋1普通END到2，Monument0→4/60、gold10→15／warrior位置不变；893840B正规save/load/continue后UIflagtrue、同city/journal/progress保持。2原图；未装启动SDK，不授全局发令数。早MainMenu尚无context、两loadingLSQ Timeout均0CMD；capture activation失败另formalWin32focus；Cityview适配Python数值邻接SyntaxWarning读取成功，后续补空格。0产品修改，既有1153不重跑；ARMED及Legacy扩张缺口仍未关闭。

## 2026-11-07：480原版保存资格适配器采用，实际失败窗口补证

[完整证据](research/baiqi-p6-settlement480-allowed-save-window-evidence-2026-11-07.json)。480完整stop/DONE/VALID，7861+164=8025 tokens，TTFT1.3370833秒、总2.373142秒，0重试。Raw极窄Read(CanSave)零参单次pcall、typedbool、UNKNOWN不填false，14个Lua51场景通过；整段采用于忽略目录只读QA，并在真实UI原版getter使用。无产品采用；文字“无global／game logic”过宽，实际会执行传入引擎getter，单列纠正。负责人扩展旧SaveWatch加入资格采样，44当前版本场景（相关35＋新增9）、Lua51编译通过；两处空白锚点准备拒绝均0Native前修正，非模型错误。

新PID624原82／148复用，为新资格问题走自然训练与行军，不重复旧绿credit。156实际FOUND返回值0、CoreARMED同token，原版CanLocalPlayerSaveGame真；一次定时保存ACKtrue／630058B SHA d5a12456e94d80cb4f06756c71876ac89a95c3c17674661748fe03543c1f5f62。原世界后成15城OBSERVED并独立保存；精确cleanup后重载定时文件却14城/live8650807@10,19/moves1/ARMED，普通两回合158仍14/live2moves/ARMED。Corefalse/-1只当前unit状态，不授输入队列已空。资格允许不证明物理UI可插入同一调用栈／autosave时序。失败与完成均保留、1张稳态原图。

148／149旧8轮ready过渡超时，停止依赖后freshread；本例之后显式24轮上限，不改旧回执。151／153／154首普通END留当前处理队列，freshpending后新progressEND，0UserForced。157一次后续UI队列只读断言失败，链停；独立J与ready读成功，未重发END。首camera截图在动画中仅私留，稳态原图审后发布。累计480/447/30/3 HTTP510extra30，OpenCode新0、未知成本null；产品82／先前1153不重跑，Steam0online-upload／Alpha74不变。

## 2026-11-07：481只读政治状态器接管与真实早期接续

[原生时间线](research/baiqi-p6-domestic481-first-tech-civic-policy-evidence-2026-11-07.json)。481stop/DONE/VALID，5837+1497=7334tokens、TTFT0.9093176秒／总9.7998775秒、0retry。Raw Lua51编译但20场景13失败：成功没KNOWN、缺pcall、DBIndex不对照输入／字符串缺失仍放行、HasTech/HasCivic不校bool与固定行缺失仍放行、slotType允许无类型。整稿0Native／0采用；owner独立reader20场景通过，实际UI基线2为采矿／法典在研与空槽，原生Index/hash合同本次匹配。

Source82同一新局普通2→18、16军事SKIP＋16END，11首次HasMining真转畜牧、14首次HasCode真转技艺并装纪律／城市规划。10Monument44/60，18HasBuilding真／pop3／gold95／待命整备项目，当前排产原因未靠余额推断。991483B save SHA104cd33b6df743864addad163ac0eec5c39edbbf815251733b68fd65e9522543，loadContinue后全部相同。2原图；gov首次旧ref过60秒守卫拒0input，freshref后oneVIEW，不放宽门。0产品修改／1153不重跑，累计481/448/30/3 HTTP511extra30/OpenCode新0/unknownnull，Steam0online-uploadAlpha74不变。

## 2026-11-07：482待命排产审阅与真实首批单位

[公开证据](research/baiqi-p6-production482-standby-and-first-units-evidence-2026-11-07.json)。482stop/DONE/VALID，52083+1215=53298tokens，TTFT6.80614秒／总16.290719秒、0retry。四项源码判断保留窄事实、拒绝普遍无恢复缺口／无死锁保证；-1000仍是可选候选，CompletedIdleHead不资格项目，UnitCountChanged是handler而实际订阅UnitAddedToMap/RemovedFromMap，未决replacement分支仍会保留。0产品patch／raw0Native，不拿源码推断Native项目完工。

已测finance观察器10项重跑通过，Lua51编译后19绑定、33精确恢复；383招募+3城请求+6文职op=392／0error-drop。实际22排builder、26进38/50、27进46/50、28出生接slinger、32军队出现、33原位；15普通END16军队SKIP，无文职／人工资源。builder仍在城内、3劳动力、10自有plot无改良，东侧可见蛮族，未授建设或完整原因。1017948Bsave SHAbe1c1596228d62a1b2f2d2b1fa79c40e163a29e5ff62eb0ad778f48acaf10ded loadContinue三单位/城/金币/项目保持。2原图。CMD空格regex只读检索失误已纠；continue ignoredhelper误删行在运行前读回恢复；loading一次LSQ拒连接0CMD，不重放load。累计482/449/30/3 HTTP512extra30/OpenCode新0/unknownnull，源码82未改1153不重跑／Steam0online-uploadAlpha74。

## 2026-11-07：483推荐非空与当前安全拒绝条件

[原生事实](research/baiqi-p6-builder483-threat-wait-evidence-2026-11-07.json)：当前33builder原生3条recommendation，2205/2281/2353均自有revealed/visible；首都radius2的19geometrycells只读可见普通+宗教层，3敌unit均owner63/atwartrue/distance2，位置61,31勇士、61,29scout、62,30蛮族骑射。源码原地work需Safe(here)，路线含origin逐项Safe，条件匹配；未调用privateSafe/Planner，也未证明分支全trace／清敌恢复／实际改良。0游戏orders/hooks/propertywrites，复用482两图但不计新图，当前已reload33不变。

483stop/DONE/VALID，1565+1541=3106tokens、TTFT0.5017968秒／总9.7810995秒，0retry。Raw compile却把GetLocalPlayer数字当对象，编GetHuman/GetLeader、缺pcall、purchased按unique而非raw计上限、Inf坐标等；27中24fail并非24种独立bug，前置错误遮蔽，0Native/0整稿采用。Owner独立reader27Lua51pass后实际KNOWN3非空。累计483/450/30/3 HTTP513extra30/OpenCode新0未知null；产品82未改1153不重跑，Steam0online-uploadAlpha74。

## 2026-11-07：484测试玩家军控与危险退去后的真实农场

[公开证据](research/baiqi-p6-threat484-combat-and-farm-recovery-evidence-2026-11-07.json)。484stop/DONE/VALID，2155+1320=3475tokens，TTFT0.484792秒／总9.9145323秒，0retry。Advisory错把Player33、warrior131073当archer／错升级对象、用CanStartCommand作远程资格；整稿0采用／0Native。Owner按原版UnitPanel upgrade和Civ6Common/WorldInput签名，15Lua51升级守卫场景通过。33slinger262146→archer327683/cost60/gold170→110，旧对象发令后不用；33→38共5END3milSKIP、额外10军控（1upgrade4move4range1melee），0civilian/grants/forced/declare。

38实际builder196608从6030到5929，先MOVE再BUILD_IMPROVEMENT/hash168372657；plot2205 FarmIndex1/nonpillaged、3→2charges／manualaction0，archer同格仍2moves/form1未带走。未来Executor133样本127recruit1city5builderop／0error-drop／军事0仅该scope；全清再1024091Bsave/hashb40b7eb45a6312a7b7bd8f57de2e7cb5c9b398d02aa89ec6bc1fd49879a4a8e3，正式loadContinue同Farm/charges/3units/pop4/gold130/standby/Jobserved。3新图内嵌，危险只是离开当前可见半径，不称全灭或全图安全。36pureSettlertrue但standby，不据此判Native合法或FAIL，485后续独立诊断。

Owner纠正：34scoutmeleepreview距2门拒0input；END34/35旧16读提前结束，分别fresh35/36无END重发，新future32读，36→37第20读成功。reposition先validate两层再ipairs，空白编辑一次Lua51compile拒0CMD后修；一次只读patch锚失配未编辑。37首快读伤害0/move1，后实际66/move0，无射击重放。累计484/451/30/3 HTTP514extra30/OpenCode新0未知null，源码82未改1153不重跑，Steam0online-uploadAlpha74；既有恢复FAIL保留。

## 2026-11-07：485移民当前资格与真实空推荐

[证据](research/baiqi-p6-production485-settler-legality-hints-evidence-2026-11-07.json)。485stop/DONE/VALID5881tokens(4759+1122)、TTFT0.8041193秒／总7.7705949秒／0retry；Lua51 compile在`player:GetCities and`语法失败，另错把GetLocalPlayer数字当对象、无全读pcall、UI缺失可跳过门。0raw合同运行／0Native／0整稿采用；owner独立25casepass（signed Hash/Native两种receiver/精确bool/三状态边界/未知保护）。

实际38 settleIndex0/hash-798712536，qsize1/standby743941431，两CanProduce和native appendCanStart均true。另原始GrandAI可用、GetSettlementRecommendations(12)真实table但0条，0隐藏坐标／属性输出。源码2027临时hasSafeSite=true做纯预算，2029才取实际Sites，2030完整门；故puretrue不等完整允许，当前appendtrue不等queueReady，更不倒推36。0gameorders/hooks/statewrite，private38FarmSave仍保持。累计485/452/30/3 HTTP515extra30/OpenCode新0未知null；source82未改1153不重跑/Steam0Alpha74。

## 2026-11-07：487—491离线发布工具

[候选与证据](research/baiqi-p6-release-tools-487-491-evidence-2026-11-07.json)、[用法](workshop/release-tooling.md)。487/488 length未采用，不拼接；489—491完整stop/JSON后选择部分逻辑。490禁止87回退／宽松Convert；491修正count==count+1，regex JSON转义本身有效不记模型错误。Owner测试预期22改为实际20；14测试方法含官方SDK C#5编译和20纯助手case全过，未调用Publisher.Main/SteamAPI。并行真实2后3（按HTTP区间），累计491/456/32/3 HTTP521 extra30；维护复用Nov7同机同用户00:36成功1.19.5，OpenCode新0、未知null。源码82不改，0联网上传。

## 2026-11-07：486与492新局真实训练、读取时刻与派发时刻分开

[公开证据](research/baiqi-p6-frontier486-path492-natural-settler-evidence-2026-11-07.json)。486raw Lua51goto拒，owner27pass；prompt没写5.1是owner准备责任。492raw可编译但18中7fail（全actor采样／userdata忽略／空路径UNKNOWN／holes等），owner18pass，路径复制变体19pass。52/53待命后的Native空plots不解释派发前；未来54/55/56实际原返回5格，55当前可见4交战敌军影响起点和前三后续格。后读威胁不是历史路径样本同刻快照。旧builder3BUILD与3改良／46消失相符；43入settler、51生393216，pop4→4未授cost；56生builder458754、排军营。18normalEND31armySKIP+5armyorders、0civ/cheats。527futureExecutor样本510recruit4city13unitop／0mil/error/drop仅scope。56save1090744B/hash049d6d01829fa298d39c38f3fe2ce09ffb8b35e1d6f2cc4ae7a55e55328425f1全钩清后正式reload保持，3新图。Owner防御第二步在moves0后仍预览再调用，被守卫0emit拒；流程错误留证后依赖操作改查exit+semantic。累计492457stop32length3transportHTTP522extra30/OpenCode新0／未知null；82不改1153不重跑／Steam0Alpha74。

## 2026-11-07：493／494发布文案候选按图和世界身份复核

[Alpha2准备证据](research/baiqi-p6-alpha2-493494-offline-preparation-evidence-2026-11-07.json)。两候选均stop/DONE/VALID，4938181tokens/TTFT1.5821299秒/总14.6315424秒，4947793tokens/1.8813511秒/12.8981036秒，均0retry。真实并行2。493错图注（18图叫14、38farm讲44/45、51图讲56），494把14城ARMED-save QA误叫新局且复制任务指令到notes，均不整稿采用；owner重写并按原PNG/Native证据修。12图=新82局5+历史7，BBCode5248B，本地93文件/ZIP逐项一致hasha1f8be6e2dd5ebccf2300caabd9e1aeebc84dec7f737ef8e72044e6d1dc1ff16。封面builtin imagegen edit原图与prompt公开，JPEG仅格式/尺寸转换，非实机。跨page意图日志新回归后15工具method/20managedcases通过，0Publisher.Main/API。累计494459stop32length3transportHTTP524extra30/OpenCode新0未知null；每日维护复用Nov7同机同用户00:36成功1.19.5。缺fresh占用状态，async问题待答，0联网上传、工坊lastverified74。

## 2026-11-07：Alpha2发布执行不是新增模型能力

[回执](workshop/v0.1.0-alpha.2/publication-evidence.json)：8个官方SDK发布器进程（7创建端上下文、1消费端），5次图库追加＋1次内容更新均OK，无Create／自动重放；12张真实正文HTMLimg与全部图像／新封面哈希、93文件实际下载通过。先取得本轮人工无人报告，不伪装API检测。模式物理操作ACK未生效，保留当前在线读回；正常Exit/普通重启后，正式Invoke＋14904实例新鲜GoOnline只读才授offline，原因未知不猜DPI。自有游戏已保存64后退出无UI残留超180秒才单独terminate，不能称clean正常退出，Steam0terminate。此执行0新HTTP／OpenCode任务，逻辑累计仍494／459stop／32length／3transport／HTTP524extra30，未知成本null，不能把SDK成功或软件15方法授40项实机。

## 2026-11-07：495—497城址连续性与只读探针

[证据](research/baiqi-p6-target495497-continuity-source83-evidence-2026-11-07.json)。三次HTTP均200/完整stop/VALID，495私有Safe／KnownSupport伪导出与源码错误拒；496少end编译FAIL、缺完整身份／可见性／界限守卫，0原稿Native，owner重写只读已知1983membership及3圈可见city。冷读64raw3且1983false，21/37当前可见0city，ownnearest4；不能倒推原进程私有goal或授私有support返回。497修改采用优先候选／call，owner去任意1000分、显式优先、重复保留最高评分。9新回归，82有3fail，83聚焦98pass；首全量18error由owner遗漏版本消费者，修后1172pass1SDK环境skip，71Lua51/93zip一致，尚未安装Native。当前82Core死builder离图额外行不算活单位；147469951实际REPAIR枚举不授修复效果。累计497/462stop32length3transportHTTP527extra30，OpenCode新0／未知成本null。

## 2026-11-08：83原生扩张与498—500计划候选拒绝

[证据](research/baiqi-p6-source83-native-and-goals498500-evidence-2026-11-08.json)。源83/93从82save56冷启，10normalEND14armySKIP+8armyorder，61自走／64到1983／65一次FOUND北京／66grain5/65及save1126483B/hashc8a27cdc4b8fd57466ee4a6e8d26d1612b88fc4b326f0b2dbf4e259c67b4dae7正式reload双上下文保持，全钩nil。当前推荐3不含1983是移动后读回，非派发原子见证；原生窄链与条件软件回归分开。270finance完整读回0error/drop、14civops含FOUND1及SKIP1，745019656来自GameInfo而非枚举；0ret不是success。500globalvisibility错误由Core只读类型证实nil/perplayerfunction，原稿构造即engine拒。498答非任务、499raw8/18且exportmissing，owner私有schema18pass未产品接线；500另有formation2/index/读回缺口均拒。500Nov8canonicalfreshOpenCode1.19.5日检查，无update；498/499调用在Nov7，各日维护不混。累计500465stop32length3transportHTTP530extra30/OpenCode新0/未知null。焦点失败未发Continue，独立UIA focus恢复；4319未资格0CMD，4318新LSQ126再读；cycle56END到57后只读路径错误，补读不重放。

## 2026-11-08：501／502未接线候选与负责人84接管

[证据](research/baiqi-p6-goals501502-source84-evidence-2026-11-08.json)。501helper能编译但Process完全不调用Read/Remember，cleanup是散文，拒绝；502在正确预期tests路径内存运行6项3error／3pass，Python集合当Lua及负数组索引、重建测试没重建，0整稿Native。owner任务混用旧Lua53夹具与5.1要求是准备问题，重写新UI全部Lua51。产品84 owner接通独立schema/Core/Gameplay/UI，30新方法中Core19、Gameplay4、Schema18子案、UI6；full1202pass1SDK环境skip、74Lua51/96zip一致。首次宽hunk错把Forget加在FOUND_RELIGION，直接读回即纠正至确证FOUND_CITY，未安装Native。抽象Controller地图显式假桥，不假扮真实Core集成；后者独立一致几何用例。每日维护复用Nov8task500成功1.19.5缓存，逻辑502467stop32length3transportHTTP532extra30/OpenCode新0/未知null。当前运行83已save66并正式请求exit一次，84尚未Native，Alpha2不改82。

## 2026-11-08：503排队负向守卫与84真实目标保存

[证据](research/baiqi-p6-queued-goal503-source85-evidence-2026-11-08.json)。84/96冷原56→61，5normalEND4milSKIP+8军队动作，0civ/domestic/grants/forced；Goalkey初始nil，61actual393216→1983/5926，actor5929/moves1/queued2132，J首都OBS1且无本actorFOUND。4futureExecutor文职ops／6目标path，全部read并Restore；save1111447B/hashd94187488d0599829087b081dee1105c50c37f60a7065e15634820af23159611，未cold。503 raw3anchors都唯一且Lua51compile，existing/qualification负案过、afterCommit仍fakeFOUND1且ARMED，整稿拒并owner补最终native边界。85新8方法通过，84初8方法中6fail/8failure子案，完整1210pass1SDK环境skip/74Lua51/96zip匹配；nilqueue不是全引擎empty授权，保留ARMED不重放。85数据Core与84字节同，计划84save→85cold明确分账。累计503468stop32length3transportHTTP533extra30/OpenCode新0/未知null，canonical复用Nov8维护。
