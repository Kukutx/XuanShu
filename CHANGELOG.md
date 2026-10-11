# 更新记录 · v.0.1.0（未发布）

- 2026-10-11 超越天府第二批（仍为 v.0.1.0）：新增四柱反查（`app/pillar_search.py`、`POST /api/pillars-to-dates`、MCP `pillars_to_dates`）与外部命盘导入核对（`app/chart_import.py`、`POST /api/chart-import-check`、MCP `chart_import_check`），MCP 工具增至 30 个，工作台新增两个页面；八字页新增大运流年时间条，点流年打开紫微同年流年层；`engines.pillar_indices` 从 `calculate_bazi` 中抽出供反查复用；页面与静态资源 gzip 并以 `Cache-Control: no-cache` 加 ETag 校验缓存。
- 2026-10-11 超越天府的一轮体验改进（仍为 v.0.1.0），分析见 `docs/research/SURPASS_TIANFU.md`：界面视觉重做，新增浅色、深色、跟随系统配色（`static/theme.js`），五行与四化配色在两种主题下达到 WCAG AA；AI 对话改为流式（`POST /api/chat/stream`，逐行 JSON），支持停止、超时、重新回答、编辑问题、Markdown 渲染（`static/markdown.js`，只建 DOM 不用 innerHTML）、对话内命盘卡片与追问建议，响应新增 `charts`；紫微盘新增大限、流年层；时辰不详的十二时辰对照；农历生日输入；奇门起局时刻；本机生成的分享卡片；重绘保留焦点与展开状态、标签页 tabpanel 关联、移动端折叠表单与横向滑动的紫微盘。新增流式接口与浏览器冒烟测试覆盖。审查后补充：OpenAI 兼容接口也流式输出并可中途停止；时辰不详标记随档案保存，并传给 AI 对话（系统提示与置信度按全天误差）、分享卡片和 JSON 导出；十二时辰对照按真太阳时取样，行名取自实际排出的时辰；默认流年按历法引擎的农历年；奇门换起局时刻即清除旧盘；对话保存时连同失败回答的提问一起略去；首页隐私说明改为“服务器不保存”。
- 2026-10-11 天府功能对齐第五批（仍为 v.0.1.0）：English / 日本語界面覆盖计算结果。新增 `static/i18n-extra.js`（约 1400 条，由 `scripts/build_i18n_extra.py` 从 `scripts/i18n_extra.json` 生成），包含界面标签、宫位星曜等术语、引擎返回的说明与限制文字，以及模板拼接片段；整段没有对应条目时按已知词组就地替换。测试要求 static/ 与 app/ 中每条中文字符串都有英日对照。
- 2026-10-11 天府功能对齐第四批（仍为 v.0.1.0）：AI 对话新增「多流派会诊」模式。请求 `mode: "panel"` 时，八字、紫微、奇门择时三位专家并行作答，每位只能调用本流派工具和共用的边界、历法工具（越界调用会被拒绝并记入 trace）；综合者不调用工具，只依据专家报告作答。`panel_agents` 可缩小专家范围。响应新增 `mode`、`panel`，trace 每步标注 `agent`。
- 2026-10-11 天府功能对齐第三批（仍为 v.0.1.0）：AI 对话回答附带置信度（`app/chat_verify.py`）。排盘置信度按出生时间误差重算四柱与命身宫；独立核验 Agent 另行调用模型，逐条标注回答中的计算陈述是否有工具依据。请求新增 `verify` 与 `profile.birth_time_uncertainty_minutes`，响应新增 `verification`、`chart_confidence`。
- 2026-10-11 天府功能对齐第二批（仍为 v.0.1.0）：新增双人紫微宫位叠盘（`app/ziwei_pair.py`、`POST /api/ziwei-pair`、MCP `ziwei_pair_overlay`，工具增至 28 个），「双人对照」页同时显示八字与紫微对照；新增界面语言切换（简体、繁體、English、日本語），繁體由 OpenCC 数据生成的字词表转换并保留术数术语。
- 2026-10-10 天府功能对齐（仍为 v.0.1.0）：新增 `docs/research/TIANFU_PARITY.md` 逐项对照天府 Agent 公开功能。新增可选 AI 对话（`app/chat.py`、`POST /api/chat`、工作台「AI 对话」）：Claude 官方 SDK 或 OpenAI 兼容接口驱动现有确定性工具，展示每步工具调用；浏览器端档案记忆、人生事件、可选对话保存与 Markdown 导出；四种回答语言。服务器不保存对话。新增择日择时区间扫描（`date_candidate_scan`）与人生事件回溯（`life_path_review`），MCP 工具增至 27 个；内置 65 个城市的时区与经纬度；新增 Web App Manifest 支持添加到主屏幕。

