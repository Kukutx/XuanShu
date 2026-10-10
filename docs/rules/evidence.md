# 深度证据分析：规则、字段、外部参考与反证

**版本始终固定 `v.0.1.0`，持续开发未发布。** `POST /api/deep-review`、MCP `deep_evidence_review`、CLI `xuanshu deep-review` 和 Web「深度证据」共用 `app.evidence.deep_evidence_review`。

## 分析不是预测

- 每个 `finding` 同时返回 `observation`（计算事实）、`evidence`（确切 JSON 字段路径与计算值）、`rule_ids`（明确规则）、`limit`（该事实不能支持的推断）。
- `references` 中 `implementation` 是**本项目实现位置**；外部 `reference` 只是**文档中的约定、API 或历法概念**，不表示该命盘已被第三方独立验证。
- `input_parameters` 明确保留完整出生参数（包括性别选项、时区、时间模式）、关注宫位与年度请求，便于和 `calculation_hashes` 一同复算；**不能只按出生日期比较完整命盘摘要**。SHA-256 仅是内容校验值，不是可信第三方签名。
- `checks` 只检测十二宫唯一性、四化安星内部一致性、三方四正分宫唯一性和共同时制等**内部不变量**。这些 checks 通过也不能证明星曜落宫正确。
- 八字年柱按立春年界，紫微原生出生年柱按农历年界；在春节附近出现不同值时应披露口径，不可擅自统一或称其中一方出错。
- 四柱藏干/十神、合冲刑害、三方四正、宫干飞化与年度四化只输出传统符号结构。**禁止**把两个体系符号“互相印证”推断为个人命运、疾病、婚姻、财富或概率。

## 使用方法

```bash
xuanshu deep-review --date 2024-02-07T12:00 --palace 官禄宫 --year 2026
```

REST JSON：

```json
{
  "birth": {"birth_datetime":"2024-02-07T12:00","timezone":"Asia/Shanghai"},
  "focus_palace": "官禄宫",
  "lunar_year": 2026,
  "include_quality": true
}
```

`focus_palace` 只能是现有十二宫之一；可省略，默认命宫。年度投影可省略；问题文本只会回显为研究主题，不交给生成式模型，不会被执行。

## 外部参考及证据等级

| 来源 | 用于什么 | 不能证明什么 |
|---|---|---|
| [香港天文台公农历换算表](https://www.weather.gov.hk/en/gts/time/conversion.htm) | 公历与农历年界、远期新月不确定性说明 | 不能证明本引擎对 1901–2099 年所有日期均正确 |
| [香港天文台二十四节气时刻](https://www.weather.gov.hk/en/gts/astronomy/Solar_Term.htm) | 交节需要精确时刻而不只是日期 | 不能证明传统八字流派的各种日界设置 |
| [iztro 星盘说明](https://docs.iztro.com/en_US/posts/astrolabe) | 命宫、星曜及十二宫等 API 概念 | 不能证明 XuanShu 的 58 颗星落宫已逐一认证 |
| [iztro 宫位 / 三方四正](https://docs.iztro.com/en_US/posts/palace) | 三合宫、对宫、宫位操作 | 不能证明星曜主题对现实事件有因果影响 |
| [iztro 配置与四化](https://docs.iztro.com/en_US/posts/config-n-plugin) | 四化流派可配置的事实 | 不能把当前全书系四化宣称为唯一规则 |
| [iztro 运限说明](https://docs.iztro.com/en_US/posts/horoscope) | 大限/小限/流年/流月/流日/流时是不同层级 | 当前只提供年干静态叠加，不等于全运限 |

更多面向功能复刻和现有缺口的分析见 `docs/research/FEATURES_AND_REFERENCES.md`。
