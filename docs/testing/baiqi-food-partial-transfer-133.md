# 133：区分已转入和救粮完成

2026-11-12，BF-202609141645。[逐项软件证据](../research/baiqi-p6-source133-partial-food-software-2026-11-12.json)，[132真实部分生效FAIL](baiqi-food-donor-native132-partial304.md)。源码133软件通过，正式冷验待做；当前仍保存并停止在132／304。

132实际把2133转入上海，但收粮收益1小于原供粮城UI收益2，上海仍净−1。133增加严格TRANSFERRED回执，表示精确城市／地块归属已证且供粮城非负、目标仍负粮；OBSERVED仍只代表两城非负。保留旧version1及ARMED／OBSERVED记录，负粮允许有限小数，首次TRANSFERRED不随下一回合或负数变化反复写；后来真实非负可升级OBSERVED。

本地hold仅凭完全相同的非空token与城市身份接受TRANSFERRED或OBSERVED。新的已确认token允许同回合按当前状态计划另一块地，turn／token按类型保存，OPEN的nil和字符串nil不同。每条新命令仍需fresh Prepare、持久ARMED读回与最终资格；已确认旧plot显式禁止重复，未决／缺token／错误token／异常回复一律不授重发。原闲地分支、有余粮邻城资格及原安全注释保留，没有人工内政、清许可或补粮。UI粮仍只是提示，实际转入和原生净粮决定接续及完成。

680／681／682均stop／DONE／合法JSON。680原稿三个独立反例：−0.5非法被拒、跨回合重复写负粮回执、允许重复原plot；整模块拒用，部分状态入口及日志方向采用。681部分精确token／stage／日志hunk采用，字符串拼接attemptKey把OPEN nil与字符串nil混淆，负责人改为类型对；未采用删注释。682原10方法仅1通过、9unittest errors，Core接线在globals前且随后覆盖ExposedMembers、虚用donor、没有第二块地和真实重载，整拒。原候选0Native。

负责人12项新Lua5.1方法、55项相关通过；实际两块地的fixture覆盖单回合两条不同请求、收益预测2但实际增1后接续、已生效旧ARM冷读、两模块真正重载、源负粮／错误身份／token／最终漂移拒绝。旧132三个精确行为均Lua断言失败（Lupa为unittest errors）。完整冻结1933项：1932通过、1官方SDK跳过；97Lua5.1、119文件包逐字节一致。首55相关中的10个错误归负责人：双格fixture保留距离4却暴露工作行，改为距离2并补直接Prepare成本；旧供粮测试负粮状态／写数按新TRANSFERRED合同明确更新，未放宽OBSERVED要求。

三HTTP实际峰3、三路重叠23.816935秒，累计682逻辑／634完整／45length／3transport／712HTTP／30extra；同日1.19.5成功维护缓存复用，OpenCode原生0，未知缓存成本净收益null。下一步冷装133载实际132部分生效档，不重放2133，读回另一个新计划和两城净粮，再继续普通回合。Steam未上线／未上传，工坊82；五条历史停止记录与人口损失开放项保持。
