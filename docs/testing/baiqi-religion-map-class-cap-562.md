# 562只读补验：当前地图先知类上限4、已成立宗教2

179回合实际读到Map.GetMapSize()=2／MAPSIZE_SMALL，对应PROPHET类MaxWorldInstances=4；按原版宗教界面的非Pantheon及HasBeenFounded条件，已成立宗教2。算术差为2。**这不是当前无预留的创教名额，也不是两个可领取先知或创教许可。**

此前555没有读取这项地图定义，上限记UNKNOWN是当时的真实边界；162的未领取先知池样本也不能当成179现状。本次只补地图类上限和公开已创教计数，没有读取当前先知池、改生产权重、手排圣地、生成先知或赠送信仰，宗教自然链仍未通过。

原版ReligionScreen.lua204–222先用Map.GetMapSize读取GameInfo.Maps.MapSizeType，再在GameInfo.Map_GreatPersonClasses匹配地图／PROPHET类，读取MaxWorldInstances。原版用于展示的nil→0回退不能作为诊断事实，负责人工具保留UNKNOWN，并将合法0与未知分开。

新增只读诊断模块不进模组包；它保留generic-for状态与控制值，接受编号0，检查有限整数、重复匹配、密集宗教列表和明确布尔标记；Native异常、稀疏／额外键、别名和无效记录不会变成0。只读取512条类数据（另一次仅检测溢出），宗教列表限64项；返回的新表只含标量，不引用来源表。负算术差保留，不伪装成0或创教资格。

22项Lua5.1检查通过，同组对562原稿为12通过／6失败／4异常。原稿虽能编译，但拒绝地图编号0、丢generic-for状态、漏异常保护，ipairs漏掉稀疏／非数组键，接受无穷上限及元表伪造宗教ID；原稿全部拒绝、0实机。负责人模块再在179的原版ReligionScreen上下文实际只读一次，0游戏命令／属性或控件写／私有Bridge。

模型562完整stop／DONE／合法JSON，1HTTP、1490+1013=2503 tokens、6.530123秒；累计562任务／524完整／35截断／3最终传输失败、592HTTP／30额外重试，新OpenCode原生生成0，未知成本null。新增的是诊断22检查，产品98及原1412项软件切点没有改变或重算为新完整回归。

下一步仍要独立核对当前先知供应、合法圣地区位和队列选择，才评估实际宗教生产策略。其他机器正在使用Steam，0模式切换／上线／登录／下载／上传初始化／上传，公开Alpha2仍内部82。

[结构化证据与候选审阅](../research/baiqi-p6-religion562-map-class-cap-evidence-2026-11-09.json)、[只读模块](../../tools/lua/diagnostic_religion_capacity.lua)、[22项验证](../../tests/test_diagnostic_religion_capacity.py)、[555历史先知池边界](baiqi-religion-public-pool-97.md)。
