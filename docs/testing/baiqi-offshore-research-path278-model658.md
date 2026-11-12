# 278：海上风电实际研究路径与UI端口边界

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-native127-research-path658-2026-11-12.json)，[32个潜在海上场址](baiqi-renewable-sites278-model657.md)。仍127／278，0新游戏命令，未发送END278。

本机原版TechTree.lua:231—245以实际goalHash调用GetResearchPath，再将表交给研究请求。Owner本次只读取得3条实际路径，共10个条目，均是dense 1-based键、值为实际科技Index，逐项能解析真实元数据与HasTech／CanResearch／进度／成本。海上风电为核裂变56→激光61→核聚变66→控制论72→预测系统74；只有首项当前CanResearchtrue，成本依次664／740／862／1100／1150，均0进度。陆上风电为54→57→62，地热为54→57。此处只证明当前存档的表形和实际图，不能对任意接口或静态XML作同样推断。

塑料54仍为533.61328125/592正进度，0研究动作，须保留。UI实际ImprovementBuilder为nil；UI GetTeam端口可用并受保护读得0。652／657的地形适用性端口位于Core，不能把Core限定的API搬进UI后当已实现。下一包将用已有ExposedMembers模式加小型只读资格桥，规划有空场址的真实供电路径，只申请下一项当前可研究的前置，继续使用原pending-before-writer协议与洪灾优先，不将场址适用性授为建造或清地许可。

658收到完整SSE终止但finish_reason=length：10420+3600=14020tokens／21476.2673ms，JSON资格UNKNOWN。半截候选正文未读取／拼接／采用／自动重试；上面诊断由Owner独立写成，Lua51编译后带前后人类白绮／单机／回合／active／settled保护执行，逐路径128／总512上限。本段不计半截候选能力。累计658逻辑／612完整／43length／3transport／688HTTP／30extra，OpenCode维护缓存复用、原生0，未知成本null。

持续供电、粮食阶段差异与旧完整矩阵仍开放；后续659—661为桥、消费端和行为用例三个不同真实任务。
