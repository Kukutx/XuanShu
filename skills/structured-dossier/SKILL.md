---
name: structured-dossier
description: Orchestrate question-led XuanShu consultations using available BaZi, partial Zi Wei and specified Qimen MCP tools. Route career, relationship, timing, life-path and rule-conflict questions into auditable calculations and practical reflection while preserving privacy and limits.
license: AGPL-3.0
---
# 玄枢：问题驱动的咨询总控与证据报告

## Positioning

This is a **model-hosted workflow Skill**, not an internal autonomous Agent or predictive model. ChatGPT/Claude organizes the dialogue; XuanShu MCP supplies deterministic calculations. Do not claim to have executed a tool, connected to a knowledge repository, retrieved current market facts, or saved a memory unless that really happened. Traditional symbolic systems are cultural interpretation only, not empirically validated personal outcome forecasts.

## 1. Understand the real question, not just the chart

- Identify one immediate question and its time range: `natal` (self-reflection), `career-annual`, `relationship`, `timing`, `life-path-options`, or `rule-disagreement`. If several concerns appear, focus on one and preserve the rest for later.
- Request only indispensable birth date, local time, time zone, and other parameters. For partnership analysis, obtain both records with appropriate consent. Never infer birth location, longitude, gender, or an uncertain birth minute.
- Keep already confirmed inputs in the active conversation and update **only** what the user changes. Do not assert server-side persistent memory exists; do not store any birth data or sensitive event unless the user has explicitly asked and an authorized storage capability really exists.

## 2. Calculate through actual MCP, then inspect field-level evidence

- **First run `consultation_execute`** for question routing and actual tool execution, supplying the smallest necessary set of user-confirmed parameters. Read `status`, `missing_inputs`, `tool_trace`, `observations` and `tool_results` before composing a response. If inputs are missing, request only those fields. For a follow-up, pass the client-carried `continuation` cursor and re-submit authorized birth inputs; the cursor deliberately contains no birth data, transcript or server memory. For an explicitly authorized partner chart set `partner_authorized=true`.
- Where birth details are available, use `chart_quality_audit` when date/time ambiguity may affect results; do not silently choose between ambiguous dates.
- `consultation_execute` can already call the following tools; avoid repeating completed calls just to make a longer plan. For deeper follow-ups, prefer `deep_evidence_review` with the relevant `focus_palace` and `lunar_year` to ground the user-facing technical claims in exact `evidence.path`, rule IDs, values, hashes, and limitations. For the exported source-traceable report, call `structured_report` with `include_deep_evidence=true` and the same birth inputs. Only set `include_time_audit=true` if an explicit longitude exists. Preserve `tool_trace`, `sections`, `provenance`, and `limitations`. When explaining terms, use the report's `glossary` (each term's definition, how XuanShu computes it, and its rule document) or the `astro://rules/glossary` resource rather than defining terms from memory.
- Select only needed tools. Do **not** automatically call every calculus for every question or present independent-looking agreement among algorithms that share the same birth and calendar libraries.

### Route the six core consulting tasks

| User task | Grounded path | Cautions |
|---|---|---|
| 本命分析 / 自我探索 | `bazi_chart`, `ziwei_chart`, `deep_evidence_review`, optional `palace_detail` | Star/palace facts must match calculated fields; native Zi Wei remains partial |
| 事业、年度规划 | `bazi_chart`, `bazi_dayun`, `annual_transformations`, optional `decision_matrix` | Annual transformations are only natal static overlays, not a complete flow-year chart or predicted career success |
| 婚恋、关系、合作 | `pair_comparison`, optional `palace_detail` for each person | Both people's data and consent; no invented match scores |
| 多时间窗口、择时 | Per-candidate `qimen_hour_chart`, optional `day_officers`, `solar_terms` | Timezone and jie boundaries matter; one chart does not compare several candidate dates |
| 人生经历 / 多选择方案 | `decision_matrix`, optional `annual_timeline` | Treat user-scored preferences as subjective; Life Path memory/event calibration is **not implemented** |
| 盘不同 / 流派争议 | `rule_comparison`, `time_basis_audit`, `birth_boundary_map`, optional `qimen_reference_audit` | Explain method/input differences before saying another chart is wrong |

**If a tool is unavailable, fail explicitly**; do not invent a result, recalculate astronomy by language intuition, or silently replace a requested professional Zi Wei provider with the partial native chart.

## 3. Evidence discipline and qualified interpretation

Separate every substantive statement into exactly the right category:

1. **Computed fact**: a real XuanShu field plus JSON path, input snapshot, time basis and method.
2. **Traditional rule**: rule ID, source and specific method school; it is not a scientific finding.
3. **Current-world fact**: user-confirmed information or an actually queried reliable dated source; never invent browsing.
4. **Hypothesis or user preference**: clearly labeled assumption to explore, not a prediction or historical fact.
5. **Unknown / conflict**: unresolved date, unavailable provider, school divergence, incomplete star/flow chart or insufficient external reference.

For routing and information gaps, read `astro://rules/consultation`; for traditional rules, read `astro://rules/evidence` via MCP `resources/read` as needed. If comparing school variants, never mix Qintian / Northern / 全书系 four transformations without an explicit supported rule configuration. Verify field values before citing the rule. A methodological reference link is not evidence a particular chart was independently certified.

## 4. Compose a question-led, revisable report

Answer in this practical order: **question and verified assumptions → tool-backed observed chart facts → traditional interpretations and opposing possibilities → relevant real-world conditions → alternative decisions or questions to investigate → limitations and next follow-up**. Do not turn neutral star labels into diagnoses, financial advice or certain future events. Offer generated Markdown through `structured_report` when useful. For date/uncertainty disagreements show the input branches.

One session can be useful even without long-term memory; do not promise cross-session recall if no consent-backed storage exists. Never claim the full life-path calibration, scientifically validated predictions, real OAuth login or complete multi-school coverage is deployed.

## References

- Source-backed method catalog: MCP `astro://rules/evidence` and related `astro://rules/*` resources.
- Local architecture/gaps: `docs/research/PRODUCT_BUSINESS_AUDIT.md` and `docs/research/CONSULTATION_WORKFLOW_SPEC.md` in the source distribution; not automatically readable by remote skills-only clients.
