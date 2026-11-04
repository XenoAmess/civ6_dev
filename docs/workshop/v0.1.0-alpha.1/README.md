# 白绮 Alpha 1 工坊发布包

内容对应已发布的[GitHub v0.1.0-alpha.1](https://github.com/XenoAmess/civ6_dev/releases/tag/v0.1.0-alpha.1)，内部74。**Steam工坊尚未上传，也没有工坊条目ID。** 最初占用查询不可用，用户随后确认有人游戏，已暂停；现用户明确确认无人游戏并要求继续上传。具体进展见[状态回执](publication-status.json)，准备文件本身不代表已同步发布。

- [介绍BBCode](description.bbcode)：玩法、强制托管、实机解读、未验风险、安装及反馈。
- [更新说明BBCode](changenotes.bbcode)：实际提交更新时使用，文件准备不代表已发布。
- [实机图及逐图解读](screenshot-commentary.md)：两张原始游戏客户区图，画廊顺序／标题／说明见[上传清单](package.json)。
- [宣传封面](media/preview.jpg)、[生成原图](media/cover-source.png)、[来源与压缩记录](art-provenance.json)。宣传插画与真实截图有明确标注。
- [准备验证](verification.json)：描述标签、图片、87个核心文件与已发布Alpha哈希核对；不授Steam上传成功或游戏全验通过。

在仓库根目录用CMD执行：

```bat
python -X utf8 tools\prepare_workshop.py
python -X utf8 tools\prepare_workshop.py --stage dist\workshop\alpha1
```

工具仅在本地验证和准备上传目录，不连接Steam、不登录、不初始化Steam API、不切换模式、不执行上传。`content/`仅含发布清单的87个游戏文件；宣传图与说明放旁边，避免把开发资料或私人记录装进游戏模组。已有目标仅在内容完全一致时复用，不覆盖不同文件、不清理其他目录。

## 上传与核验流程

1. 在任何Steam上线、下载SDK、启动上传器或Steam API初始化之前，先按用户2026-11-05要求获得新鲜、可靠的账号远端游戏占用状态。区分本机自有验收游戏与其他设备的游戏；未知或有人游戏均停止后续联网发布步骤。好友隐身、空的本机进程、缓存配置、缺失社区状态与HTTP错误均不证明无人游戏。
2. 占用已可靠排除后，才通过Steam正式入口短暂上线。上传工具优先使用官方Civ6 Development Tools中的Workshop Uploader；本机尚未安装SDK，下载同样受第一步约束。不要通过启动游戏、SteamAPI_Init或强制登录来“试探”占用，不关闭他人游戏。
3. 先核对已有条目和模组ID，避免重复创建。使用`content/`、`preview.jpg`、清单中的标题／标签、完整介绍及更新BBCode，添加两张真实图与逐图说明。选定《风云变幻》依赖；正式提交前核对工具实际可用字段。当前未验证上传器界面，清单字段不是已成功填写的证据。
4. 提交一次后保存回执。若结果不明，先查询是否已经创建，禁止盲目重复创建／发布。新条目检查可见性、正文、缩略图、两张图、更新日志和依赖。用官方`GetPublishedFileDetails`读回标题／正文／文件信息，并独立访问公开详情及更新日志；只有真实订阅下载、核验文件哈希后才能宣称工坊安装文件验证通过。
5. 发布步骤完成或中止后立即通过正式入口恢复离线，再以后台只读方法确认当前实例；不把菜单操作ACK或好友离线当作确认。随后继续独立游戏验收。

上传规则依据[本项目Steam流程](../../steam-offline-workflow.md)及用户“不顶号”的明确限制。官方参考：[Civ6开发工具公告](https://steamcommunity.com/games/289070/announcements/detail/576861888092920827)、[Steam UGC接口](https://partner.steamgames.com/doc/api/isteamugc)、[Workshop实现说明](https://partner.steamgames.com/doc/features/workshop/implementation)。图片按官方UGC附加预览限制准备为小于1MB；具体上传器限制仍须以实际界面及成功回执验证。