- 2026-10-10（仍为 v.0.1.0）：修复 Linux Python 3.15 虚拟环境符号链接触发发行脚本误报；新增跨环境回归。优化工作台全局搜索、键盘导航、工具直达、过期命盘提示及 Markdown 复制。保留旧 Python 版本以兼容其他项目。

- 2026-10-10 Python/UX：Windows Python 3.15.0 侧装、验证并切换默认解释器和项目 .venv，保留 3.13 回退；uv 更新到 0.13.0；工作台优先显示常用功能、支持全部工具搜索、五种咨询快捷模板、高级参数折叠、草稿内存保留、日期默认更新、演示资料提示与清晰 HTTP 错误。新增 Python 3.15 CI 任务及回归测试，版本不变。

- 2026-10-10 Packaging: 浏览器回归默认生成 Git 忽略的 .artifacts；ZIP 排除 QA 图片、私有 .env.* 与密钥文件，并在包校验时拒绝这些路径；新增两个安全回归测试。版本仍固定 v.0.1.0。

- 2026-10-10 Windows/GitHub: 修复 Docker Slim 缺编译器，改为多阶段 wheel 构建；补充 Chrome 真实 HTTP 测试；公开仓库上传成功；修复 CI wheel 构建依赖，通过 Python 3.11/3.12/3.13 与 Docker 四组任务。项目版本仍固定 v.0.1.0。

## 2026-10-10 · 全工具接口验收与 Windows 安装脚本（仍为 v.0.1.0）

- 新增 `scripts/full_functional_audit.py`，对照全部 25 个 MCP 工具与 REST 端点，强制清单一致，失败不可用错误分开报告；新增测试固定工具清单，防止新增 API 时漏测。
- Windows 侧实测 Python 3.13、uv、Node、Docker CLI 与 `iztro-py 0.5.0` 的独立真实 API 可调用性；Docker Engine 当时未运行，不能据此写成通过容器测试。
- 新增 `scripts/windows_acceptance.ps1`，使用项目 `.venv` 进行隔离安装、全接口/CLI/HTTP/Chrome/Node 验收；不自动对外部署或保存出生档案。
- 未修改版本号、已审核术数算法或第三方私有接口。

## 2026-10-10 · 咨询执行器（固定 v.0.1.0，未正式发布）

- 新增实际可执行的 `app/consultation.py`：六类问题自动路由，缺失出生/年份/伴侣/候选时刻/方案时显式澄清；只调用必要的原有计算引擎，提供字段证据、trace、原始结果和限制。
- 同一执行器通过 REST `/api/consultation`、MCP `consultation_execute`、CLI `consult --input`、Web 新的「AI 咨询工作流」使用；MCP 现为 **25 Tools / 17 Resources / 15 Prompts / 18 Skills**，Web **22 视图**，项目版本不变。
- 新增客户端携带的非敏感 `continuation` 游标（意图/宫位/年份/轮次），不保存服务器会话、出生记录或现实个人事件。合盘要求显式许可；现实情况作为用户自述而非计算证据或已核事实。
- 新增 12 项可执行咨询回归，并对真实 HTTP、MCP 2026、CLI、Chromium、wheel 与现有安全流程进行验证；不将此确定性工具编排冒充自主语言模型咨询。


