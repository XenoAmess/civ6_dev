# P5 验收记录

2026-11-01，机器 `BF-202609141645`，游戏 Build `15296837`，单人《风云变幻》。本轮从 `5bbda83` 干净工作区开始，Steam 后台只读确认离线后启动。完整请求、截图、Tuner 回执与存档保存在本机忽略目录。

## 冷启动与恢复

P4 最终整包首次完整冷启动成功，进入 `Baiqi_P4_20261031_DelegatedCapture`：T2、金币 1555、两座城市、旧经营表 nil、清理版本 2。三个已完成征城重复请求均返回 duplicate，余额 `1555 → 1555`；旧 granary 请求在效果之前返回 invalid_target。该窗口通过，不能据此将所有故障恢复场景标为通过。

## 发现的控制权缺陷

完整科技树与快捷科技选择器是不同 UI 上下文。P4 未包裹 `ResearchChooser`／`CivicsChooser`。实际在 ResearchChooser 调用原版按钮回调，制陶术合法，研究从 index 2 变为 index 0，证实人工可绕过托管。

修复增加两个独立上下文，先安装 UIGuard，再包含原版脚本。风云变幻的 ResearchChooser 只有 `_Expansion1` 版本，加载器正确选择该版本，不能凭规则集拼出不存在的 `_Expansion2`。同时覆盖有直接单位操作入口的 UnitFlagManager；此处确认的是上下文未覆盖，未把源码可达路径直接说成已实测文职移动成功。

新增测试验证原版初始化期间捕获的回调也被拦截、普通领袖仍能写入、只初始化一次，以及单位旗帜中军队可操作而文职不可操作。全套 **63 个软件测试方法通过**。修复后实机结果继续追加，不提前记为 PASS。

## 夹具核对

资本周围实际为草原／平原和森林、沼泽，不能根据画面颜色推断为全部雪地或冰盖。原生建造者建议为空这一观察成立，但尚不能据此判定控制器缺陷。实际队列 `GetAt(0)` 是 table，含 Directive、BuildingType、Location、Modifiers；原版 ProductionHelper 按 Directive 读取 UnitType／BuildingType／DistrictType，不能混用数组位置或假造 hash 字段。

本轮仍须执行修复后的冷启动、正常生产／建造者／政策／扩张窗口。完整 40 项游戏用例未全部通过。
