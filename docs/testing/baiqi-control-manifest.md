# 行为关闭对照的清单准备

tools/control_manifest.py 提供纯函数 make_control_manifest(source)，只转换传入XML字节，不读写文件、安装模组或调用游戏。

它保留Mod身份／版本及数据库、文字、图标、美术、导入文件等静态内容，移除InGameActions中的AddGameplayScripts、AddUserInterfaces和ReplaceUIScript。保留白绮内容是存档兼容准备，不等于整个模组移除；转换成功也不证明存档可载入或已形成有效性能对照。

本地模型183提供转换循环与报告候选，负责人部分采用并补充根元素、唯一InGameActions及全树执行入口校验。同样7项消费者验证原候选时，4项未拒绝错误根、重复动作组、前端／深层执行入口；负责人版本7项通过。模型185的测试候选误要求删除整个InGameActions，且多个负例同时缺少必需标签，无法隔离目标校验，未采用。

验证命令：

    python -m unittest discover -s tests -p test_control_manifest.py -v

测试包含实际47版清单的静态内容等价和独立的结构反例，没有在游戏安装该对照。[对应证据](../research/baiqi-p6-performance-first-window47-evidence-2026-11-02.json)同时记录当前首次规划窗口的超限与剩余测量边界。正式对照还须冻结全部文件指纹、可载入性和相同玩家指令／游戏状态，并按[性能协议](baiqi-performance-protocol.md)执行。
