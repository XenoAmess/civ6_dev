# Stage A诊断前缀的沙箱兼容纠正

2026-11-14，BF-202609141645。[实机读回及修正产物哈希](../research/baiqi-stageA-sandbox-correction-2026-11-14.json)。Owner的724诊断实现误用了游戏未提供的`rawget`／`rawset`。在新鲜offline证明后冷启，原始85载入并Continue一次，预热前资格门失败；只读实测两个内置函数及P6PerfPlanA均为nil。Lua.log明确报NewQualificationTrace第159行“function expected instead of nil”，发生在原版include／Executor正文及QA订阅／绑定之前。

这是Owner实现缺陷，不是模型724原代码的实机行为，也不能倒推首次Stage A已有的三个资格错误。0END、0正式重读、0正式样本，原始85文件哈希保持；已请求原版退出一次，没有为修复强杀Steam、上线或终止他人游戏。

修正版仅使用受pcall保护的普通表操作，trace返回明确初始化ready，失败时生命周期不能启用；记录失败不会掩盖游戏函数的原错误。有界原因／前16事件／饱和计数与未知元数据不补零的合同保持。测试沙箱主动移除这两个内置函数；6 trace、13窗口／生命周期、4真实构建／Executor方法共23项再次通过。97Lua51／53、119文件私有包已准备，只有Executor变换，尚待新冷验。

后续按这个明确新产物安装并检查真实初始化，再预热、重读和诊断。此前五窗B_turn／N_req证据保持独立，B_plan、B_delta及全功能验收仍开放。725另为匹配对照普通END计时合同的真实未完成任务，不能把其HTTP成功当成本次Owner修正或Native通过。
