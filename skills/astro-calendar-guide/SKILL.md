---
name: astro-calendar-guide
description: Use this skill to check Chinese lunar dates, leap lunar months, day stem-branch cycles and 24 precise solar terms for a date or range via XuanShu MCP.
license: AGPL-3.0
---
# 节气与农历日期检查

## Procedure

1. If the user gives a specific Gregorian date or range (1901–2099), call `calendar_days` with `start_date` and `days` 1–31. Split longer queries into bounded periods.
2. When querying all 24 solar terms of a year, call `solar_terms` with an integer `year`.
3. Present Gregorian date, lunar year/month/day with leap-month flag, day pillar, and exact time when a solar term occurs. Solar-term timestamps are `Asia/Shanghai`.
4. Each `calendar_days` day also has `festivals`: traditional festivals (闰月 repeats none), 三伏 periods and 数九 nines, each with `rule`, and `day`/`length` for a fu or nine. Quote the rule when naming one. A `caution` appears when the solar term the count starts from falls within half a minute of midnight (only the 1951 winter solstice in 1901–2099); say the start may differ by a day.
5. Distinguish the **lunar year boundary** at Chinese New Year from the **BaZi year boundary** at 立春.
6. If the user asks for an auspicious date, explain this version has no 黄历宜忌/吉凶 engine. Do not invent one; provide only calendrical facts and ask what practical constraints should determine scheduling.

## Example arguments

```json
{"start_date":"2024-02-04","days":14}
```

## Boundaries

Dates are computed using a modern standard China UTC+08 convention. Some historical conventions and rare years can differ. The engine does not claim authoritative fortune-based date selection.