## 主营业务与 Agent 工作流全面审计 — 2026-10-10（版本保持 v.0.1.0）

- 对照公开 Tianfu Agent 功能说明、iztro 动态流曜 API 和当前 `app/`/`static/`/`skills/` 代码，指出**核心缺口是以问题为中心的咨询 Agent/多轮记忆/知识规则库**，不是 MCP 工具数量；新增 `docs/research/PRODUCT_BUSINESS_AUDIT.md` 深度业务审计与 `CONSULTATION_WORKFLOW_SPEC.md` 六场景验收规范。
- 在**现有** `skills/structured-dossier/SKILL.md` 中加入六种业务路由、必要信息确认、具体 MCP 调用选择、事实与传统/假设分层、流派冲突处理、无持久化内存时的诚实降级。
- 原有 MCP `prepare-report` Prompt 增加问题驱动路线判断，保持 24 Tools、16 Resources、15 Prompts、18 Skills，不新增版本、不伪称已运行自主 LLM 或私有平台功能。
- 新增导向性回归测试；没有新增付费内容、受限网页抓取、私有天府 API 或虚构科学预测功能。生产 OAuth、公网真实多轮客户端仍未验收。


## 深度证据与独立参考研究 — 2026-10-10（版本仍为 v.0.1.0）

- 新增 `app/evidence.py`：字段级追溯、10 条规则及公开参考目录、单字段 SHA-256、八字/紫微输出对象 SHA-256、跨立春/农历年界口径校验、十二宫三方四正/飞化结构和 4 项内部一致性检测。
- REST `/api/deep-review`、MCP `deep_evidence_review`、`astro://rules/evidence` 资源和 `deep-evidence-review` Prompt、CLI `deep-review`、Web「深度证据」、综合报告 `include_deep_evidence` 打通。**现有 18 Skills 不增加版本、不另建工程目录**；加强 `structured-dossier` Skill 的证据溯源规则。
- 修复一个真实的演示复算缺陷：公开样本使用 `gender=unspecified`，测试误传 `female`，导致紫微完整摘要不同。所有深度结果与金样本现在明确包含 `input_parameters` 并有性别敏感性测试。
- Python wheel 安装包现在也包含新增的 `docs/research` 方法调研和 `examples` 复核材料（与源代码包内容一致），增加隔离安装验收，避免规则出处在安装后失联。
- 增加 `docs/research/FEATURES_AND_REFERENCES.md`，以公开资料区分天府 Agent 的产品自述与可独立实现/验证功能；示例、边界反例、浏览器/MCP/HTTP/隔离安装测试同时覆盖。
- 现有断言同步核对 24 Tools、16 Resources、15 Prompts、18 Skills、21 Web 页签，版本保持 `v.0.1.0`。**这些参考不构成专业盘全量认证或现实人生预测。**

## 开发阶段整包合并（版本仍为 v.0.1.0）— 2026-10-10

- 可选 `iztro-py` 专业紫微适配器支持本命与选定日期动态盘输出；独立于原生子集，依赖未安装时拒绝虚假返回。
- 奇门逐宫参考盘比对 REST/MCP/UI/CLI，5 个公开样本各 15 个外部提供字段核对，共 75 个字段；其他字段需后续外部证据。
- MCP Skills draft 导入接口 `skills/list`、`skills/get`，提供 SHA-256 资源完整性校验，优先暴露 5 个供扫描；完整工程 18 Skills、23 工具与 20 页签。
- 创建了真实的 ChatGPT 私有 Skills Plugin（没有公网计算服务器）；新增 `scripts/build_plugin.py` 和私有插件产物。
- 更新真实 Uvicorn HTTP、Chromium 控件及隔离 wheel 安装回归；没有正式公开发布或版本升级。

## 安装包、协议输入与跨时区日期修复 — 2026-10-10

