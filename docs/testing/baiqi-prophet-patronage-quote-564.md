# 564只读实机：当前先知的正常赞助报价

99版182回合，公开未领取先知122的普通点数招募资格为false；原版金币赞助与信仰赞助资格均true，实际报价分别为500金币、350信仰。白绮当时持有4534.1015625金币、522.14453125信仰。

**本次只读，没有赞助、扣费、赠送、招募或退款。** 原生资格和价格是当前样本，不能保证未来仍可支付或授予单位。当前BaiqiAdmin只走CanRecruitPerson的普通点数招募，没有自动赞助链；不能把这次报价写成已实现自动采购。

原版GreatPeoplePopup.lua728–738使用CanRecruitPerson(pid,individual)，以及按YieldTypes.GOLD／FAITH的CanPatronizePerson和GetPatronizeCost；253–261又分开处理信仰按钮展示和禁用。诊断只复用这些读取，没有调用原版点击处理器或RequestPlayerOperation，也没有私有模组Bridge。

新工具不进入模组包，20项Lua5.1检查通过。它先验证完整密集时间线再报价，允许有效编号0，将Claimant0视作已领取；异常、稀疏／重复、定义冲突或读取中回合／余额变化保持UNKNOWN。原生cost=nil只标未知、不伪造0；合法1000000展示哨兵保留，不据此称可支付。返回表脱离来源，未知成本对象不会泄露到结果中。

模型564能编译，但把Game静态方法写成冒号调用；完整原版源码已在输入中，原稿20方法出现9个失败事件。只修正三个静态调用的诊断对照仍有19个失败事件：ipairs漏稀疏／额外键、漏已领取重复和定义编号、错误NIL成本状态、无读取末尾新鲜性检查等。失败事件可能在同一方法内有多个子场景，不当成19个独立方法。原稿与此对照均未用于实机，负责人模块通过20项后才只读一次。

模型564完整stop／DONE／JSON，1HTTP、13946+1197=15143 tokens、9.177928秒；累计564任务／526完整／35截断／3最终传输失败、594HTTP／30额外重试，新OpenCode原生生成0，未知成本null。这20项诊断检查不冒充一次新的产品完整回归。

太原182实际开始圣地与后续完工／先知点观察另记；宗教完整链、旧ARMED恢复FAIL和完整40用例仍开放。其他设备正在使用Steam，0模式切换／上线／登录／下载／上传初始化／上传，公开Alpha2仍内部82。

[结构化证据](../research/baiqi-p6-religion564-native-prophet-patronage-quote-evidence-2026-11-09.json)、[只读模块](../../tools/lua/diagnostic_prophet_patronage.lua)、[20项检查](../../tests/test_diagnostic_prophet_patronage.py)、[99生产修订软件切点](baiqi-first-holy-site-production-99.md)。
