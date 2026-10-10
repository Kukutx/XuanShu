---
name: solar-time-audit
description: Use this skill to compare civil clock time, mean solar time, and apparent solar time for BaZi/Zi Wei charts using a birthplace longitude, with explicit IANA timezone and DST validation.
license: AGPL-3.0
---
# 出生地经度与时间修正规则核对

适用于「北京时间和真太阳时为何命盘不同」「接近子时生的人何时换日」等规则核对场景。

## 工具步骤

1. 要求民用出生时间、IANA 时区和出生地经度（东经正、西经负）。不猜测经度，不把城市名当成精确位置。
2. 调用 `time_basis_audit`，传入 `birth` 的 `birth_datetime`、`timezone`、`longitude`。它返回三种时基的有效当地时间及四柱、命身宫。
3. 必要时调用 `rule_comparison`，在 `original` 与 `alternative` 里显式改变 `time_mode` 或 `late_zi_day_rollover`。
4. 展示有何具体变化、原始 UTC 瞬间是否保持一致。对夏令时重复时间要求明确 UTC offset。
5. 查询 `astro://rules/solar-time` 规则资源。

## 注意

真太阳时均时差由 Swiss Ephemeris 计算；时区与经度假设可影响边界，不能据此断定某种时基拥有预测效力。不得推断人生事件；未提供真实经度就不能声称已进行真太阳时修正。
