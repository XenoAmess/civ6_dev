# 126：建造者相邻施工的软件修复

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-source126-adjacent-builder-software-2026-11-12.json)，[125真实缺口](baiqi-solar-suitability275-model652.md)。源码126软件通过；安装／运行仍125／275，不能授126施工实效。

原版GS以独立BUILD_IMPROVEMENT_ADJACENT操作建设滑雪场。126仅在Builder白名单加入该操作，严格限定实际IMPROVEMENT_SKI_RESORT元数据；普通BUILD_IMPROVEMENT仍只能所在格，不开放任意远程建设。GetOperationTargets以Hash取PLOTS，按pairs接受0键稀疏原版列表，最多128原始行，逐目标读回己方可见／已揭示／空改良无区域／相距1及威胁，再以准确operation、目标XY、Hash逐项Native资格；稳定按plotIndex选当前合法目标。原在途route优先、修复优先，之后相邻施工先于普通同格改良；最后writer拒绝即停止，不转而走路或另建。

writer沿原RequestCivilian和pending，不在模型或诊断中发命令。Native资格之后再读新鲜演员、位置、护送、上下文／Core、同一目标ID／坐标／归属／可见／空状态／距离和真实元数据Index／Hash／type，绑定同一qualifier、writer及operation／参数键；pending在单次RequestOperation之前。军队、宗教战斗单位和其他文职没有新增许可，未知回执沿原协议保持。

AI滑雪场山格建议现在转为最多6个相邻己方可见、可步行陆地格作为站位；沿既有预算、分阶段路径和最后MOVE安全检查抵达后，再从实际原生可施工列表重检。站位上已有农场或其他改良保留，未增加拆地或太阳能转换。普通AI建议目的地保持。最多128城、每城128建议／总1024及每目标6邻格；异常、未知、缺GS入口不授相邻命令。

653／654两真实任务并行，实际HTTP重叠26.500657秒、初始与峰值2，不冒称12—16。653完整26151+2603=28754tokens／26500.6884ms，原helper错用CanStartOperation多返回替代原版GetOperationTargets，隔离已提供合法目标仍nil且0真正目标查询；另含未声明ctx、错误站位和不可达writer hunk等整拒。654完整26256+3222=29478tokens／31049.9640ms，Python编译过，但原13方法均因自己未补UnitOperationResults在setup报错、0行为通过；另有空pass、plotID当XY、原生目标当所在格、字面反斜线n等问题，原测试不采用。Owner依原版合同重写实现及测试，不将题目已有接口要求算模型发现。

新增15个Lua5.1测试通过，覆盖真实目标producer、准确operation／XY／Hash、pending先于writer和一次请求、优先级、普通远程拒绝、军事／护送／外方／隐藏拒绝、稀疏目标、异常／超限未知、Native回调改变演员／目标／元数据／函数绑定后拒绝、邻格站位和普通路径保持。精确旧125在三个关键行为均断言失败／0异常；首次比较把普通查询做抛错哨兵得2失败1fixtureerror，改为计数false返回后得到上述3失败，原件保留，不归产品或模型。现行完整1807项／147.131秒：1806通过、1官方SDK跳过；95Lua5.1编译，117文件压缩逐字节一致。

实机125只读资格先核原生operation945035974、Ski45／2135005470、PLOTS1933683541，6建造者均返回table且合法目标当前空，0异常；6山格周围18独立己方可见非不可通行邻格只是站位提案，不当安全路径或当前建造许可。275正式保存2229218字节／5deec39c15d40e11b064758db9f0d6445859c86c90b131c964e8ad52a32c4e09，未END275。下一步正式126冷装与自然移动／施工、完成态保存重载。

累计654／610完整／41length／3transport／684HTTP／30extra，Nov12同机同用户OpenCode1.19.5维护缓存复用，OpenCode原生0，缓存／成本／净收益未知null。Steam离线／0上传，工坊82；持续供电、粮食阶段差异和全功能验收继续。