- 修复 wheel 分发包遗漏 `static/`、MCP `docs/rules/` 与 `skills/` 导致独立安装后 `app.main` 无法启动的严重交付问题；新增构建时打包资源、`MANIFEST.in`、真正的临时目录 wheel 安装烟雾测试，并纳入 CI。保留源码根目录为唯一可编辑的规则/静态资源来源。
- 统一 REST 与 stdio MCP 的严格 JSON 入口校验：拒绝 `NaN` / `Infinity`、浮点溢出、重复键、不可编码的孤立代理项及过深嵌套，修复已复现的 HTTP 500；增加畸形 JSON 与返回错误码回归。
- 排盘质量审计新增“所在地有效公历日 vs 相同绝对瞬间的北京日界农历”的明确对照及人工复核提示。保留既定本命盘口径，不静默改变任何八字、紫微星曜位置；新增 2024 春节时区交界参考用例和 Web 显示。
- 奇门增加横跨阴阳遁、多个年份与时辰的九宫排布不变量测试；仅核验内部结构，并不等于跨流派逐宫外部认证。
- **版本仍固定 `v.0.1.0`，无新版目录、无正式公网发布**。


## 实际可靠性与 Docker 安全启动修复 — 2026-10-10

- 修复默认 Docker Compose 将宿主请求视为容器网桥非回环来源而拒绝访问（403）的问题：不降低匿名安全边界，改为仅宿主回环发布 + 强制认证的 Compose，新增私密随机令牌初始化脚本；CI 增加实际 Docker 容器运行与 REST/MCP Host/Origin 鉴权检查（执行环境需有 Docker）。
- 修复 MCP 收到数组/对象形式的协议版本、非对象初始化版本、非法 `params._meta` 等时抛出 `TypeError` 的缺陷，全部返回结构化 JSON-RPC 参数错误并保持 stdio/HTTP 服务存活。
- 修复本地非 8000 端口网页调用 REST/MCP 被误拒绝，同时避免错误信任其他本地端口；本机浏览器 Origin 与实际 Host、方案、端口严格一致，公网模式仍按显式来源白名单。
- 新增独立回归、真实 Uvicorn 自定义端口联调、Docker 网桥模拟。外部 OAuth、全紫微/奇门流派和远程部署仍未完成；项目版本保持 `v.0.1.0`。

## 项目统一命名：玄枢 · XuanShu — 2026-10-10

- 正式开发目录由旧工程名直接更名为唯一的 `xuanshu/`；Python 分发包、命令行 `xuanshu`、MCP 服务标识、Docker 服务、前端标题及导出文件均统一为 **XuanShu**，**版本仍为 `v.0.1.0`**。
- 保留旧 localStorage 档案单次迁移及旧 AES-GCM 加密备份的**只读导入兼容**，避免更名后个人档案不可恢复。
- 修正 CI 仍验证旧版本 ZIP 的失效路径，增加一致性测试与旧格式真实 WebCrypto 解密测试；本地真实 HTTP 与 Chromium 桥接测试均重新执行。
- 奇门按公开 MIT 项目的五组参考盘额外核对了 45 个九宫暗干单元格，并新增全部九宫暗干数学不变量与 REST/MCP 一致性测试。此项**不代表**全部门、星、神与不同流派通过验收。

## 本次合并维护 — 2026-10-10

- **固定 `v.0.1.0` 未发布版本号**；统一 Python 包、Web、API/MCP、示例与 ZIP 的版本标识，禁止发布前叠加版本。
- 紫微保留全部 14 主星与原 18 颗辅助星位置，新增 26 颗辅助/杂曜、四组本命十二神和可选虚岁小限；**仍不是专业全星系**。
- 解决 JSON 快照输出中 `frozenset` 导致的辅星排列不稳定；保留原始独立参考盘，并增加扩展盘回归、结构约束与跨 `PYTHONHASHSEED` 测试。
- 修复代码、文档、MCP 工具描述与报告仍标注 18 颗辅星的过期信息。

## 奇门与 OAuth 资源鉴权研究 — 2026-10-10

