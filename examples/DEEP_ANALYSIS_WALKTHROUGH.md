# 可复核演示：立春与农历年界不是同一时间

**XuanShu v.0.1.0 · 测试样本，无关任何用户隐私。**

## 研究输入

```bash
xuanshu deep-review --date 2024-02-07T12:00 --tz Asia/Shanghai --palace 官禄宫 --year 2026
```

用 2024 年 2 月 7 日，是因为它位于 2024 年立春之后、农历甲辰年正月初一（2 月 10 日）之前：

- **八字年柱**按立春年界，标为**甲辰**。
- **原生紫微年干支**按农历年份，标为**癸卯**。
- 不应擅自“修正”为同一个年柱，也不能断言它们相互印证了个人事件。

程序在 `findings[].rule_ids = ["calendar.year_boundaries"]` 的观察中同时给出 `bazi.pillars.year.text` 和 `ziwei.year_pillar` 的实际值与单字段 SHA-256。你可以分别调用 `bazi_chart`、`ziwei_chart` 复算，并对比 `calculation_hashes`。

**重现条件：** 此示例 CLI 未传入性别，所以 `gender=unspecified`，`examples/deep-evidence-reference-2024-02-07.json` 已明确包含全部 `input_parameters`。若改成 `female` 或 `male`，可能触发紫微小限/大限等输出差异，完整紫微 SHA-256 也会随之变化。这是输入不同，不是哈希随机。

## 如何阅读其余观察

1. 四柱与时制：核对年、月、日、时四柱与 `time_basis.mode`；如果出生时制不同，必须先比时制而不是解读不同盘。
2. 十神与藏干：`hidden_stems[]` 列出传统表及无权重的十神对应；**不要**把计数用作个人能力或财运评分。
3. 三方四正：从焦点宫位找两三合宫和对宫，输出准确地支与宫名；主题标签只是传统术语。
4. 生年四化与飞化：两个映射出发点不同，分别列出星名、所落宫和自化标记。只认当前固定全书系四化配置。
5. 年度叠加：2026 年按**农历命名年份**映射静态年干四化，不等于完整 2026 年命盘。
6. 质量与反证：`checks` 为本系统内部一致性测试，通过不能代表外部专业软件认证。

## 独立参考

- [香港天文台农历转换表](https://www.weather.gov.hk/en/gts/time/conversion.htm)
- [香港天文台二十四节气时刻](https://www.weather.gov.hk/en/gts/astronomy/Solar_Term.htm)
- [iztro 星盘 API](https://docs.iztro.com/en_US/posts/astrolabe)
- [iztro 三方四正 API](https://docs.iztro.com/en_US/posts/palace)
- [iztro 流派与四化配置](https://docs.iztro.com/en_US/posts/config-n-plugin)

以上链接均为**方法与日历背景参考**，并未独立运行本引擎的完整 58 星安星审计，绝不能据此声称命运预测可靠。
