# 忠诚诊断：只读选址警告与本方时代

这两个工具只采集信息，不在模组的104文件安装包中，不会授予移动、建城或内政命令权限。源码仍92，[成都130长期FAIL](baiqi-expansion-stability-fail130-92.md)保持。[请求、审阅、资格和实机分账](../research/baiqi-p6-loyalty-information541542-evidence-2026-11-08.json)。

[城址警告读者](../../tools/lua/settlement_warning_info.lua)只读已揭示且当前可见的单个本方／无主非城市地块；使用原版静态Map接口、plot的self方法和按pid取得的可见性对象，不迭代警告全表、外国城市或隐藏地图。没有条目返回UNKNOWN，不能改成0；KNOWN_NONNEGATIVE也不代表城址安全或可以发令。它保留include消费者导出；实际Native诊断在局部同名变量内执行，避免向产品上下文发布全局。

541原稿能编译，但实际API夹具有9个失败反例，整稿拒绝。负责人独立版本34场景通过，125与130各读取三个既有目标都为UNKNOWN；旧91一个可见目标的原生−20不填补新读者的负值正案，也不证明警告完备性、缓存期限或未来压力。读者没有接入产品选址。

[本方时代读者](../../tools/lua/own_age_info.lua)使用原版Game.GetEras静态入口和时代对象的self方法，只读当前本方时代、时代得分、倒计时及三种年龄标记；采样前后复查身份、回合、规则与全部字段。Heroic与Golden可同时真，Dark与任一并存视为UNKNOWN；倒计时−1有效。未知方法、异常、无穷数、采样内变化均保持UNKNOWN，Standard不读取时代对象。采样一致不证明原生缓存新鲜或历史因果。

542原稿能编译，但7个反例失败。独立可证缺陷有：未拒绝Dark与Golden／Heroic冲突，虽然它的测试文字声称会拒绝；原生库索引异常未受保护；无穷值可通过floor判断；环境元表可执行。另一个Standard字符串反例含负责人输入问题：原合同只写了裸词Standard，没有明确RULESET_STANDARD常量。这项歧义归负责人，不把它全部算作模型错误；依据已有项目和运行规则修正，没有为了该项重投模型。

负责人独立版本20场景通过，130实际返回：RULESET_EXPANSION_2、时代Index4、得分42、倒计时−1、Heroic=false、Golden=false、Dark=true，即黑暗时代。成都同时4.0625／−15。**这是130本方状态，不是压力突变原因已证。** 128对照档已完成读取：时代Index3、得分41、倒计时1、Heroic=true、Golden=true、Dark=false，即英雄时代；成都17.96875／+1.09375。130为时代Index4／黑暗时代，证明两采样之间本方时代／年龄发生变化，但未直接读取精确切换回合。安装的原版Expansion1_Leaders.xml将黄金／黑暗年龄条件分别绑定到每公民忠诚修正Amount 0.5／−0.5；这支持继续检查时代影响，不能据此单独算出−15或排除其他压力变化。[正式读取与限定](../research/baiqi-p6-loyalty-age128130-comparison-evidence-2026-11-08.json)。

本次Loading期间曾拒绝hung窗口截图、只读LSQ超时，均未输入。第一份Continue区域全字节比对与旧参考不一致，执行在点击intent之前停止；看过新原版Continue画面后，用新参考再核新鲜截图、所属进程／前景／几何／哈希，点击一次。没有重发Load；原生就绪证据确认实际128，移民／目标保持，无新增END／军队SKIP／手补内政。当前为已保存128的活动世界，原130失败档保留未加载。

[两项定向测试](../../tests/test_diagnostic_loyalty_information.py)共54个Lua5.1场景通过，实际源码与独立资格源码字节一致。包括static／self、userdata库、可见性先于地块元数据、隐藏／外国目标拒绝、缺条目、元表／函数不执行、阶段变化、正确本方身份及异常保护。只有2个unittest方法，54是内部子场景，不加到产品既有1321通过里冒充全量重跑。

```bat
python -X utf8 -m unittest discover -s tests -p test_diagnostic_loyalty_information.py -v
```

542为canonical普通HTTP一份stop／DONE／合法外层JSON；原稿0Native／0产品采用，负责人版本仅诊断。累计542逻辑／506完整外层JSON／33截断／3最终传输失败／572HTTP含30额外尝试，OpenCode原生生成0。Nov8首500成功每日检查的1.19.5维护缓存复用，未知缓存与人工成本null。原始请求、SSE、候选、机器日志和私人存档留忽略目录。其他设备仍占用Steam，0上线／登录／下载／上传初始化／上传／模式切换，公开Alpha2仍82／12图。
