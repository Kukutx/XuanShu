---
name: pair-chart-comparison
description: Use this skill for structural comparisons between two traditional Chinese BaZi charts, including pillar matches, six harmony and six clash tags; never output relationship compatibility scores.
license: AGPL-3.0
---
# 双盘结构对照

## Procedure

1. Obtain two distinct birth records with local birth date/time and IANA timezone. Do not retain sensitive birth information beyond the immediate task.
2. Call `pair_comparison` with nested `person_a` and `person_b` BirthInput objects.
3. Describe shared stems and four pillar branch relations. `六合`, `六冲`, `同支` are **cultural classifications**, not measurements of relationship stability or worth.
4. Respect the user's selected 23:00 day boundary for each chart separately.
5. For broader symbolism, optionally call `bazi_chart` on each record. Avoid combining unsupported Zi Wei relationship calculations into a definitive compatibility claim.

## Example arguments

```json
{"person_a":{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai"},"person_b":{"birth_datetime":"2001-01-01T12:00","timezone":"Asia/Shanghai"}}
```

## Boundaries

No compatibility score, deterministic relationship verdict, counselling diagnosis, or advice to end or begin a relationship based on fate patterns. Use ordinary communication and real-world context for decisions.
