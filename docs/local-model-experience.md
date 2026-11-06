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
