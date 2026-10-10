---
name: annual-four-transformations
description: Explain rule-based Zi Wei Four Transformations overlay for a selected named Chinese lunar year on the natal chart, with transparent school assumptions and without pretending it is a complete annual forecast.
license: AGPL-3.0
---
# 指定农历年干四化叠加

处理某个农历年的「禄权科忌」与本命盘星曜宫位映射，而不是完整流年命盘。

## 工具步骤

1. 确认出生本地时间与时区，并确认目标 **农历纪年**（目标公历某日需先辨别是否已过春节）。
2. 调用 `annual_transformations`，参数 `birth` 和 `lunar_year`（1901–2099）。
3. 报告目标年干支、四化星名称及其所落 **本命盘** 宫位；与 `ziwei_chart` 的本命四化区分。
4. 若需相关宫位内容，可调用 `palace_detail` 获取三方四正与原星曜组合。
5. 对象为公开传统文化规则；不要给出个人流年吉凶、疾病、财务或人生保证。

## 适用限制

没有完整流年命宫、限运、流曜、命宫变化和流派差异矩阵。本项目仅提供干四化标签的可重复计算映射，绝非完整流年推演。
