---
name: qimen-reference-audit
description: Cross-validate XuanShu hour-Qimen roots and every supplied palace field against user-provided independently obtained reference plates with exact mismatch paths and school provenance.
license: AGPL-3.0
---
# 奇门独立参考盘逐宫核对

用 `qimen_reference_audit` 校验明确流派和出生时刻的独立参考盘，不能把玄枢自己生成的盘当作外部独立证据。

1. 收集参考盘出处、原日期时间与时区、排盘流派（拆补、置闰、转盘或飞盘），记录阳遁/阴遁及局数。
2. 在 `root_fields` 填入已经确认的字段。`palaces` 各宫只能填有出处的地盘/天盘/暗干、九星、八门、八神、空亡等实际字段。
3. 调用 `qimen_reference_audit`；逐宫列出 `mismatches` 以及 `compared` 总数，不对缺失字段做“通过”或“全盘一致”的推断。
4. 若不同流派差异导致的合法分歧，区分流派参数错误、天文节令差异与真实算法缺陷。
5. 全部结果仅为传统术数算法比对，不得声称未经验证的现实吉凶预测。
