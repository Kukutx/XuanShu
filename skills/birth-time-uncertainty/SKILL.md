---
name: birth-time-uncertainty
description: Use this skill when the user knows an approximate birth time rather than an exact minute and needs a bounded, explicitly sampled BaZi and partial Zi Wei chart sensitivity comparison, acknowledging gaps between samples and historical timezone uncertainty.
license: AGPL-3.0
---
# 不确定出生时刻与规则敏感性分析

## 工作流程

1. 确认出生日期、当地钟表时间、IANA 时区和误差范围（例：前后 30 分钟）。如需太阳时则确认经度，不猜测位置；重复 DST 时间必须提供正确的 UTC offset。
2. 用 `birth_time_window` 工具填入 `birth`、`uncertainty_minutes`（5–120）和 `sample_every_minutes`（5–60）。建议在区间临近时辰或节令边界时使用较小间隔。
3. 先列出采样总数、观察到的不同四柱/命宫/身宫/五行局及对应观测范围，再解释具体变化发生在何处。不要把未采样的区间说成完全验证。
4. 如果存在经度问题，结合 `time_basis_audit` 对比钟表时间、平太阳时、真太阳时，这与误差区间属于不同维度。
5. 明确本工具不宣称预测效力，不输出命盘优劣或概率。无法确定精确出生时刻时，不应编造唯一结论。

参考资源：`astro://rules/birth-window`。
