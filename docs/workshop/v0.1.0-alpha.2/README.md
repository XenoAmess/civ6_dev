# Alpha 2工坊材料

状态为离线准备，尚未上传。包含[12图解读](screenshot-commentary.md)、[BBCode正文](description.bbcode)、[变更说明](changenotes.bbcode)、[图像来源与生成提示](art-provenance.json)、[包计划](package.json)。产品版本82，现有条目3833805495。

上传前先取得新鲜可靠的其他设备游戏占用状态；不能从本机离线或失败查询推断无人。已有发布授权不等于占用状态已确认。参照[Steam流程](../../steam-offline-workflow.md)。

离线核验：`python tools/prepare_workshop.py --release v0.1.0-alpha.2`。有清闲确认后才运行发布器，先inspect核归属和原图库，再append-preview一次一张，未知结果不重发；新UGC地址换入正文后再次提交／推送、离线核验，再update-content更新现有条目。最后读回、下载比对93文件，立即恢复并只读确认Steam离线。没有新建条目或协议自动接受。新版本意图日志跨页面修改保持同一路径，避免正文编辑隐藏未明提交。
