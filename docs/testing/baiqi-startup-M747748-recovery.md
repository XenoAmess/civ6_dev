# M启动卡住、747／748原稿与同包N恢复

2026-11-14，BF-202609141645。[机器事实、原稿审阅与恢复切点](../research/baiqi-startup-M747748-recovery-2026-11-14.json)。142 M私有正式包SHA256 `a04706aeeda55d9fa0e7ba07d6c1b0f1610cd286345e9d7aef9d51f4549cc555`已按119文件逐字核对、Steam新鲜后台离线确认后启动，但原生4318／4319 LSQ均超时，主界面未取得合格上下文。进程持续单核活动、日志停在成功重配置及art files之后；系统前台是DWM的Ghost未响应窗口，原有截图／焦点守卫正确拒绝，未绕过。M零CMD／载入／Continue／END／存档输入、零采样，不是142实机通过或游戏功能FAIL。

747原稿完整stop／DONE／JSON，但把psutil线程tuple当有cpu_times方法对象，原样执行在OpenProcess前失败；也复用旧线程列表、误用dbgshim替DbgHelp、无独占事前凭证、未比实际exe路径，0采用。Owner按[微软MiniDumpWriteDump文档](https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/nf-minidumpapiset-minidumpwritedump)从独立Python进程采普通转储，未写游戏内存或发游戏输入。转储345902字节、SHA256 `39a8df52847300ee4abc612f4f953cfd03f9482dcd60800457271b01a3f3f2af`，只保留忽略目录；原始内存／栈／路径不公开。线程8244在2.037662秒采样里CPU增2.046875秒。

748完整原稿把合法的重复UnusedStream0目录当成重复关键流，真实转储上直接拒绝；还输出完整路径、只取首个重叠模块、覆写输出及硬编码无关成功回执，0采用。Owner根据微软公开[模块结构](https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_module)、[线程结构](https://learn.microsoft.com/en-us/windows/desktop/api/minidumpapiset/ns-minidumpapiset-minidump_thread)和[x64上下文](https://learn.microsoft.com/windows/win32/api/winnt/ns-winnt-context)独立校验SHA／边界／体系结构／唯一范围，读得133模块／34快照线程；CPU采样当时38线程是另一时刻，不能要求一致。单点RIP映射ntdll.dll+0x9deb4，只是上下文地址，不是解栈或卡住原因证明。

Owner初次关闭守卫也误用win32gui不存在的方法，在任何关闭事前凭证前失败，改用实际typed user32接口后才执行。随后只向精确自有M窗口投递一次WM_CLOSE，15秒未退出，才终止这个启动超过十分钟、没有载入游戏的自有进程；这是挂起启动恢复，不冒称静止正常退出残留。Steam客户端和其他人的游戏均不动。

N未重装、未改代码／缓存／配置，复用同一142包；启动前离线证明年龄0.004897秒。N主界面LSQ已唯一合格，原85载入ACK一次true；尚无完整142采样／性能／全功能通过。不能因为同包N可启动就确定M的唯一原因，失败原件不追改。

747／748各一次完整流、顺序峰1，tokens／耗时见JSON；累计748／695完整（含历史JSON拒绝）／50length／3最终transport／778HTTP／30extra。Nov14维护成功cache复用、OpenCode原生0，未知缓存／Owner主动成本／净节省null。
