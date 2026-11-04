# 白绮 Alpha 1 工坊发布包

当前展示页为[第二版玩法图文](README.md)，正文与画廊各有7张实机图。[公开HTML核验](public-readback-revision2.json)确认正文确实生成7个图片元素，7张远端图片逐字节匹配仓库；[当前上传清单](package-current.json)与[第二版BBCode](description.bbcode)对应。下面关于2张图和5219字节的内容是首次发布过程，冻结证据不回写成第二版。

第二版先批量补图收到Timeout，核对仍为2图后重试收到Busy；客户端日志同时有断线与SDK暂存文件冲突，根因未单独证明。随后改用新的本次暂存文件名，每次补1图并读回，最终为7图；最后一图首次FileNotFound与断线同窗，自动重连后重新核对6图再补齐。没有删除或修改Steam账号／Cloud配置，没有重建条目或重传游戏内容。失败回执与成功分开保留。

[第二版更新说明源码](changenotes-revision2.bbcode)随页面提交，但公开更新日志当次查询仍只显示初次Alpha条目；不把SDK提交ACK当作新增日志已可见。游戏仍内部74，87个产品文件未变。开发上传入口按当前清单准备7图，采用`append-preview`逐张追加与`update-page`更新正文；已发布条目不得再运行创建流程。

内容对应已发布的[GitHub v0.1.0-alpha.1](https://github.com/XenoAmess/civ6_dev/releases/tag/v0.1.0-alpha.1)，内部74。**已同步公开到[Steam工坊](https://steamcommunity.com/sharedfiles/filedetails/?id=3833805495)**，条目ID `3833805495`。最初按用户报告的占用情况暂停；用户明确确认无人游戏后才继续。详见[发布回执](publication-status.json)。

- [介绍BBCode](description.bbcode)：玩法、强制托管、实机解读、未验风险、安装及反馈。
- [更新说明BBCode](changenotes.bbcode)：实际提交更新时使用，文件准备不代表已发布。
- [实机图及逐图解读](screenshot-commentary.md)：两张原始游戏客户区图，画廊顺序／标题／说明见[上传清单](package.json)。
- [宣传封面](media/preview.jpg)、[生成原图](media/cover-source.png)、[来源与压缩记录](art-provenance.json)。宣传插画与真实截图有明确标注。
- [准备验证](verification.json)仅记录上传前本地检查；[公开页读回](public-readback.json)核对完整中文正文、更新日志及三张图；[实际工坊下载验证](download-verification.json)确认87个文件与Alpha逐项哈希一致。这些不代表全部游戏用例通过。

在仓库根目录用CMD执行：

```bat
python -X utf8 tools\prepare_workshop.py
python -X utf8 tools\prepare_workshop.py --stage dist\workshop\alpha1
```

工具仅在本地验证和准备上传目录，不连接Steam、不登录、不初始化Steam API、不切换模式、不执行上传。`content/`仅含发布清单的87个游戏文件；宣传图与说明放旁边，避免把开发资料或私人记录装进游戏模组。已有目标仅在内容完全一致时复用，不覆盖不同文件、不清理其他目录。

`package.json`是上传前冻结的准备清单，其中空条目ID、拟定标签和PREPARED状态不作为当前发布状态；实际ID、标签、结果以发布回执为准。已有工坊条目后不要重新创建。

## 官方SDK上传源码

[Python入口](../../../tools/publish_workshop.py)编译[C#桥接器](../../../tools/BaiqiWorkshopPublisher.cs)，引用用户本机正式安装的Civ6 SDK `ModUploader` 目录。SDK DLL只复制到忽略目录，不入库或随模组分发。运行这套开发上传工具需要Windows .NET Framework编译器；玩家游玩没有这一要求。

仅在已核对远端无人游戏且通过Steam正式菜单上线后，才可初始化上传SDK。例如将 `CIV6_SDK_ROOT` 设置为本机SDK目录，再读取现有条目：

```bat
python -X utf8 tools\publish_workshop.py --sdk-dir "%CIV6_SDK_ROOT%" --remote-idle-confirmed --mode readback --item-id 3833805495
```

`--remote-idle-confirmed`记录操作者确认，工具本身不证明远端无人游戏。它不自动切上线、不登录、不强制夺取会话，也不接受法律条款。正式占用信息出现矛盾时应停止。`create-draft`会查询已有白绮条目，并在创建／提交前独占写入意图日志；结果未知时不得删除日志重跑。`publish`先读回完整标题、正文和两张附图再公开；`download`使用游戏消费端289070上下文、低优先级、无需订阅。私有回执在 `.local-model/steam/workshop-alpha1/`。

本次官方图形上传器只允许首次设置封面、标签和可见性，不能填完整长正文和两张附图，因此最终使用其自带Steamworks.NET托管接口。旧SDK固定字符数组按Windows ANSI读回会产生中文乱码；桥接器按该SDK实际结构偏移读取原生UTF-8，未重传或改坏远端中文。独立匿名Web API也验证中文全文一致。

## 上传与核验流程

1. 在任何Steam上线、下载SDK、启动上传器或Steam API初始化之前，先按用户2026-11-05要求获得新鲜、可靠的账号远端游戏占用状态。区分本机自有验收游戏与其他设备的游戏；未知或有人游戏均停止后续联网发布步骤。好友隐身、空的本机进程、缓存配置、缺失社区状态与HTTP错误均不证明无人游戏。
2. 占用已可靠排除后，才通过Steam正式入口短暂上线。上传工具优先使用官方Civ6 Development Tools中的Workshop Uploader；本机尚未安装SDK，下载同样受第一步约束。不要通过启动游戏、SteamAPI_Init或强制登录来“试探”占用，不关闭他人游戏。
3. 先核对已有条目和模组ID，避免重复创建。使用`content/`、`preview.jpg`、清单中的标题／标签、完整介绍及更新BBCode，添加两张真实图与逐图说明。选定《风云变幻》依赖；正式提交前核对工具实际可用字段。当前未验证上传器界面，清单字段不是已成功填写的证据。
4. 提交一次后保存回执。若结果不明，先查询是否已经创建，禁止盲目重复创建／发布。新条目检查可见性、正文、缩略图、两张图、更新日志和依赖。用官方`GetPublishedFileDetails`读回标题／正文／文件信息，并独立访问公开详情及更新日志；只有真实订阅下载、核验文件哈希后才能宣称工坊安装文件验证通过。
5. 发布步骤完成或中止后立即通过正式入口恢复离线，再以后台只读方法确认当前实例；不把菜单操作ACK或好友离线当作确认。随后继续独立游戏验收。

上传规则依据[本项目Steam流程](../../steam-offline-workflow.md)及用户“不顶号”的明确限制。官方参考：[Civ6开发工具公告](https://steamcommunity.com/games/289070/announcements/detail/576861888092920827)、[Steam UGC接口](https://partner.steamgames.com/doc/api/isteamugc)、[Workshop实现说明](https://partner.steamgames.com/doc/features/workshop/implementation)。图片按官方UGC附加预览限制准备为小于1MB；具体上传器限制仍须以实际界面及成功回执验证。
