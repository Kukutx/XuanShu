---
name: transparent-decision-planning
description: Build an auditable multicriteria decision matrix using user-provided options, criterion weights and zero-to-five ratings, with normalization and sensitivity analysis that are independent of astrology and predictive fortune claims.
license: AGPL-3.0
---
# 现实方案透明比较

## 适用时机
用户比较两个以上的工作方式、开发路线、学习计划或其他可用事实量化的现实方案，希望看清权重与敏感性，而不是要求预言。

## 执行步骤

1. 先得到用户实际目标、2–8 个方案、1–8 个可解释的评价标准及其正权重。不得编造用户未给出的实际事实。
2. 各方案在每个标准上必须提供 0–5 分用户评分。资料不足时可说明需要补齐，不能无声推测。
3. 调用 `decision_matrix`，展示归一化权重、方案贡献、同分并列和逐项排除指标后的敏感性。
4. 提醒评分是主观输入，排名不是概率，也不能替代外部证据；如果某指标变化导致首位变化，应标记该结论不稳健。
5. 当用户同时询问命理时，将命盘结果放在独立文化参考章节，绝不可把命理标签混进客观决策评分。

## 数据与隐私
仅一次请求的输入即时处理；默认不建立服务器档案。禁止把出生信息、身份资料写进评分字段或报告日志；不声称可以预测个人未来。
