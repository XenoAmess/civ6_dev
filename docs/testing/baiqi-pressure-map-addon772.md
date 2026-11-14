# 私有压力地图入口／772

2026-11-14，BF-202609141645。[结构化记录](../research/baiqi-pressure-map-addon772-2026-11-14.json)。[前置地形和严格快照](baiqi-pressure-geometry770771.md)上增加 tools/build_pressure_map_mod.py，输出独立四文件地图包和外置元数据，不安装或启动游戏。源文件和输出哈希均取实际字节，避免Windows文本换行差异；发布142的119文件保持原哈希，主334本单元零Native查询／动作。

原版AustraliaScenario的FrontEndActions／AddMap、Base的StandardMaps域和地图大小覆盖提供ABI依据。两个地图均为2大文明、0城邦，固定44×26不横向环绕。入口嵌完整自制核心和布局，include MapEnums取运行时地形索引；GetMapInitData只读，无参数GenerateMap自行组装端口，首次调用前锁定标记，成功／异常都禁止重放。无游戏回调或城市／单位／可见性准备。

5项Owner测试通过：实际四文件／XML引用／字节SHA、Lua51和53两变体无参回调／双方起点／加载零写入、成功和setter异常均不可重放、既有目录／发布目录保护、非法输入在建目录前拒绝。实际CLI包已准备，installed/native_generated均false。另软件构建119文件私有静态control，12文件差异／SHA 3f14bff5ddb7b93448d31d6b7e2c0ce1cc1b4e8cabcc29f8fe06ffcfafb6f70c，未安装，是诊断副本而非产品控制权入口。

772完整stop／DONE／strictJSON，但代码／测试0采用。生成Lua51／53均解析失败，错把含语句模块置表达式右侧；缺MapEnums，回调需要游戏不传的E；UpdateDatabase缺File。四个记录哈希与Windows实际文件不符，metadataJSON有效。原6个普通函数测试所需pytest本机未安装，这是环境事实；标准库逐项执行3通过3错误，三运行例先在eval执行赋值处失败；独立compile另证入口解析失败。Owner完整重写，保留原件。

原版编辑器调度确认Create第二参数为数字地块索引；普通Core适用性和实际读回未验证。ChangePopulation(1)／UnitManager.Kill(unit)有原版例；AddProgress只知成员存在，签名未闭合，零调用。

POST峰1，6230input／3442output、20537.309ms，TTFT949.765ms，单attempt。累计772逻辑／718完整／51length／3最终transport／802HTTP／30extra；维护成功缓存复用，OpenCode原生0，未知成本null。无新Native世界和压力结果，TC036仍PARTIAL。下一步先保存主334，经正式退出与当前实例新鲜离线确认，再准备独立世界；Steam未上线／上传。
