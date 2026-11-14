# NO_SITE配对输入审计／798

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-pressure-nosite-input798-2026-11-15.json)。798为后续NO_SITE五组配对提供纯文件审计：固定92f初始1、普通END1—5、激活2—6；真实TAB帧、军队请求ID／类型顺序、同回合重复及四种唯一回执均核验，不重标MANY数据，不把SKIP调用当物理完成。

核心采用，Owner补record回合及pid必须精确整数；原稿接受True作from_turn、2.0作to_turn及False作pid。原测试把MappingProxyType从collections导入，导入即失败、原测试执行0；只修为types后18方法通过。Owner另6负例覆盖3种类型与缺失／重复／畸形标记，1个带真实上下文前缀TAB／完整深复制不变正例通过。原测试和改后验证分开记录，未把原稿写成全绿。

模型7799输入／3858输出tokens、22941.6963ms、TTFT1332.5378ms，stop／DONE／JSON有效，1POST无重试。累计798逻辑／740完整／55length／3最终传输失败、828HTTP／30额外；维护复用Nov15成功缓存，原生工具生成0，缓存与全成本未知。请求在K初始载入与预热期完成，正式性能采集尚未开始。此处0Native查询或游戏操作，B_delta仍待真实十侧25段，TC-036仍PARTIAL。
