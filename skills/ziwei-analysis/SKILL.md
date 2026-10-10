---
name: ziwei-analysis
description: Use this skill to inspect Zi Wei Dou Shu 12 palaces, primary and auxiliary stars, year transformations and palace flying mappings using the independent XuanShu MCP calculator.
license: AGPL-3.0
---
# 紫微斗数十二宫与四化

## Procedure

1. Confirm birth date, local clock time, IANA timezone and gender parameter if decade directions are requested.
2. Call `ziwei_chart` to obtain twelve palaces, primary and selected auxiliary stars, 命宫/身宫 and 生年四化.
3. If a single palace is mentioned, call `palace_detail` with `birth` as the complete input object and `palace` as one of the official palace names (e.g. `命宫`, `财帛宫`).
4. Report `transformation_school` and distinguish `birth_year_transformations` from `palace_flying_transformations`. `self_transform=true` is only a map label, not a prediction.
5. Cite which specific star / palace / stem yielded each label, including any notes about the partial star list.
6. For technical rules, read MCP resource `astro://rules/ziwei`.

## Example arguments

```json
{"birth":{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai","gender":"female"},"palace":"命宫"}
```

## Boundaries

Full auxiliary star coverage, full 小限/流年/流月 and complete genre-specific interpretation are not implemented. Longitude-based solar-time correction is available when explicitly requested. Do not fabricate these. Explain that different schools use different 四化 tables.
