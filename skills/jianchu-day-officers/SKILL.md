---
name: jianchu-day-officers
description: Independently compute and audit traditional Jianchu twelve-day-officer labels across dates with solar-term-month and sexagenary-day provenance, explicit transition-day warnings and no claims about auspiciousness.
license: AGPL-3.0
---
# 建除十二值日历法核对

## 适用时机
用户想知道某天的传统「建、除、满、平、定、执、破、危、成、收、开、闭」值日标签，或比较多个日期的历法结构。

## 执行步骤

1. 先确认公历日期范围，统一按 `Asia/Shanghai` 的北京时间解释日期。不要擅自用本地设备时区替换。
2. 使用 MCP 工具 `day_officers`，提供 `start_date`、`days`（1–93）和可选 `filter_officers`。保留输出 `day_pillar`、`month_branch_at_noon`、`officer` 和 `jie_boundary_on_date`。
3. 当边界标记为真时，提示该日交节前后采用的月建可能改变；如需精确时刻，再调用 `solar_terms` 或相关节令计算。
4. 引用规则资源 `astro://rules/jianchu`。任何传统标签都不能描述为真实吉凶、婚姻成败或医疗、财务收益的证据。

## 避免的错误
不要从星期、农历初一或月相直接推算值日；十二值日按节令月建和干支日支计算。不能把筛选结果写成「最佳签约日」。不要向来源平台请求隐藏接口或复制其软件资源。本项目拥有独立的历法算法。
