# 105官方SDK引用的离线补验

此前完整1598项运行记录为1597通过、1跳过。跳过原因准确地说是没有设置BAIQI_WORKSHOP_SDK_ASSEMBLY环境引用，并非已经确认本机未安装官方SDK；先前口头“缺少SDK”表述不准确。

从当前游戏目录的同级已安装Civ6 SDK中定位现有Steamworks.NET.dll，只向本次子进程提供引用路径。单独运行test_csharp5_compile_and_pure_helpers_without_publisher_main，通过1个测试方法，内含20个本地辅助函数断言。C#5编译明确选择WorkshopOfflineTests入口，未调用BaiqiWorkshopPublisher.Main、SteamAPI.Init、Steam联网或上传。临时测试目录限在忽略目录并自行清理，没有下载或复制SDK入库。

这是一项分别执行的补验，不能改写此前完整运行的跳过原件，也不能写成又跑了一次完整1598。源码105与产品1598项检查清单未变，游戏功能／Steam发布验证不由这个纯辅助函数检查替代。

用户报告其他设备占用Steam仍有效，本次0上线／登录／下载／上传初始化或上传。工坊Alpha2仍内部82。

[结构化补验、程序集摘要与范围](../research/baiqi-p6-source105-official-sdk-offline-single-evidence-2026-11-09.json) · [实际测试入口](../../tests/test_workshop_publisher_managed.py) · [20个离线断言](../../tests/workshop-publisher-offline.cs)
