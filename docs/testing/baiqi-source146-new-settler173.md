# 146独立新移民已出生并自主行军，建城继续

2026-11-15，BF-202609141645。[结构化证据](../research/baiqi-source146-new-settler173-837-2026-11-15.json)。同一冷146、119安装哈希保持，源码 `4138d4a`。从161南京自主移民队列持续普通推进，172投入217/220；173初次快照仍8人口、hash0、217投入且新单位未出现在集合，驱动停在输入前。随后独立读回新移民10027070、南京8→7、移民投入归零、下一个单位成本235，并由后台接娱乐中心 `0:173:235`。不能把未稳定的首次173快照当永久生产失败；未单独安装UnitAdded／ProductionCompleted监听，训练归因来自上述连续队列、同城出发和人口配对。

新演员出生地南京11,1，后台 `0:173:259/260/261` 三次MOVE_TO分别55→54→53→97，均有同actor observed回执；独立位置9,2、单编队、健康、pendingfalse／queuednil。0测试玩家文职移动、生产填补或军队护送。此为独立新演员和后台行军正案，尚未新建城。

原8650807仍10,19，ARMED、settle:0:1、0:156:173及846保持；没有清理、重放或取消旧FOUND。公共live2／queued0，私有reserved未知。新移民行军提案已持久保存到845@9,19，原846不被占作新目标。当前UI剩余0.5／readyMove true、readySelect false；另一侧纯Core Classify为LIVE、moves0、dead／delayed false。Core Remember资格要求moves>0，与当前等待相符；两侧读取并非原子，未直接调用会写提案的Remember取返回原因，不能据此断定唯一原因或永久故障。后续普通回合继续跟踪到址／建城。

170第一次普通END返回后仍活动、无待操作单位／阻塞／弹窗。依据既定[普通结束流程](baiqi-test-player-turn-workflow.md)，另记一次原版按钮操作；新鲜CanUnready=false、单位／城攻检查false、选择模式、按钮可用，走原版单参数普通END分支，独立实际171。旧凭证／issued表不重置，0UserForced。167一次军队Step在首个上下文断言前拒绝，具体失败布尔未采集，不能把Core忙猜测写成已证原因；原请求零发令经VM和marker读回分类。保已成功2次SKIP，后继新鲜军队流程只发剩余5次。32双Lua场景通过，显式defer只代表零军令，可能已经做了查看选择。168短暂单位阻塞后来独立读成0／0ready，改为有界只读等待，未补内政。

173另存656528字节，SHA256 `47c89dd26f6f5d2e1bc083cccb96715af53ed3bc10f2d4fc976e82488ee36166`，保存切点0END173，尚未重载。837完整7414+653tokens、5690.8944ms／TTFT1315.4805，原查询Game冒号调用／虚构单位方法／无界遍历拒绝，0raw Native；仅reason分支映射部分参考。Owner漏供真实classifier和Controller桥／proposal定义单列，原请求不改，后补实际只读字段／纯Classify，不授完整源审。累计837／774完整／60length／3transport／867HTTP／30extra，新OpenCode原生0、未知成本null。新城、完整功能、旧ARMED恢复及146性能仍开，Steam0上线／上传。
