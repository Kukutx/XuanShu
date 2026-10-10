# XuanShu 咨询 Agent：六类业务工作流与可操作验收

**设计约束：`v.0.1.0`，模型无关，独立实现。** 这是 ChatGPT/Claude 通过现有 MCP 与 Skills 进行咨询的执行契约；非已上线的专用 LLM Runtime。所有传统术数输出仅是文化象征，不是现实成功概率。

## 1. 统一数据契约（目标架构；不可误报为当前已实现）

```text
ConsultationRequest:
  question, focus, confirmed_birth_profile?, target_window?,
  second_birth_profile?, options?, factual_context?, school_settings?
  consent: {temporary_use, save_profile, save_events, share_second_profile}

ConsultationRun:
  run_id, workflow_type, input_snapshot, plan, tool_calls, evidence,
  unresolved_assumptions, school_differences, report, follow_up_questions,
  storage_state, created_at

EvidenceItem:
  id, kind(computed|traditional|factual|user_provided|hypothesis),
  source_uri_or_rule_id, calculation_path?, method_version?,
  input_fingerprint?, statement, limitations, checked_at?

LifeEvent (未来特性):
  event_id, owner_id, date_or_interval, event_type, user_text,
  consent_scope, correction_history, deleted_at?
```

`owner_id` 必须由鉴权令牌服务端确认，不能从客户端自报信任。当前无真正服务器账户数据库，因此 `LifeEvent` 只是需求契约。

## 2. 通用五阶段

1. **Clarify**：识别一个聚焦问题及所需时窗。按需询问出生信息（包括时区/时制/不确定性），不要为了每次对话让用户重填已经确认的参数。个人资料的保存要明确授权。
2. **Compute**：先检查必要的生日和交节准确性，再用合适的 MCP Tool 取得结构盘数据。拒绝凭语言模型推测干支或星曜；调用失败不能悄悄替换为幻觉文本。
3. **Verify**：按流派与规则 ID 对照；将“同源算法结构一致性”与“异源验证”分离；冲突应展示流派口径、不同输入与未覆盖字段。
4. **Interpret**：输出传统象征+现实信息（明确来源）+替代方案，绝不把传统标签或用户主观评分换算为必然事件或真实统计概率。
5. **Follow-up**：给出用户可核验或改变的前提，不保留隐私资料，除非在允许的环境获得了明确存储同意与真正可撤销的存储能力。

## 3. 六个可复现业务场景

### S1 本命自我探索：如何理解我的职业相关宫位？

- 输入：已确认出生时间/时区；焦点 `官禄宫`。
- 工具：`chart_quality_audit → deep_evidence_review(focus_palace='官禄宫') → palace_detail('官禄宫')`；如明确需要，可用 `structured_report`。
- 输出：四柱与宫位计算事实、三方四正及四化传统含义、当前实现流派与缺失项。禁止根据宫位推断具体职业收入。
- 验收：每个星曜、四化和宫位都有来自工具的原字段；出生时间不确定时给出质量提示。

### S2 某一年职业选择：明年转职还是留下？

- 输入：出生资料、目标**公历或农历年界**、两种真实工作方案与偏好。
- 工具：`chart_quality_audit → bazi_chart → ziwei_chart → annual_transformations`（明确仅静态年干映射）；如需大运调用 `bazi_dayun`；现实方案调用 `decision_matrix`（用户自设指标）。
- 输出：传统年度标签及限度、现实条件对照、无法据盘推断的收入/录用/行业数据、应核实的事实。
- 验收：不得把静态四化叫“完整流年”；不得从星盘自动产生财务成功率。

### S3 关系与合作：两个人如何更好沟通？

- 输入：双方明确同意用于本次计算的出生信息以及需要讨论的关系情境。
- 工具：`pair_comparison`；必要时分别 `palace_detail(夫妻宫/仆役宫)`。
- 输出：传统合冲与宫位对照、现实沟通的开放性问题；不形成所谓 88% 匹配分或命定关系。
- 验收：双方时区不混淆；不得以关系结构否定用户现实经历。

