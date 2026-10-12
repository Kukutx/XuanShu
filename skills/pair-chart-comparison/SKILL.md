---
name: pair-chart-comparison
description: Use this skill for structural comparisons between two traditional Chinese BaZi charts, including pillar matches, six harmony and six clash tags; never output relationship compatibility scores.
license: AGPL-3.0
---
# 双盘结构对照

## Procedure

1. Obtain two distinct birth records with local birth date/time and IANA timezone. Do not retain sensitive birth information beyond the immediate task.
2. Call `pair_comparison` with nested `person_a` and `person_b` BirthInput objects.
3. Describe the day-stem ten god in both directions (`day_stems`), the day-stem five combination, the zodiac labels and `branch_links`: every labelled pair of branches across the four pillars (`同支`, `六合`, `六冲`, `六害`, `相刑`), including pillars in different positions. These are **cultural classifications**, not measurements of relationship stability or worth.
4. If either person does not know the birth hour, pass `person_a_hour_unknown` or `person_b_hour_unknown`. That hour pillar is then `null` and never compared; a pillar that changes during that birth day (a jie or a 23:00 day change) is `null` too. Do not call `ziwei_pair_overlay` in that case: it needs both hours and refuses.
5. Respect the user's selected 23:00 day boundary for each chart separately.
6. For broader symbolism, optionally call `bazi_chart` on each record. Avoid combining unsupported Zi Wei relationship calculations into a definitive compatibility claim.
7. For three to eight people, or two people in one particular year, call `group_relations` with `members` (each with `label`, `birth` and optional `hour_unknown`) and `year`. Put each person's `birth.gender` so the luck pillars can be set. `year_view` lists each member's luck pillar in that year, the year pillar read against each chart and `luck_pairs`, the labels between members' luck pillars. With an unknown hour, `start_years` may hold two years and `status: depends_on_hour` lists both possible luck pillars under `options`; describe both rather than picking one.

## Example arguments

```json
{"person_a":{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai"},"person_b":{"birth_datetime":"2001-01-01T12:00","timezone":"Asia/Shanghai"}}
```

## Boundaries

No compatibility score, deterministic relationship verdict, counselling diagnosis, or advice to end or begin a relationship based on fate patterns. Use ordinary communication and real-world context for decisions.