- 新增限定流派的 **时家奇门拆补转盘**：九宫地干/天干、三元九局、八门九星八神、旬首值符值使、时旬空亡。源码 `app/qimen.py`，接口 `/api/qimen` 与 MCP `qimen_hour_chart`、CLI 和 Web 九宫视图；已与公开 2026 五组盘的 6 项字段交叉对照；逐宫外部流派验收仍未完成。
- 新增外部 JWT OAuth **资源服务器**：`app/oauth_resource.py`，RFC 9728 资源发现、签名/iss/aud/sub/scope/exp 校验、HTTPS JWKS、401 Bearer 挑战；没有内建身份提供商或实际公网安装。
- 扩展至 **21 Tools、15 Resources、14 Prompts、16 Skills、18 个 Web 视图**。补充计算、离线 OAuth 和 REST/MCP 回归及文档。
- 与此前开发阶段一样，不把工程测试通过等同于命理算法得到权威认证、完整系统上线或远程 OAuth 联调。

## 大运与节令边界研究 — 2026-10-10

- 新增独立 `app/advanced.py`：传统八字大运十年干支、十二节顺逆、三日一岁名义起运、可配置顺逆方向和近似公历时间投影；不输出人生吉凶和成功率。
- 新增出生时间误差的事件驱动边界地图：按 UTC 区间检测真实时辰/日界/DST/历史 UTC 偏移并二分至秒，叠加天文交节事件，逐段调用八字与部分紫微引擎。
- **修复**节令精确时刻处的八字月柱浮点边界偏差；建除值日月建复用同一节令时刻判定；大运准确处理出生恰在交节的零时差情况，避免把起运年数误算到下一节。
- 新增 39 项精确节令参数化测试，覆盖 2000、2024、2033 各十二节的交节前/当刻/后瞬间，另有真实排盘、时区转换和大运零时差测试。
- 通过 Web / REST / 2025/2026 MCP / stdio / CLI / 结构化 Markdown 报告接入；合计 **20 Tools / 13 Resources / 13 Prompts / 15 Skills / 17 个 Web 视图**。
- 增加发布版本一致性校验，并明确“数值秒级定位”不等于出生资料的真实精度；完整奇门、全紫微流派、OAuth、多租户和公网 HTTPS 仍未实现。

## 历法、决策和多端工作流研究 — 2026-10-09

- 新增独立建除十二值日（月建按太阳黄经节令月、日支按六十甲子日循环）；可查询 1–93 天并过滤值日，交节日提醒日内值日可能变化。
- 新增 1–30 年年干四化固定本命盘叠加，可关注单宫及统计各宫符号出现数量，不得当成吉凶或事件预测。
- 新增现实方案透明加权决策矩阵（2–8 方案、1–8 维度、0–5 主观评分、权重归一化和剔除单一维度敏感性）。与命理结果完全隔离。
- 三项功能贯通 CLI、REST、MCP、Web 工作台及说明文档；扩展到 18 Tools / 11 Resources / 11 Prompts / 13 Skills、15 个 Web 视图。
- 决策矩阵 Web 编辑器加入指标/方案动态增删，拒绝空值、布尔伪装评分和空白问题；新增真实 Chromium 点击测试、命令行对照和新接口鉴权回归。
- 新增独立规则出处与对照用例。通过 DevMate 检查本地 REA 安装，但尊重目标网站禁止逆向及未经许可自动访问的公开服务条款，**未对其执行 REA 抓包或源码提取**。
- 继续保留既有的计算、加密备份与部署安全限制；奇门其他流派、紫微完整流曜、完整 OAuth 登录和公网部署仍未实现。

## 历法审计与协议加固 — 2026-10-09

### Independent audit and reliability

- Audited published Hong Kong Observatory new-moon starts with 26 independent month-start fixtures (2024 and 2033), including leap month handling.
- Surfaced published future new-moon uncertainties (2057, 2089, 2097) without silently changing astronomical outputs; known model/reference divergence is now explicitly flagged.
- Added comprehensive `chart_quality_audit` for hour/day/jie boundaries, solar-time day changes, cross-timezone conventions and historical timezones. Fixed the prior almost-always-on 60-minute warning by making the default **15 minutes**.
- Added the audit to REST, CLI, HTTP + stdio MCP, reusable agent rules and the provenance-bearing Markdown report.

