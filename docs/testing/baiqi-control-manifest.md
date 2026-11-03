# 行为关闭对照的清单准备

tools/control_manifest.py 提供纯函数 make_control_manifest(source)，只转换传入XML字节，不读写文件、安装模组或调用游戏。

它保留Mod身份／版本及数据库、文字、图标、美术、导入文件等静态内容，移除InGameActions中的AddGameplayScripts、AddUserInterfaces和ReplaceUIScript。保留白绮内容是存档兼容准备，不等于整个模组移除；转换成功也不证明存档可载入或已形成有效性能对照。

本地模型183提供转换循环与报告候选，负责人部分采用并补充根元素、唯一InGameActions及全树执行入口校验。同样7项消费者验证原候选时，4项未拒绝错误根、重复动作组、前端／深层执行入口；负责人版本7项通过。模型185的测试候选误要求删除整个InGameActions，且多个负例同时缺少必需标签，无法隔离目标校验，未采用。

验证命令：

    python -m unittest discover -s tests -p test_control_manifest.py -v

测试包含实际47版清单的静态内容等价和独立的结构反例，没有在游戏安装该对照。[对应证据](../research/baiqi-p6-performance-first-window47-evidence-2026-11-02.json)同时记录当前首次规划窗口的超限与剩余测量边界。正式对照还须冻结全部文件指纹、可载入性和相同玩家指令／游戏状态，并按[性能协议](baiqi-performance-protocol.md)执行。

## 2026-11-03：保留现有接口，记录重复任务错误

负责人未先检索现有实现，向模型217重复派发了清单转换任务，并用AddFile覆盖原测试。工具应用前的存在性检查阻止覆盖现有工具；本轮新增测试原件保存在忽略目录，原测试恢复为当前Git提交字节，现有bytes／报告接口与7项检查保留，普通模组未改。该POST是负责人重复工作，217源码采用0，不能算对照包新进展；新的10项候选检查有5处失败也不属于既有接口回归。覆盖前未提交原像未单独持有，不倒推额外原件。实际对照包安装、可载入性与配对仍待完成。[记录](../research/baiqi-p6-steam-and-duplicate216217-evidence-2026-11-03.json)。

## 2026-11-03：复用旧工具形成56私有对照制品

负责人复用既有make_control_manifest和构建器生成独立私有包，69项清单保持，只有Baiqi.modinfo改变，68项字节相同；静态数据／美术／身份／版本语义保留，清单中的31条已知Lua执行入口移除，原始普通源码未改。这是实际制品校验；尚未安装、读档或执行配对，未使用217重复候选。未执行的Lua文件仍在VFS库存中，须通过实际原生上下文和行为核对排除缓存／加载差异。[制品证据](../research/baiqi-p6-control56-artifact-evidence-2026-11-03.json)。
