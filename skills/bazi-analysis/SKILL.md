---
name: bazi-analysis
description: Use this skill when a user asks to calculate or explain BaZi four pillars, hidden stems, ten gods, Na Yin, Chinese calendar year boundaries, or precise jie solar-term transitions using XuanShu MCP.
license: AGPL-3.0
---
# 八字计算与解释

## When to use

Use for questions about 四柱八字、日主、地支藏干、十神、纳音 and 节令/月柱切换. Do not use the model's internal memory to invent exact calendrical values.

## Procedure

1. Ask only for required birth date, local time, and timezone if not provided. If user is unsure about time, state which outputs cannot be determined reliably.
2. Call MCP `bazi_chart` with `birth_datetime` and `timezone`. Optional rule: `late_zi_day_rollover` controls the 23:00 day boundary.
3. Present year, month, day, hour pillars first; then day master, hidden stems, and the nearest jie from `jie_boundaries`.
4. Explain each ten-god label as a relationship between **stems**, not as a personality fact. Note that apparent element counts use visible stems and branch primary elements only.
5. When the user asks why one app gives a different chart, compare timezone, local/true solar time, 23:00 day change, leap month handling and exact solar-term instant. Request a reference output instead of assuming the other app is wrong.
6. For the source calculation rules, request MCP `resources/read` with URI `astro://rules/bazi`.

## Example arguments

```json
{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai","late_zi_day_rollover":false}
```

## Boundaries

Never claim an empirically validated personal fate, health, financial result, guaranteed future event, 'missing element' diagnosis, or exact 起运岁数 (not implemented). Use `time_mode` with explicit `longitude` for solar time; do not assume birth location.
