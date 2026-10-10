# XuanShu 深度参考调研与差距分析

**研究日期：2026-10-10 · 项目固定版本：`v.0.1.0` · 开发阶段。**

## 研究边界

本文件研究天府 Agent 的**公开自述功能**、iztro 的开源开发接口以及香港天文台的公开历法资料，目标是为 XuanShu 独立设计可审计功能。没有抓取受限页面、私有接口、用户数据、付费模型权重或对他人系统运行 REA。外部页面中的产品描述是**产品自述**，不是精度测试或效果认证。

## 功能差距（不把“计划”写成“完成”）

| 公开产品方向 | XuanShu 当前状态 | 缺口及验收证据 |
|---|---|---|
| 八字与紫微双核心结构解释 | 四柱、有限紫微本命盘；新增 `deep_evidence_review`，可追溯到具体字段与规则 | **仅共用历法和输入的结构对照**，不能宣称两个系统是独立预测验证；完整星曜须跨库逐宫复核 |
| 长期生命轨迹 / 历史经历校准 | 静态农历年度四化序列、透明方案矩阵、可本地保存出生档案 | 尚无经过用户授权、可追溯的事件日记和显式撤销/存储政策；不能捏造因果“校准” |
| 择时、时家奇门 | 时家拆补转盘限定实现、建除值日标签；支持用户提供独立黄金盘字段校验 | 置闰与其他流派未实现；应按节气交接前后、阴阳遁、暗干及各宫星门神逐项外部验盘 |
| 多流派紫微 | 14 主星 + 44 选定辅/杂曜；可选 iztro-py 适配器 | 可选依赖尚未在当前隔离环境完成真实运行；非完整流曜/流限，不应标为全流派兼容 |
| 结构化可视化工具链 | 本机 Web + REST + MCP stdio/HTTP + CLI；报告可导出 Markdown | 没有公网 HTTPS OAuth 登录、正式跨 ChatGPT/Claude 的远程调用验收 |
| Agent 深层解释 | 本轮新增证据工作流：规则 ID、来源、字段、限制、内部一致性检查 | 目前是**确定性结构解释**；不能假装已经运行可验证的 LLM 推理或科学预测 |

## 证据要求

1. **外部独立参考**：输入规则、时间基准、流派、字段完整性都公开且可重复获得。只验证共有字段；缺失字段一律为**未验证**。
2. **计算追溯**：结论必须给出 API/JSON 精确字段路径和使用的规则 ID，不能仅写“依据大数据”或“根据模型”。
3. **冲突分类**：立春/农历年首、北京时间/出生地、时制、闰月、四化流派都可能产生合法差异；先检查口径，再判断算法错误。
4. **测试等级**：内部逻辑单元测试 ≠ 单个外部黄金盘 ≠ 大样本异源权威比对 ≠ 正式云端安全验收。报告分别记录。
5. **隐私**：只有用户明确同意才可存储出生资料/经历记录；当前服务器默认不保存，浏览器档案明文而备份可加密。

## 一手 / 开源资料

- 天府 Agent 官方公开功能说明：[Tianfu Agent About](https://tianfuagent.com/about)（双核、长记忆、Life Path、择时、奇门等为其对外宣传；本项目不复用私有实现）。
- iztro 开发文档：[Astrolabes](https://docs.iztro.com/en_US/posts/astrolabe)、[Palaces](https://docs.iztro.com/en_US/posts/palace)、[Configuration](https://docs.iztro.com/en_US/posts/config-n-plugin)、[Horoscopes](https://docs.iztro.com/en_US/posts/horoscope)。
- 香港天文台：[农历转换表](https://www.weather.gov.hk/en/gts/time/conversion.htm)、[二十四节气时刻](https://www.weather.gov.hk/en/gts/astronomy/Solar_Term.htm)。
- MCP 官方：[2026-07-28 Tool specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx)。
- 独立奇门参考：[qfdk/qimen 公开测试](https://github.com/qfdk/qimen/blob/main/test/paipan.test.js)，仅用于其确实给出的字段，不视作所有流派的权威认证。

**结论：** 目前最需要提升的不是再增加几百条命理断言，而是跨流派黄金盘样本、时制模型差异可视化、明确的规则与证据链、以及真实远程 MCP/OAuth 互通。新增的深度证据工作流解决了可解释性与内部矛盾识别的一部分，但不填补专业验盘或正式部署缺口。
