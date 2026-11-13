# Stage A v2：提前调用的完整区间证明／729软件

2026-11-14，BF-202609141645。[版本、明确产物哈希及软件证据](../research/baiqi-stageA-v2-preanchor729-2026-11-14.json)。在[独立87真实参数记录](baiqi-stageA-nativeD-arguments728.md)之后、v2正式采样之前声明本规则：只对无已知原生锚点时的精确Controller.RunNow(false)、恰1参数，完整执行canonical计时并保留样本，先记pending。真实Native回调必须随后给出该回合锚点，证明started<anchor、ended≤anchor、有限有序完整区间、同回合及已知城市数，才可单列为固定窗前调用。跨界、缺锚点、无穷／倒序、失败调用、未解决或账目不符仍未知／拒绝；true／nil／Admin无此例外，不按false参数直接丢弃样本。

提前行同样占4096总额，成功零时长不聚合；两个目标仍各需100纯十城窗口内样本，p95≤20ms／最大≤50ms，其余预算不变。证明和pending有独立计数，最终pending／错误必须0、recorded=validated且与逐行数量相等；缺失字段不补零，不造时钟。窗以实际观察到的原生回调时间为参考，内部引擎物理发出时刻及分辨率仍未知。

当前私有构建源标识显式升为`baiqi140-stageA-v2`，游戏发布版本仍140。v1分析形状和窗前拒绝规则保持；旧FAIL既不Reset、补行、改版本标识，也不追授通过。新v2分析单列before_native_anchor，不将这些窗前调用混入两个纯十城分位数。

7证明、4窗口集成、4分析器新方法通过；连23现有参数／窗口／生命周期、5真实构建、6未改trace、11旧v1分析，共60个不同相关方法已通过。真实Executor消费者测试额外加载当前Controller.Update源码，实际走TurnReady=false→Update→RunNow(false)，保留pending，随后逆序派发条件下真实回调入口解决，再记录窗内调用；不是复刻该Update实现。测试主动移除rawget／rawset。97Lua51／53、119文件明确v2包已准备，尚未新Native。

729完整5585tokens／5430.7598ms／TTFT1116.2816ms，单次stop／DONE／合法JSON。raw引用未定义Finite、已有锚点时不把新行入队／解决、pending未减、重复记录膨胀、倒序区间可通过、unknown回调可抛出；6合同探针全失败。为暴露两个后续问题，隔离测试仅提供Finite测试谓词，不拼接或采用候选。0原代码采用，Owner重写全局容量／唯一行引用／真实锚点绑定及所有消费者。

累计through729：729逻辑／676完整流（含历史一次严格JSON拒绝）／50length／3transport／759HTTP／30extra，新峰1；Nov14维护缓存复用、OpenCode原生0、未知成本null。下一步v2新冷启、原85预热／正式重读；没有B_plan、B_delta或整例PASS，持续修复验收。
