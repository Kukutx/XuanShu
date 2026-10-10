---
name: ziwei-professional
description: Compute an optional extended Zi Wei natal and period chart using an independently installed iztro-py provider; disclose unverified provider version, school assumptions and calculation-only scope.
license: AGPL-3.0
---
# 专业紫微本命与流运对照

只有用户明确需要完整星盘或者大限/流年/流月/流日/流时时调用 `ziwei_professional_chart`。需要安装独立的本地 `iztro-py` 提供方，不能默认为已经安装。

1. 核对公历出生日期、出生地本地时间、IANA 时区、性别、子时与闰月习惯。
2. 调用工具传入 `birth`，可选 `target_date`（公历）和 `target_hour`。
3. 显示提供方 `iztro-py`、方法参数及返回的原始盘；若提供方不可用，**停止并明确说明**，不要用玄枢原生局部排盘伪装为完整专业星盘。
4. 以明确的来源对照星曜、四化及运限字段；不同流派相冲突时逐字段列出，不能武断以单一结果为标准。
5. 仅解释传统文化结构，不据此预测真实人生、医疗、财务或重大关系结果。
