# 122／256：实际维护费导致购买被误挡

2026-11-12，BF-202609141645。源码／安装／运行122，源码4ab8227695430d8bab70ca0e93634540b8139e3c。[分项证据](../research/baiqi-p6-source122-native256-failure-and-model640-2026-11-12.json)，[软件](baiqi-paid-flood-barrier-122.md)。

117文件逐字节安装，新鲜后台Steam离线确认后0.005207秒启动。正式冷载保留的121／256，一次Continue；0END、0人工内政／购买、0上线上传。WORLD／CITY／BUILDING／DISTRICT／PLOT／UNIT及11城粮食／vitals与原256完全一致。两城屏障仍未建，金币19287.51953125未减少，各自报价135、两种原版购买资格皆true，Holds=false，共享洪水需求皆true；没有请求日志。122尚未通过购买实效，保持256不推进海平面事件。

负责人误设“只支持零维护屏障”，实机metadata Maintenance实际为1。将准确源码中的只读Context／Read／Eligible函数在词法局部预验，不include、不执行Work／Run／RequestCommand或覆盖全局：Context=true，配置leader／reserve100／net2正确，实际Gold.Index=2及枚举类型正确；两城Read与Eligible均pcall成功但返回nil。零维护条件足以阻断路径，不能用无错误日志代替资格通过；未设置全局调度调用计数，不追认实际调度次数。

640先提出真实诊断候选：HTTP200/stop/DONE/VALID，7274+614=7888tokens、5474.3291ms。其H2维护费方向经独立Native确认；原诊断却把Context函数当环境对象、再次把pcall布尔索引、没有引入私有函数作用域，隔离反例失败，原代码拒用；hypotheses还未遵循字符串合同。Owner只读共13值与4函数结果，所有回合标签256，无游戏动作／订阅／全局替换。

安装私有helper首次缩进错误发生在执行任何安装／启动之前；修复并py_compile后仅正式安装一次，没有重放游戏动作。模型每日维护复用Nov12同机同用户1.19.5成功缓存，累计640／596完整／41length／3transport／670HTTP／30extra，OpenCode原生0，未知成本null。

继续123：按真实有限非负维护费计入预算，保留100金币与净收入2，并为同回合新增维护费留余量；软件验证后从同一原256重新冷验，不热替换模组、不人工代购。旧121／257沉没失败和本122未购买失败均保留。全功能验收未完成。
