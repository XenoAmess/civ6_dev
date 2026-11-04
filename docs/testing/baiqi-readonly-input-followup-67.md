# 普通67：剩余只读输入的窄范围复核

2026-11-04；本页是待执行矩阵，不是新通过记录。用于继续TC-004／035及相关控制隔离；已有42版城市控件、45版普通领袖、46版宗教战斗与67版考古Delete／右键样本保留。

| 待补输入 | 实际路径 | 必须取得的证据 |
| --- | --- | --- |
| MOVE_TO模式左键释放 | 原版WorldInput的LButtonUp→OnMouseMoveToEnd→MoveUnitToCursorPlot→MoveUnitToPlot；右键释放实际是取消。白绮WrapMove和CanStartOperation守卫分别核对。 | 选中实际本国托管文职，核原版合法性；证明真实输入到达对应回调、拦截分支与零原生转发，读坐标／行动／订单。行动0时仅坐标不变不足；同条件普通领袖和玩家军队应能正常下令。若QA直接打开原版呈现模式以测深层守卫，须注明，不能冒充物理快捷键已通过。 |
| 城市生产取消与队列交换 | CurrentProductionButton右键／Trash／队列拖放→ProductionHelper.RemoveQueueItem／SwapQueueItem→CityManager.RequestOperation(BUILD)。OwnCity守卫拦截本国非军事操作。 | 比较原始队列、完整项／进度、费用及实际输入来源；交换须有两个原本存在的合法项。不能为凑正常生产通过人工补队列；专用旧队列夹具须明确标注。普通领袖同条件应能取消／换序。 |
| PlotInfo市民操作 | CitizenButton→OnClickCitizen→CityManager.RequestCommand(MANAGE)。上下文守卫核本国所有者，不能只检查别处的代理。 | 实际选城、地块／市民／焦点前后，回调到达及原生提交是否被阻止；普通领袖对照。城市面板对应控件已禁用，不因原版事件函数仍存在就判可接管。强制QA呈现与自然鼠标入口分开记录。 |

暂不接受模型声称的生产队列绕过：ESC只取消选择／关闭，且已有只读控制、控件禁用和底层请求拦截。负责人原325输入缺少ProductionHelper完整声明，已自行从原版补核，不能反说模型忽略了已提供的该声明；模型另外误读的ESC及忽略现有控件禁用有独立源码证据。Attack快捷键确有特殊预览入口，但普通文职本来不能攻击，单凭零攻击不授托管拦截通过。

每次实机保留真实构建／存档、正常原生资格、输入、受影响对象与后台动作归因；只临时观察实际入口并恢复同一指针，不更改AI权限、军队命令或外交。输入由测试代理扮演玩家，不向用户索取逐次点击。失败则保留、修复、复测，不临时增加禁用类型或改判据。

[324／325完整候选审阅、输入遗漏、实际并发与未知成本](../research/baiqi-p6-readonly-inputs324325-evidence-2026-11-04.json)。两份仅部分分析采用、代码0；静态检查不代表这张矩阵已通过。

## MOVE_TO左键：新增窄阻止样本

普通67／110回合实际考古学家6422556在9,15、行动0，原版对10,15合法移动资格仍true，受保护资格false。QA仅以原版呈现调用进入MOVE_TO，再真实点击一次：左键按下1／释放1、实际MOVE_TO表回调1、受保护MoveUnitToPlot入口1、该WorldInput上下文单位请求0。UI／Core位置和行动保持，serial1／作品15保持；临时观察器已恢复、两个诊断状态清空。不能只凭0行动时没移动判通过，也不能把上下文计数说成全局零军令。

这补了模式左键阻止样本，物理M快捷键、普通领袖及军队阳性对照仍须补齐。原生没有输入处理器getter，恢复使用受控正常上下文已知原始OnInputHandler，不能证明任意外来SetInputHandler未发生。326原稿正常恢复会误报冲突，负责人纠正后5项软件检查及当前实机分别留证。[实际计数、源纠正和清理范围](../research/baiqi-p6-native67-leftmove326-evidence-2026-11-04.json)。

## 白绮军队的真实M与左键阳性对照

110回合勇士131073，15,14／行动2。原版与受保护WorldInput移动资格都true；真实M进入MOVE_TO（没有SDK设置模式），再物理左键一次，实际MOVE_TO回调1／MoveUnitToPlot1／单位操作1，UI和独立Core均读到15,13／行动0。目标为可见、自有、空的相邻陆地，没有战斗、宣战、费用或结束回合。临时绑定和诊断状态均恢复，输入处理器getter缺失的限制保持。

这证明此玩家军队的M及模式完成路径可用，与326文职零请求相对照；单位／地形不同，不比较固定移动成本。军队坐标变化明确来自TEST_PLAYER，不算后台越权；原正常训练存档保持，考古文物serial1／作品15也未变。普通领袖对照及受保护文职的物理M仍待补，不授全TC004／035。[实际原值及清理](../research/baiqi-p6-native67-military-leftmove-positive-evidence-2026-11-04.json)。

## 托管文职物理M：327新增观察与正确资格读取

在上述样本之后，实际对考古学家6422556按M一次：WorldInput原始按下／释放各1，Native键13等于Keys.M；UnitPanel的InputActionTriggered动作35一次，选中身份保持，模式仍为SELECTION，观察器自身错误0。NativeKeys不是Windows键码：VK_M不存在，77过滤计数0不能解释成M没有到达。

原版UnitPanel精确调用为`UnitManager.CanStartOperation(u, UnitOperationTypes.MOVE_TO, nil, false, false)`。后续只读对照在行动力0时，原版对考古学家和勇士都返回true，受保护UnitPanel对考古学家false／勇士true。先前三参数探测对两类单位都报“Instance does not exist”，属于负责人错误签名，不能认作单位消失，更不能倒推它导致更早的M行为。

327原稿传感器异常吞转发及静态Remove签名错误经有限Lua复现、负责人纠正和8项软件检查后才绑定Native；两个上下文已恢复并清空自有状态。输入槽getter仍不存在，恢复已知源码baseline不等于独立读取槽指针。本节补充文职物理M和资格样本，普通领袖及其余输入矩阵仍未完，不授全TC-004／035或全40项通过。[逐案审阅、实际观察和清理](../research/baiqi-p6-mkey327-handoff328-evidence-2026-11-04.json)；接手顺序见[本轮交接](../handoff/2026-11-04.md)。
