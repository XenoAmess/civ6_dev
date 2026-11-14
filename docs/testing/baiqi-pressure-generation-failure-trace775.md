# MANY生成访问冲突与阶段日志／775

2026-11-14，BF-202609141645。[结构化证据](../research/baiqi-pressure-generation-failure-trace775-2026-11-14.json)。MANY第一次新世界创建FAIL：同一自有13172实例从已认证NO_SITE返回菜单后，原版启动一次；最后持久Lua行停在map seed616018722，未到几何完成／加载就绪。原生弹窗确认EXCEPTION_ACCESS_VIOLATION，WM_GETTEXT只读取759字符，调用栈全???，不能定位地形／丘陵／咽喉／大陆／渲染／复用实例的根因。

本次没有继续Esc、结束回合、人工城市／可见性准备、军队／文职命令或重复创建。地图内部原生写入数量未知，不补零。错误框仅对已核实自有PID的OK按钮BM_CLICK一次，随后进程自然消失，0强杀／Steam动作／截图。崩溃后重新核对主334的f70b50de…保存点和NO_SITE Ready1的92f43e9c…大小／SHA均保持；未提交存档。

新增 tools/lua/pressure_generation_trace.lua，构造不调用Native／logger，保留Map身份、有限整数地形索引及全部真实端口预检。记录1144地形调用的起止／128进度，以及区域、咽喉、大陆和双方起点的前后边界；参数／nil返回孔与原错误对象保持，logger失败不替代Native错误或增加调用，额外1145次在Native前拒绝。C++访问冲突不能由Lua pcall捕获，边界日志只是后续定位依据，不证明根因。

地图构建器新增 --trace-generation，仍独立四文件、无游戏回调；地图入口加载／尺寸回调和生成阶段日志只用于私有准备。原默认构建的全部元数据／输出哈希与772精确相同。12项相关方法通过，含7新方法；Lua51／53执行真实几何消费者及实际无参生成入口、原self／nil孔／错误身份／logger失败。产品142的119源哈希未改。新阶段日志包仅准备，未安装或Native运行，不能写成已修复崩溃。

775完整stop／DONE／strictJSON但代码／测试0采用。原Lua51／53均解析成功，却没有返回模块，Map身份改变、枚举校验缺、起点self传错、参数／返回丢失且不挡1145。原Python解析成功，7测试全在eval(local E语句)错误，尚未到Lua53；它们未加载被测模块，Python冒号写法还是注解而非方法调度。仅为软件反证额外加一行Owner export bridge，两版本实几何假端口均在1147次假变更后原self断言失败，不计原稿通过／采用／Native效果。156／144行也超过各130。Owner见证助手首次缺ROOT导入路径，失败于Lua前，修助手并核对候选原件相同后继续；不归模型失败或回填review时间。

5564input／3457output、21059.382ms、TTFT860.652ms，单POST峰1；累计775逻辑／720完整／52length／3最终transport／805HTTP／30extra。维护成功缓存复用、OpenCode原生0，未知成本null。继续新阶段日志包和全新实例的独立MANY尝试，保留本FAIL；完整TC036仍PARTIAL，Steam0上线／上传。