### Interoperability and security

- Strictly validate `io.modelcontextprotocol/clientCapabilities` for 2026-07-28 metadata requests; emit appropriate cache hints on modern discovery/list/resource operations; preserve 2025 compatibility.
- Harden local HTTP Host allowlisting to prevent DNS-rebinding abuse and reject untrusted REST Origin headers, not just MCP Origins.
- Added a real loopback Uvicorn HTTP smoke test, optional real Chromium DOM smoke with FastAPI TestClient bridge, and expanded unit/regression suites.
- Updated docs, CI release version and security status; added `docs/DEEP_AUDIT.md` differentiating resolved defects from unsolved production and professional-calculation limitations.

### Important limitations

- Browser bridge tests are *not* full network E2E; real Docker image, OAuth, remote Plugin registration, production HTTPS and native third-party client interoperability are not claimed.
- Multi-school full Zi Wei, full Qi Men Dun Jia and extensive independent 1901–2099 reference comparison remain unfinished.


## 计算、客户端与安全基础 — 2026-10-09

### Core and calculation

- Added three clock-basis choices: civil clock, geographic mean solar time and equation-of-time-corrected apparent solar time, with IANA timezone / DST ambiguity checking.
- Added a side-by-side time-basis audit and difference comparison for two input/rule configurations.
- Added BaZi branch relationships, transparent rule metadata, and a structured provenance-bearing combined BaZi / partial Zi Wei Markdown report.
- Added year-stem four-transformation overlays and 12-palace three-harmony/opposite references for partial Zi Wei.
- Added **lunar-to-Gregorian inverse conversion** with leap-month validity checks and round-trip validation.
- Added **sampled birth-time uncertainty analysis**, including safe handling of UTC and DST, and clear limits on non-exhaustive sampling.

### Application and interoperability

- Increased MCP surface to **14 tools, 7 resources and 7 prompts**; introduced **2026-07-28** stateless protocol compatibility alongside legacy 2025 MCP initialization.
- Published **9 independent agent skills** and reusable Python CLI, REST and stdio interfaces.
- Upgraded local Web workbench to 11 tabs, with embedded calendar conversion / birth-window tools, year overlays, time audits, rule comparisons and provenance reports.
- Added local AES-256-GCM WebCrypto encrypted archive export/import with PBKDF2 key derivation; browser profiles remain explicitly opt-in and otherwise saved in plaintext localStorage.

### Distribution, hardening and verification

- Public mode now requires 32+ character static Bearer token and exact host allowlist, plus Origin validation for MCP and streamed HTTP request-size enforcement.
- Updated Python CI matrix to 3.11/3.12/3.13, added comprehensive HTTP/MCP and calendar tests, expanded Docker and security documentation.
- Added a reproducible source ZIP build utility with file SHA-256 manifest and independent archive verification.
- **119 tests passing before packaging**, with a separate WebCrypto smoke test and local live HTTP smoke test; no claim of Chromium E2E, Docker runtime or permanent HTTPS deployment.

### Known limitations

Partial Zi Wei with school-specific tables only; Qi Men Dun Jia, complete professional astrology, cross-device identity/OAuth, long-term cloud memory and fully deployed remote ChatGPT/Claude plugins are **out of scope for this release**. Traditional interpretation is cultural rather than scientifically validated prediction. Swiss Ephemeris AGPL/commercial licensing applies.

## 排盘与本地数据基础 — 2026-10-09

- BaZi hidden stems, ten gods, Na Yin and solar-term references; natal Zi Wei four transformations, palace details, calendar / pair comparison and local profiles.
- Expanded to 8 tools, 3 resources, 3 prompts, 4 skills and 7 workbench views.

## 项目初始化 — 2026-10-09

- Initial BaZi, partial Zi Wei, Chinese lunar calendar, REST and stateless MCP HTTP / stdio with a local Web console.