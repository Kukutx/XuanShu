# 问题驱动咨询执行器 · XuanShu v.0.1.0

- `consultation_execute` 运行的是**确定性的本地工具编排**，不是自主 LLM Agent。ChatGPT / Claude 可以在返回的结构化证据上生成交流文字，但不能虚构命理结果或现实事实。
- 六类场景：`natal`（本命）、`career`（年度/职业）、`relationship`（双人关系）、`timing`（候选时间）、`decision`（现实方案）、`rules`（规则差异）。`auto` 采用透明关键词规则；歧义场景可以强制指定 intent。
- 执行顺序：问题路由 → 必需字段检查 → 质量审计 → **按需**计算 → 规则证据展示 → 待补输入与续问游标。每一步在 `tool_trace` 中有实际执行的工具名。
- `status=needs_input` 表示没有可进行的计算；`partial` 表示部分计算已完成但问题还缺输入；`completed` 表示选定计算路径已运行，**不代表预测、专业验证或现实咨询已经完成**。
- `continuation` 仅携带意图/关注宫/年度/回合数，不含出生日期、姓名、历史问句或完整命盘；不会在服务器保存。继续调用时重新提交 `birth`、`partner`、`candidate_times` 等必要参数。续问游标**不具有身份鉴权作用**。
- `observations` 按 `calculated`、`traditional-rule`、`user-assumption` 分类，`tool_results` 留存当前请求中的完整原始字段以供核对；基于传统术数的标签不应当推断财务、疾病、感情成败或现实吉凶概率。
- 每条调用仍受原 MCP/REST 的鉴权、Origin、Host、请求体大小以及输入验证约束。模型和 Agent 不得擅自存储/共享他人的出生信息。
- 包括双盘、择时、多个未来选择在内，系统不会凭出生盘自动生成恋爱匹配分或吉日成功率；判断现实选择需要用户认可的事实、方案与评价标准。
