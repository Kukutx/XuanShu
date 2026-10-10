---
name: annual-timeline-review
description: Trace consecutive named lunar years of Zi Wei natal four-transformation mappings with a single reusable chart, transparent palace labels, source rules and no claims of real-life future events or complete annual fortune charts.
license: AGPL-3.0
---
# 连续农历年干四化对照

## 适用时机
用户希望把多个年份的传统四化符号排列在同一张出生盘上进行结构对照，或者查看某宫位在哪些年份出现四化标签。

## 操作步骤

1. 确认出生日期、时间、时区、闰月参数与时制；避免在未核对输入时直接论断。
2. 调用 `annual_timeline`，传 `birth`、`start_lunar_year` 和 `years`（1–30）；可选 `focus_palace` 限定十二宫。
3. 逐年展示禄、权、科、忌的星曜与本命宫位。说明这些「年份」是从春节起的农历命名年，而非自然公历年。
4. 读取 `astro://rules/timeline`；必要时调用 `palace_detail`，但清楚区分本命盘静态星曜和年干四化标签。
5. 对同宫出现次数只作结构统计；**不可**据此报告个人生死、疾病、感情、金钱、吉凶或个人前途。

## 限制
本接口不包含流年命宫、限运、流月、流曜或流派完整矩阵，不能称为完整流年命盘。AI 需要把确定性计算与解释性文化表述分栏展示。
