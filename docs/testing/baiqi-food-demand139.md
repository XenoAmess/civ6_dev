# 139已知无需求早退：软件通过，待实机

2026-11-14，BF-202609141645。[逐项证据](../research/baiqi-p6-source139-food-demand708-2026-11-14.json)，接[138仍超时](baiqi-native138-cold333-latency-open.md)。不盲删最终权限门：救粮先照常核对Core回执和未决token，再用当前本地玩家／回合／自有城市身份读取需求。只有有限且已知非负粮食才提前NoAction；负粮仍完整Player重验，再由Snapshot重新读实际粮食构造计划。Core Prepare、持久许可、post-arm Inspect、新鲜最终快照／Player／writer／参数重验保持，无跨回调缓存。

粮食偏好只在没有未决请求、当前已知非负或未知粮食时略去无用的citizen标志读取；有未决hold时即使粮食为nil／NaN也仍读实际偏好标志以观察，不重发。9新方法通过，相关88项通过；完整2023项中2022通过、1SDK环境条件跳过，134.031秒，97Lua51／119包逐字核验，既有sqlite警告保留。尚未安装／实机或授性能通过。

708单HTTP完整stop/DONE／严格JSON，17482+1682=19164tokens、12064.5755ms／TTFT2380.4561ms。救粮候选只是旧City，承诺的需求门不存在；真实正粮双城仍4次完整UI busy读、1次无用flag读取，0代码采用。偏好只保留Owner指定的未决区分方向，原稿nil粮食直接>=0异常，未决flag实际读取0而应1，整函数未直接采用。Owner补有限数与未知hold观察，独立实现需求／新鲜计划分层；不追授独立设计或节省。

累计708／657完整流48length3transport738HTTP30extra，Nov14维护cache复用、OpenCode原生0、未知成本null。138已保护333并正式退出请求一次；继续残留核验、新鲜离线139冷装同档与自然计时，不降低20ms参考，Steam0上线／上传，工坊82。
