# 独立无落点几何夹具与只读快照／773

2026-11-14，BF-202609141645。[结构化证据](../research/baiqi-pressure-nosite-fixture773-2026-11-14.json)。真实新世界已准备，实际第1回合、白绮10城／埃及1城。独立只读快照覆盖全部1144个可见地块，核验1133水域／11城市／0裸陆地，QUALIFIED_NO_ADMISSIBLE_GEOMETRY。它只证明当前Controller必要的非水／非城市几何门排除全部地块；没有自然推荐样本、压力性能或MANY≥12结果，完整TC036仍PARTIAL。

主334新存档 Baiqi_P6_20261114_V142_PrePressureFixtureMain334.Civ6Save，2460247字节／SHA f70b50de5f2d8d6f1ce6689d306f0015ae6f4b4d46bcc7a4f07b147357e661cf，正式OnExitGame一次后原PID16524自然退出，无强退、END334或主世界建设／单位输入。发布142源码不改。安装已验证的私有静态control119文件和独立4文件地图包，当前自有PID13172／出生1794655286.7166457，CPU1—8。冷启动前当前Steam14904后台新鲜离线确认，年龄0.004468秒；正式菜单导航与模式证明分列，零截图／上线／上传。

地图在原版设置中注册成功，选NO_SITE后自动2大文明／0城邦。原版参数选择白绮和克娄巴特拉、远古／标准速度／王子／GS规则／无蛮族，种子game−335780351、map−335780350。地图回调真实记录44×26／11陆地，ordered当前创建日志确认加载完成后只向自有HWND发送一次Esc，再独立读取原生状态。原始世界双方0城，白绮移民65536和勇士131073同在4,4，未指挥军队或文职。

人工初始数据准备使用WorldBuilder.CityManager():Create(playerID,numericPlotIndex)，先1城验证普通Core适用性，再其余10城，每座独立读回位置／归属／城市数。返回两个数值为playerID和cityID；双方第一城ID均65536，证实跨玩家ID可重复。之后对1144地块各一次ChangeVisibilityCount(index,+1)，再读回全部可见。0人口／单位删除／生产或进度给予／移动／外交／结束回合。这些人工创建和揭图不计AI建城／探索成果。

工具 tools/lua/pressure_fixture_snapshot.lua 返回Collect(E,layout)，只读精确地图ID／尺寸和完整全图可见性，再读城市及地形；最后地块不可见时前面也不读取隐藏内容。城市ID、位置、归属、地块标志及前后回合一致性严格检查，非城owner由外部适配器显式序列化JSON null。6项Owner方法通过、Lua51／53两变体接实际Python核验器。原5过后补MANY真实分支，最终6过。一次Native采集完整1144行并独立核验，事实SHA 0291894883a28e45d81453a391cb9904a18dd43ca34d54e31260b5478153455e。

Ready私有存档 Baiqi_P6_20261114_V142_PressureNoSiteReady1.Civ6Save，295622字节／SHA 92f43e9ca5fa38adef7d0e602d50d3e11da6d65f9cfbd6db496292113c8b9aa0；留在忽略目录／游戏本机，不提交存档。仍实际1回合、10／1城；后续初始化1、正式窗2—6、收尾7，不重编号。尚无原生wrapflag读取，此几何门证明不依赖邻接／环绕。

负责人修正并留证：Mods出现8／32同名上下文，两次查询在CMD前拦截，未启用；改从唯一MainMenu持有的ModsContext执行原版API，读回启用。g_PlayerParameters实际为有序pairs数组，直接按0索引失败于setter前；改原版GetPlayerParameters(0)再选实际domain。初始误假定T0的两只读预检失败，实际诊断T1后改守卫，没有重放动作。端点首助手漏port在LSQ前失败，加载期间timeout只保留失败，未重发启动或继续。

773因length完整收到DONE但不满足stop，候选内容从未读取／解析／编译／执行，0采用、不拼接重发。3770input／6500output、37978.328ms、TTFT694.021ms；累计773逻辑／718完整／52length／3最终transport／803HTTP／30extra。维护成功缓存复用、OpenCode原生0，未知缓存／Owner有效成本／净节省null。继续自然调用观察与压力计时、独立MANY夹具。