### S4 多候选择时：哪些时段可供优先考虑？

- 输入：可行日期/地点/时区、事件目的、无法调整的现实约束。
- 工具：按候选时刻分别 `qimen_hour_chart`，如需日常建除标签调用 `day_officers`；对边界情况调用 `solar_terms` / `chart_quality_audit`。
- 输出：方法限定的多候选结构表，附现实可行性和时区/节令提醒；不得断言某时刻保证成功。
- 验收：精确到每个候选**当地时区**；没有完整其他流派时明确拒绝相应结果；不是单盘冒充择时。

### S5 Life Path：如果继续留职与转行，我该如何比较？

- 输入：用户确认的经历/工作条件、方案和优先级；如用户允许，参考此前确认事件。
- 工具：`decision_matrix`，必要时独立查询传统结构或年度标签。
- 输出：可编辑的每个方案、现实前提、传统象征性解读、条件触发与复盘计划。
- 验收：事件不得凭模型补齐；未获得存储授权不得声称未来记得该事件；不得用星盘推算真实概率。

### S6 连续追问与流派冲突：那下一年呢？为什么另一软件不一样？

- 输入：先前已确认的资料、仅更新年份，或新流派口径的公开参考盘。
- 工具：`rule_comparison`、`time_basis_audit`、`birth_boundary_map`、`qimen_reference_audit` 按差异类型选择。
- 输出：保留原输入快照，显示仅更新的字段及可能导致差异的时区、子初换日、农历闰月、四化表、中宫寄法等。
- 验收：能重放计算输入；“口径不同”不误判为“另一方错误”；没有明确外部数据则不得宣称第三方逐盘认证。

## 4. 失败时必须清楚呈现

| 失败 | 正确响应 |
|---|---|
| 出生小时不确定、临交节 | 请求范围或做 `birth_boundary_map`，展示多种可能结构，不给单一确定答复 |
| 专业紫微提供方未安装 | 明确提示该后端不可用；不得将原生部分盘冒充专业全盘 |
| Agent 无 Web 实况信息来源 | 标明“未核实的现实数据”，不能声称已联网查到 |
| 存在流派分歧 | 显示学校、规则版本及差异字段，不盲目投票得出统一结论 |
| 只有方法链接，无黄金盘 | 引用方法但标记“没有独立实例验证” |
| 没有记忆/账户授权 | 仅在当前会话内讨论，不能声称以后会记得或已持久保存 |
| OAuth 令牌失效 | 提示重新授权，不能静默用旧静态 Token 绕过认证 |

## 5. 回归验收目录

- 6/6 场景都有完整工具规划，所有计划引用**现有** MCP 工具，不编造工具或参数。
- 每条计算事实都对应实际 `structuredContent` 字段；无“看似专业”的虚构星曜。
- 对立春前后、农历元旦、23:00、DST 交叠和闰月等边界做不可省略的反例测试。
- 多轮改动只变更用户明示的维度；在未支持的存储方式下不得保存资料。
- 输出分层：计算结果、传统解释、现实事实、用户信息、假设及限制；追问方向与原问题直接相关。
- 生产部署只能以 ChatGPT/Claude 真实 HTTPS OAuth MCP 回路通过为完成，不能以本地单元测试或私有 Skills 插件代替。

## 6. 产品衡量方法

**正确指标**：完成一个真实问题所需往返轮次、工具调用成功率、字段引用准确率、跨流派差异可解释率、用户能否修正输入/删除记录、真实客户端 E2E 成功率、不同年龄/时区的计算边界覆盖。**错误指标**：Tools 数量、页面标签数、报告字数、没有样本定义的“命中率”或虚构的命运预测概率。

相关审计：[`PRODUCT_BUSINESS_AUDIT.md`](PRODUCT_BUSINESS_AUDIT.md)。
