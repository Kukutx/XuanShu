---
name: lunar-date-inversion
description: Use this skill to convert a specified Chinese lunar year month and day (including an explicit leap-month flag) back to Gregorian date using the local deterministic astronomical lunar calendar tool, with boundary checks and rule disclosure.
license: AGPL-3.0
---
# 农历转公历 / 反查历法核验

## 工作流程

1. 从用户文字明确提取农历年、月、日与是否「闰」。不能把「闰四月」偷换成普通四月，也不能没有来源猜测出生年份或地域规则。
2. 使用 `lunar_to_gregorian` 工具，参数为 `lunar_year`, `lunar_month`, `lunar_day`, `is_leap_month`。输入年限 1901–2099，输出公历也要落在这一范围。
3. 工具会按新月月首定位、检查当月天数并用公历→农历再次核验结果。碰到不存在的闰月、日期超出月长或超出范围时，转述清晰错误，不进行自动补正。
4. 必要时用 `calendar_days` 查询相邻几日，指出公历日期和农历月份的对应关系。
5. 说明使用现代中国标准时区 `Asia/Shanghai` 规则，不声称覆盖全部历史地方历法。该计算属于日期转换，不得擅自附加吉凶、人生预测等结论。

参考资源：`astro://rules/lunar-inverse`。
