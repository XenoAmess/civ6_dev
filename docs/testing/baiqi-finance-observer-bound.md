# 财政与单位被动观察器：长窗记录上限

`tools/lua/diagnostic_finance.lua`的Install现在接受可选`maxRecords`，省略仍4096；仅允许1至16384的有限整数。非法值在读取namespace或API表之前拒绝，已验证的上限保存在闭包中，外部修改返回handle不会取消界限。超限只丢证据并增加drops，仍向原函数转发一次，不能以截断窗口授予完整验收通过。

14个针对方法通过，其中新增4个，覆盖小上限后的继续转发及handle篡改、16384边界、非法值零getter／零发布／零绑定、独立namespace的双层观察与精确LIFO恢复。尾nil、原返回及异常的原有检查保持；Lua5.1编译通过。这是工具检查，没有新跑完整产品套件。

现场旧观察器仍按原4096上限运行，源文件修改不会热改其闭包。为避免撤除后重新安装造成观察空隙，可在另一namespace套上更大上限观察器；所有命令依次经过两层，原函数仍只执行一次。先读回旧窗口的切点，再装外层、读双方counts衔接；结束时必须先Restore外层再Restore内层。内层提前Restore应拒绝且不部分撤除。只有原生现场完成这些步骤后才能记录实机通过。

580原模型diff损坏且验证位于getPublished之后，未采用。负责人修正如上。仅诊断工具变化，不变更模组105，零Steam操作。

[本轮软件与144原生证据](../research/baiqi-p6-source105-beijing-final144-and-diagnostic-bound-evidence-2026-11-09.json)
