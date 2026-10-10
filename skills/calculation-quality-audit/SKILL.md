---
name: calculation-quality-audit
description: Independently flag input-quality risks in calendar, BaZi and partial Zi Wei calculations, especially Jie, civil/solar-time day rollover, time-zone differences, lunar boundaries and Hong Kong Observatory published far-future new-moon uncertainty.
---

# Chart calculation boundary audit

Use the deterministic `chart_quality_audit` MCP tool with `birth` and optionally `boundary_window_minutes` (1–1440; default 15), or the equivalent `/api/quality-audit` REST endpoint. It computes an input/boundary audit and supplies the exact time and selected chart markers used for traceability.

## Workflow

1. Collect the Gregorian birth time, its IANA birthplace time zone, and the exact local offset if daylight-saving folds make the time ambiguous. Request longitude only if a solar-time mode is selected.
2. Call `chart_quality_audit` before drawing interpretive conclusions from a chart. Do **not** mentally estimate Jie, moon, new-moon dates or time correction values.
3. Present each flagged assumption as a check, using the original source and timestamp where possible. Never claim that a `review_needed: false` result certifies a school-specific professional chart.
4. When `published_new_moon_uncertainty` appears, state that Hong Kong Observatory itself notes uncertainty for 2057/2089/2097 dates, and that this project's astronomical model may differ by one day. Do not silently overwrite the output.
5. If hours or local-day boundaries are close, compare different user-authorized rule choices using `rule_comparison` and `time_basis_audit`, rather than picking a supposedly lucky or correct variant.
6. Traditional astrology is cultural symbolism, not scientifically validated prediction; do not give important medical, legal, financial or relationship decisions from its outputs.

## Limits

This Skill does not implement new Zi Wei star schools, add Qi Men Dun Jia, validate historical almanacs, or replace external qualified astronomical references. It does not authorize data retention. Birth records remain unpersisted on the server.
