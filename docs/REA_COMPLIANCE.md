# REA / DevMate：合法取证与独立实现说明

本文件记录本项目的研究边界，不是从他人代码中提取的设计或源代码。

## 工具状态

用户电脑经 DevMate `gateway_status`、`run_command` 检查：Node.js v24.21.0；`rea` CLI 已在系统 PATH；REA 的 Claude Code/Codex 配置显示 aligned。DevMate 当前活动 `refract-mirror-study` 路径失效，故未修改任何旧项目。用户的本地文件未被复制到云端。

## 访问边界

- 目标网站：https://tianfu-ai.com/chat
- 其公开服务条款（https://tianfu-ai.com/terms）明确禁止逆向工程、提取源码、绕过限制和未经许可自动化访问。
- 因此**没有对目标网站实施 REA CDP 抓取、脚本恢复、接口枚举、登录绕过、模拟付费访问**。
- 功能取材于合法可访问的公开 `features` 页面（https://tianfu-ai.com/features）、传统建除公开规则（https://zh.wikipedia.org/wiki/建除十二神）以及用户对独立 Agent 能力的要求。
- 设计、源码与测试全部独立实现；不得暗示用户取得目标网站私有算法、提示词、API 或账户数据。

## 如需对自主拥有的软件使用 REA

`rea capabilities`、`rea doctor --client codex --json` 可查询配置。对用户**有权分析**的 JS/Electron 应用可执行 `rea analyze-javascript-application /path/to/own-app --json`；若需要远端网站 CDP 观测，必须先得到目标站授权并配置获批准的 Origin。REA 自身文档： https://rea.tools/get-started/ 。

## 已在本项目实现的相似通用能力

1. 程序化结构对照：`annual_timeline`。
2. 节令与日期规则：`day_officers`。
3. 使用者主导的可解释方案比较：`decision_matrix`。

**证据级别：** 功能的独立规则、源码和自动测试是可复现事实；未声称对应天府 AI 的内部工作方式或算法。
