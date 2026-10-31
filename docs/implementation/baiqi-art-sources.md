# 白绮领袖与顾问美术素材筛选

日期：2026-11-01。执行机器：`BF-202609141645`。本次按用户要求先完整 `git clone`，再检索并查看 [slay-the-spire-vivhite-mod 的 assets](https://github.com/XenoAmess/slay-the-spire-vivhite-mod/tree/94559b5a80ef4bdec8ff8a58042256902d8df713/assets)。源提交为 `94559b5a80ef4bdec8ff8a58042256902d8df713`，`assets/` 有 3,654 个跟踪文件，其中 PNG 1,847 张、JPEG 1 张。数量是目录清点，不代表逐张人工验收。

已找到足够制作静态领袖及可选顾问的人物素材；仅独立宽幅背景使用内置 imagegen 补画一次。此处的“选定”是制作源筛选，不代表已完成 Civ6 资源导出、加载或实机美术验收。玩法原型仍使用原有占位资源。

## 选定制作源

下表上游路径均相对于 `assets/vivhite-ironclad/`；完整路径、SHA-256、真实尺寸与 Alpha 数据见[机器可读清单](../research/baiqi-art-sources-2026-11-01.json)。

| 本机素材名 | 实际尺寸 | 上游路径 | Civ6 用途 |
| --- | --- | --- | --- |
| `leader-master.png` | 1680×2512，RGBA | `custom/character_select/sources/vivhite-character-select-hero-master-v1.png` | 静态领袖主体，供选人、加载与外交前景分别布局 |
| `portrait-master.png` | 1024×1024，RGBA | `generated/evolink-paid/2026-08-28/0006-ui-icon-attempt-01/output.png` | 领袖头像和可选顾问头像的高清母源 |
| `bust-master.png` | 832×1248，RGBA | `generated/evolink-paid/2026-08-28/0011-ui-select-attempt-02/output.png` | 可选顾问半身像或较紧凑的人物展示 |
| `magic-sigil.png` | 2048×2048，RGBA | `custom/character_select/sources/vivhite-character-select-magic-sigil-v1.png` | 可选独立魔法装饰层，不当作宽幅场景背景 |
| `background-master.png` | 1774×887，RGB | 本次内置 imagegen 新生成 | 无人物、无文字的蓝紫金色宽幅背景，供加载／外交背景适配 |

角色保持银发、紫瞳、金色眼镜、蓝蝶、白蓝服装与空手施法的既有设计。没有为换游戏重新设计人物。

本机完整克隆在 `C:\workspace\slay-the-spire-vivhite-mod`，本项目选定素材副本在 `.local-model/art-discovery-20261101/selected/`。副本与上游 PNG 逐字节相同；上游仓库工作区保持干净。原件和制作包均未加入本项目 Git，来源记录与清单可公开共享。

## 筛选依据与实际检查

- 阅读了资产根索引、集合说明、UI 逐项制作记录，以及实际 `VivhiteCharacterAssets.cs` 消费者。`custom/.../sources/` 是独立语义原图，`approved/ui/` 是独立 UI 图；运行时 Spine atlas 页不作为立绘使用。
- 领袖母图与上游付费归档 `0016-character-select-hero-attempt-04/output.png` 哈希相同；魔法印记与 `0017-character-select-magic-sigil-attempt-01/output.png` 哈希相同。
- 本次四张选定透明源图均实际解码为 RGBA，四角 Alpha 为 0。人物原图还在黑、白与深蓝色上做真实 SourceOver 合成并人工查看，未见背景矩形或被直接透明预览夸大的灰色光雾。预览在 `.local-model/art-discovery-20261101/alpha-review.png`。
- 头像原图底边有不透明人物内容，最大 Alpha 254；这是胸肩构图到画布底边，不能误报为无效透明背景。后续圆形头像布局仍需留安全边距。
- `approved/ui/icon.png` 只有 85×85、`select.png` 为 132×195，保留作上游 UI 参考，不放大冒充高清母图。改选其真实原始生成文件 `0006` 和 `0011`。
- `legacy-contaminated/`、被拒绝批次、原版 Ironclad 提取资产、Spine 图集页、死亡姿势及失败截图均未进入选定包。`references/character-design.png` 是带文字和背景的设定板，仅用于确认身份，不作头像成品。

## 背景补图

用户允许必要时使用 imagegen；本次使用内置工具，独立生成一张不透明宽幅背景，以现有领袖母图作配色／风格参考，没有编辑上游人物图。画面为深蓝紫色魔法空间、金色几何线和少量蓝蝶，左侧留暗部供文字、人物单独叠放。生成结果已视觉检查为独立背景，无人物或可见文字。

工具真实返回为 **1774×887**，不是提示中期望的 2048×1024，也尚未导出为游戏目标尺寸。完整最终英文 Prompt、参考路径及工具信息在[清单](../research/baiqi-art-sources-2026-11-01.json)的 `generated_background` 中，本机另存 `selected/background.prompt.txt`。生成原件保留，所选 PNG 已复制到本项目的制作包。

## 之后接入时的目标

按实际 Civ6 消费者分别制作资源，不能把 PNG 复制进模组后就记为显示成功：

1. 用高清头像母源导出领袖所需的 256、80、64、55、50、45、32 像素图标，并检查圆形安全区。
2. 用领袖母图安排选人／加载和静态外交前景，分别检查人物位置、手部、蝴蝶与文字区遮挡。825×1024 是常见静态前景布局参考，不是原图尺寸。
3. 宽幅背景需适配加载的 1920×960 与外交的 1920×1010；当前原稿略小，需要明确记录缩放／裁切后再验效果，不能宣称已有原生高清导出。
4. 若接入白绮顾问，原版 `AdvisorPopup.xml` 的头像显示为 128×128，可复用头像母源。原版其他位置还有 32／48／64／80 像素顾问图标及 22 像素推荐标记；本次没有全局替换原版顾问，也不新增总督人物或晋升图标。
5. 注册 Civ6 图标／前景／背景映射及必要美术包后，验证选人、加载、外交、不同界面缩放和读档。当前这些步骤均 `NOT_RUN`，没有游戏显示通过结论。

尺寸工作流参考 [Sailor Cat 的领袖图像教程](https://steamcommunity.com/sharedfiles/filedetails/?id=2420858843)；顾问尺寸依据本机 Civ6 `Base/Assets/UI/Popups/AdvisorPopup.xml`、`Icons/Icons_Advisors.xml`、`PartialScreens/WorldRankings.xml` 和推荐标记的实际 XML 消费者。

## 本地模型与经验

本次为尚未完成的素材映射派发两次真实本地模型 HTTP，请求互相顺序执行，实际在途峰值 1，运输重试 0。首轮 `finish_reason=length`，保留原件、拒绝采用、不拼接；缩窄后得到完整 SSE／`stop`／合法 JSON。仅部分采用领袖母图与排除 atlas 的建议；模型将带文字的设定板推荐为头像，负责人拒绝，依据上游逐项记录与实际图片选择 `0006` 高清原图。缓存数据和服务端实际推理并行均未知，保持 `null`。精简回执见清单，完整请求与 SSE 留在被忽略的本机目录。

可复用经验：先区分图集与独立源，追到小 UI 图的高清原稿；查看器里的透明图 RGB 光雾不能替代真实 Alpha／SourceOver 检查；生成工具的期望尺寸与实际返回尺寸分开记录。没有因素材筛选修改或测试玩法代码。
