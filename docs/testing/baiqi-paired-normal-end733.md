# 普通END跨UI入口／733软件

2026-11-14，BF-202609141645。[结构化证据](../research/baiqi-paired-normal-end733-2026-11-14.json)。新增`paired_normal_end.request_end(query,turn,token)`：严格验证85—89及32位小写hex token，只发一次ActionPanel查询。真实普通END资格和桥marker／source140／Begin函数验证后，桥Begin紧接原版无参数UI.RequestAction之前；完整发行返回凭证必须逐字段匹配。无选择／跳过单位、内政操作、UserForced、重试或伪造时钟。测试玩家的军队准备仍由外部回调先完成，独占END凭证／READY和原生换回合仍归既有驱动分读。

733完整候选模块原样采用；API、原版资格、调用顺序和回执形状是Owner事前明确合同。11297总tokens（359输出），4020.2102ms／TTFT1708.6640ms，单attempt／stop／DONE／合法JSON。原样6方法通过，正式采用后同6方法再验证消费者接入；共6个不同方法，不计12。实际canonical Lua时钟和桥确认五段各2秒不含各5秒准备；另验重复桥拒第二次END、动作后传输异常、缺失／错误／重复／ERR回执、坏参数和原版资格失败。

ActionPanel映射到单一Lua运行时仅为软件夹具，真实跨UI访问及静态control的普通END门仍未验证；需要实机五组25匹配段，不能从本包授B_delta或整例通过。累计733／680完整流／50length／3最终transport／763HTTP／30extra，本次峰1；维护成功缓存复用、OpenCode原生0、未知成本null。
