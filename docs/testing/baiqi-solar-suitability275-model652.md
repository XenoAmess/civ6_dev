# 275：太阳能适用性、阳性对照与相邻建设缺口

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-p6-native125-solar-suitability652-2026-11-12.json)，[卫星已拥有与AI建议](baiqi-satellites-unlocked275-builder-125.md)。仍125／275，本段0END／游戏命令，原275保存保持，Steam离线／工坊82。

从本机原版Pirates／CivRoyale消费者找到ImprovementBuilder.CanHaveImprovement(plot, improvement.Index, player:GetTeam())，第三参是团队。UI取得217己方可见购买格packet，Core逐格重核plot坐标、owner、购买城ID／坐标及可见／回合后，用实际team0／太阳能Index38查询：217 false、0 true／unknown。此为当前引擎适用性，不能当建造者操作资格，更不能预测清地／移除后会合法。独立阳性对照用实际6个滑雪场目标，同端口／team0均true。

652先行候选完整stop/DONE/合法JSON，2258+1294=3552tokens／8050.9301ms；原函数continue实际不兼容Lua51，且Safe返回result,'OK'，消费者却当ok,boolean：真实true和false分别见证为true,'OK'／false,'OK'，无法保留引擎布尔。整份拒用、0rawNative。Owner重写8合同后只读接入，测试team7≠pid0、false保留、缺端口／稀疏packet／boolID／外国地块／错误／非布尔／pid9等边界。

补充阳性对照第一次混入未资格Core方法而整体报function expected instead of nil，外层未保部分输出，不能把该次调用计0错或推定引擎调用数。随后独立分开受保护Core对照和已资格UI地块读取，取得上述6个阳性；6建造者当前各在市中心、农场、区域、长城、伐木场、区域，没有人工移动或改良操作。

本机原版Expansion2的WorldInput_Expansion2.lua:31—44明确以BUILD_IMPROVEMENT_ADJACENT、目标XY和improvementHash建设相邻格；51—58以GetOperationTargets和UnitOperationResults.PLOTS提供目标。125的Builder白名单缺这项，RequestCivilian非移动分支强制目标等于所在格，而AI建议保留山地目标本身。相邻施工功能缺口已确认，下一步接通原版目标与安全选路，并保军队／护送／未知回执边界。不能仅放宽普通BUILD_IMPROVEMENT的任意远程目标，也不据此拆农场。

累计652／608完整／41length／3transport／682HTTP／30extra，维护缓存复用，OpenCode原生0；缓存／成本／净收益未知null。太阳能建设、持续供电、粮食阶段差异和旧完整矩阵仍开放。
