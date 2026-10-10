---
name: bazi-dayun
description: Compute traditional BaZi decade pillar cycles, direction, adjacent solar-term boundaries and approximate nominal start age without predictive claims.
license: AGPL-3.0
---
# 八字大运排布 Skill

使用本项目 `bazi_dayun` MCP Tool（或 `POST /api/dayun` / `xuanshu dayun`）进行**非预测性**传统干支十年序列计算。

1. 获取明确出生 ISO 日期、IANA 时区、性别（传统排法男/女）及流派时制，经度缺失不能启用太阳时。
2. 性别未指定，必须让用户明确 `direction_override=forward/reverse`，不能猜。
3. 展示年柱阴阳、月柱、实际上一/下一**十二节**、分秒差、三日一岁起运岁数；同时声明公历交运日按365.2425日/年近似投影。
4. 只列出十年干支和对应名义年龄，禁止预测现实事件、发财、婚姻、疾病、灾难及概率。
5. 如出生恰好交节，提示核对实际出生时刻及历史时区信息；任何流派冲突注明口径。

规则：`astro://rules/dayun`。