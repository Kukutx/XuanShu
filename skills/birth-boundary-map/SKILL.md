---
name: birth-boundary-map
description: Audit modeled BaZi and partial Zi Wei birth-time discontinuities across uncertain times, including solar terms, local day/hour and timezone changes.
license: AGPL-3.0
---
# 出生时刻临界对照 Skill

使用 `birth_boundary_map` MCP Tool（`POST /api/birth-boundaries`、`xuanshu birth-boundaries`）。

1. 先确认出生日期、时区、时基和经度；对夏令时重叠时段要求 ISO UTC offset。
2. 在前后 1–120 分钟真实 UTC 区间定位传统时辰、日期、节令和时区边界，按模型分段展示代表八字及部分紫微。
3. 明确 `boundary_resolution_seconds=1` 是数值定位，不是出生资料精度，也不是对未实现的流派规则完备性证明。
4. 无切换点时只能表述「当前模型在检查区间内未发现」，不得称出生盘已认证。
5. 出生时刻离 1901 年初或 2099 年末不到误差范围时，区间截到支持范围的边缘，`clipped_to_supported_range` 写明截掉的一侧（`start` 或 `end`），`birth_utc` 给出出生瞬间；截掉的部分没有检查，要照实说明。

规则：`astro://rules/boundary-map`。