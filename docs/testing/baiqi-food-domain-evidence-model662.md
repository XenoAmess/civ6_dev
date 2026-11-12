# 662：粮食证据按独立领域保留未知

2026-11-12，BF-202609141645。[逐项证据](../research/baiqi-food-domain-evidence662-2026-11-12.json)，[原271—272现场](baiqi-renewable-research-native271-food272-125.md)、[273阶段差异](baiqi-satellites-unlocked275-builder-125.md)。本包只处理离线诊断，0新游戏命令，模组版本128不变。

新增[纯分析器](../../tools/food_interval_evidence.py)和[9项行为测试](../../tests/test_food_interval_evidence.py)。UI区间、Core端点值和生产记录覆盖分别资格：同实例／城市、恰一回合、同人口与完整有限UI字段才算库存差；Core各自匹配对应UI的scope／城市／回合才比较值，但明确不是原子同时采样。缺Core或事件不能抹去合格UI库存变化。事件None、记录空列表、超过128、畸形覆盖分开；超额整段未知，不用前缀冒充完整。只保留范围内本城完成事件，输出拷贝已验证字段，不带未验证extras，不能由空列表推所有游戏事件不存在。永不返回END许可，因果结论固定null。

662完整1505+2167=3672tokens／12835.5005ms、stop／DONE／合法JSON、Python可编译，但5个隔离反例成立：外国Core被记qualified；无合格UI范围仍保事件；畸形事件被排除后领域仍记qualified；超大整数math.isfinite抛OverflowError；借用完整事件行使未验证object泄漏到输出而JSON不可序列化。输入不变方向成立，整份拒用／0rawNative。Owner接手，9方法与额外55个坏参数组合通过。

实际重放125保存的272→273旧消息：邢州11人，UI库存1.34765625→0.34765625、差−1，UI净粮+1→−1；Core272为+1，273稍后读为+4。分析器保库存损失、记录端点值差异，生产覆盖缺失仍未知，没有把后读正数当成前一结算无损，也没有把跨阶段Core／UI差值当瞬时冲突或证明项目供电导致。原始查询／私有存档没有提交。根因和213人口损失仍未解决，本包不授粮食修复通过。

只补独立诊断工具及其验证，128模组此前完整1838通过／1SDK跳过另记，不将新增9项冒称重跑全部。累计662／616完整／43length／3transport／692HTTP／30extra，维护缓存复用、OpenCode原生0，未知缓存／成本／净收益null。Steam保持离线／工坊82，继续实际供电前置与粮食验收。
