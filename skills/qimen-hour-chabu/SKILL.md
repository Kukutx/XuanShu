---
name: qimen-hour-chabu
description: Provide deterministic hour-based Qimen Chabu rotating-board calculations with full input provenance and clear distinctions between tradition, calculation and empirically unsupported fortune predictions.
---

# 时家奇门拆补转盘计算

通过 `qimen_hour_chart` 工具取得结果，不应自行猜测局数、节气交接时刻或星门宫位。

## 输入检查

- 明确问事时刻及 IANA 时区；出生时间不是必填概念，`moment.birth_datetime` 在这里表示排盘瞬间。
- 可选 `time_mode` 和出生地经度，但只有提供经度且明确选择太阳时模式才改变时辰。
- 节气交界按实际北京时间/UTC 时间求解；时柱按工具的八字时基计算。时区不明先说明假设。

## 推演步骤

1. 调用 `qimen_hour_chart`；复核 `solar_term`、`fu_tou_branch`、`yuan`、`dun`、`bureau`。
2. 对照 `xun_head`、`xun_instrument`、`zhi_fu_star`、`zhi_fu_palace`、`zhi_shi_door`、`zhi_shi_palace`。
3. 逐宫读取 `earth_stem`、`heaven_stem`、`star`、`door`、`deity` 和 `void`，不要人工挪宫。
4. 如有跨学派疑问，明确本项目仅支持时家拆补转盘、中五寄二，不替换为置闰等其他流派。
5. 报告数据来源和不确定性；**不把星门神的传统象征解释成现实吉凶、医疗、投资、婚恋或事业预测**。

底层计算规则：`astro://rules/qimen`；使用者可对照排盘字段独立核验。
