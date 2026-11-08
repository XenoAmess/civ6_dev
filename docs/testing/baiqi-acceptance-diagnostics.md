# 白绮验收诊断工具

这些模块位于tools/lua，不打进96文件的模组。测试玩家或验收脚本显式传入当前实例的API；产品不依赖这些工具。三个模块均不补选生产、不移动单位、不修改存档属性。

- [生产快照](../../tools/lua/diagnostic_production_snapshot.lua)：M.Queue(E,city)，E含GameInfo／MilitaryFormationTypes，只读自有0城市。明确区分EMPTY与UNKNOWN；按当前hash读取四类真实进度和成本，单位区分标准／军团／集团军。允许Native userdata、保留进度超过成本的真实队首，异常和无穷值不能伪装为空队列。19项边界。
- [区域前请求观察](../../tools/lua/diagnostic_district_placement.lua)：M.Install(E)，E含CityManager、CityOperationTypes、GameInfo、PlayersVisibility、Map、Game、guard。只观察玩家0可见自有地块、实际自有城市ID，回合40—160、最多16条；外层guard必须核验准确世界／版本／场景。先记录不可变原地块，再原样转交已有请求一次，保留self、尾随nil、函数返回和原异常，不新增游戏命令。Restore只恢复自身包装；第三方换过绑定则拒绝覆盖。26项边界。
- [战略资源快照](../../tools/lua/diagnostic_resource_snapshot.lua)：M.Read(E)，E含Game／Players／GameInfo，严格只读本方0。按原版资源Type读取库存、上限、预留、积累、进口、加成及单位／电力需求，元数据最多256条；异常、nil、NaN、无穷、重复或空集合为UNKNOWN，不补0、不返回部分KNOWN、不钳制超额真值。只读账面资源，不读地图资源分布。20项边界。

[生产与区域测试](../../tests/test_baiqi_acceptance_diagnostics.py)、[资源测试](../../tests/test_diagnostic_resource_snapshot.py)使用lupa.lua51：4个测试方法、65个逻辑边界。命令为python -m unittest discover -s tests -p test_baiqi_acceptance_diagnostics.py和python -m unittest discover -s tests -p test_diagnostic_resource_snapshot.py。它们是API合同检查，实机结果另见[99—119窗口](baiqi-five-city-twenty-turns-87.md)。

API依据是本机原版GS CitySupport209—307、UnitPanel2252，以及TopPanel_Expansion2 44—55、ReportScreen_Expansion2 83—99。第三方游戏代码仅本机读取，不上库。区域BEFORE_REQUEST_NOT_ACK只是原请求前的见证；请求返回、Map落地和城市区域完成必须分别核验。观察只覆盖所安装上下文及安装期间，0行不能推断其他上下文没有请求。资源工具119以后才可采样，不能追认缺失的99—118库存。
