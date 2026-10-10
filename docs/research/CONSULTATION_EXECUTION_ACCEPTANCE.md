# 玄枢咨询执行层：实际实现与验收（v.0.1.0）

## 已实现与未实现的明确边界

`app/consultation.py` 不是编写好的一段 Agent 提示词，而是实际运行的 Python 编排器。所有报告由已有确定性函数生成；ChatGPT 或 Claude 可通过 MCP 再用宿主模型讨论报告。不含自主多 Agent 内循环、外部现实事件查询、神奇预测或服务器的跨会话记忆。

| 任务 | 至少一个实际计算或缺输入行为 | 核验方式 |
|---|---|---|
| 本命结构 | `chart_quality_audit` → `deep_evidence_review` | `test_natal_selective_tool_calls_and_explicit_focus` |
| 年度事业 | 质量 → 证据 → `annual_transformations`，选项允许时运行 `bazi_dayun` | `test_career_executes_actual_trace_and_year_overlay` |
| 双人关系 | 未提供对方则 `partial`；确认允许后才运行 `pair_comparison` | `test_relationship_does_not_fake_partner_or_success_probability` |
| 候选时刻 | 各候选时刻独立运行 `qimen_hour_chart`，不排名“吉凶” | `test_timing_candidates_not_ranked_as_lucky` |
| 现实方案 | 缺权重评分则 `needs_input`；完整输入调用 `decision_matrix` | `test_decision_requires_user_scoring_and_does_not_require_birth` |
| 流派/规则争议 | 指定两套出生/时制参数后运行 `rule_comparison`，保留差异字段 | `test_rules_compares_submitted_variants_and_keeps_actual_differences` |

## 多轮与隐私

先输入 `2027年事业` 并给出本人出生资料，响应返回 `continuation`：

```json
{"intent":"career","focus_palace":"命宫","turns":1,"lunar_year":2027}
```

下一次输入 `那2028年呢？` 并将上述游标、出生资料再次传入，会按 2028 农历年重新计算。**单独提交这个游标绝不能重新生成任何出生盘。** 服务端不保存游标、出生资料或历史消息。合盘需要用户明确确认拥有第二人的数据使用权限；用户提供的现实经历属于**未经核实自述**。

## 开发验收命令

```bash
python -m pytest -q tests/test_consultation_runtime.py
python scripts/http_smoke.py
python scripts/browser_smoke.py
python scripts/wheel_smoke.py
xuanshu consult --input examples/consultation-demo.json
```

`browser_smoke.py` 是 Chromium 真实 DOM + FastAPI in-process 桥接，不是公网 HTTPS 网络 E2E。其余 Docker、真实 OAuth、Claude / ChatGPT 在线 MCP 插件授权、完整术数流派认证依然是未验收项。
