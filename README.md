# 玄枢 · XuanShu v.0.1.0

**最新 Windows Python 3.15 回归（2026-10-10）：723 项通过、1 项条件跳过**；25 个 MCP 工具与 REST 一致，真实 Chrome→HTTP、隔离 wheel、AES-GCM 已验证。最新版 Python 3.15.0 已安装并用于玄枢；旧终端显示 3.13.7 时需要重新打开以刷新 PATH。

**本机 Python 最新版：** 已安装 Python 3.15.0（官方 2026-10-09 发布），玄枢虚拟环境与用户 PATH 默认均已指向 3.15；如旧 DevMate/PowerShell 窗口仍显示 3.13.7，请重新打开窗口刷新环境，旧版保留供其他项目兼容使用。

**工作台使用体验：** Ctrl+K 搜索 24 项功能、同义词查找、方向键与 Home/End 切换、工具直达链接（仅存工具 ID）、出生参数改动后旧结果标记，以及咨询报告 Markdown 一键复制。详情见 docs/research/UX_AUDIT.md。


## AI 对话（可选，需要自备模型 API Key）

工作台首页「AI 对话」用自然语言提问，由你配置的语言模型调用玄枢的 33 个确定性工具回答；模型不自己排盘，每次工具调用的参数、结果摘要和 SHA-256 都能在「推理过程」里展开核对。对应天府 Agent 的对话、主动追问、跨对话档案记忆、人生事件回溯和多语言输出，对齐清单见 [docs/research/TIANFU_PARITY.md](docs/research/TIANFU_PARITY.md)。

```bash
# Claude（官方 Anthropic SDK，默认 claude-opus-5-5）
python -m pip install '.[chat]'
export ANTHROPIC_API_KEY=...            # 可选：XUANSHU_LLM_MODEL、XUANSHU_LLM_EFFORT=low|medium|high|xhigh|max

# 或任意 OpenAI 兼容接口（DeepSeek、通义千问、本地 Ollama 等）
python -m pip install '.[chat-openai]'
export XUANSHU_LLM_PROVIDER=openai XUANSHU_LLM_MODEL=deepseek-chat XUANSHU_LLM_BASE_URL=https://api.deepseek.com/v1 XUANSHU_LLM_API_KEY=...
```

- REST：`GET /api/chat/status`、`POST /api/chat`，以及同样参数的 `POST /api/chat/stream`（逐行 JSON：工具调用开始与完成、命盘卡片、回答文字、最后是完整结果；断开连接即停止）。不提供 MCP 版本：MCP 客户端本身就是模型，直接调用 33 个工具即可。
- 对话体验：回答边写边显示，可随时停止（Esc）或重新回答、编辑上一个问题；回答按 Markdown 排版；模型排出的八字、紫微、奇门盘以小卡片嵌在回答里；每条回答后按本次用到的工具给出追问建议。
- 择日择时：工作台「择日择时」或 `POST /api/date-scan`（MCP `date_candidate_scan`），在最多 93 天里按建除值日、交节日、本命相冲筛选候选日，可附加指定时刻的时家奇门盘；按日期列出，不打吉凶分。
- 人生事件回溯：档案里记录人生事件后可一键对照（`POST /api/life-path`，MCP `life_path_review`），把每个事件与大运、流年干支、年度四化和本命地支关系并列，不需要配置模型。
- 出生城市：内置 65 个国内外城市的时区和市中心经纬度，选中即自动填写；页面可「添加到主屏幕」。
- 回答语言：简体中文、繁體中文、English、日本語。
- 界面语言：右上角切换简体中文、繁體中文、English、日本語，只记住所选语言代码。繁體按字词表转换全部界面和计算结果（`static/zh-tw-map.js` 由 `scripts/build_zh_tw_map.py` 从 OpenCC 数据生成，保留天干「干」、地支「丑」、「斗数」「台辅」「咸池」等术语）；English 与日本語覆盖界面和计算结果：标签、宫位、星曜、四化、十神、节气、说明与限制文字都有对照表（`static/i18n-extra.js`，由 `scripts/build_i18n_extra.py` 从 `scripts/i18n_extra.json` 生成，约 1400 条）；拼接出来的文字按已知词组就地替换。天干地支（含「庚辰」这类柱值）在所有语言下都保持汉字；你自己输入的档案名、记忆、人生事件和方案名不会被改写。
- 双人合盘：「双人对照」页同时给出八字四柱对照和紫微宫位叠盘（`POST /api/ziwei-pair`，MCP `ziwei_pair_overlay`）：两张命盘按十二地支对齐，列出各自命宫、身宫落在对方哪一宫，以及一方生年四化落入对方命盘的宫位；不打匹配分。AI 对话中需勾选「已获第二人同意」才会调用。
- 档案记忆与人生事件按本机档案隔离，**只存在浏览器里**，随每次提问发送；模型只能“提议”记忆，你点击后才保存。对话历史默认不保存，需在档案里主动勾选。服务器不保存任何对话或出生资料。
- 回答置信度：每条回答下方显示「排盘置信度」——按你选的出生时间误差（±2 分钟到 ±2 小时），在 ±1 倍和 ±2 倍误差处重算年、月、日、时柱和紫微命身宫，没变化为高、只在 ±1 倍内不变为中、±1 倍内就会变为低。默认还会做一次「独立核验」：另一次模型调用只看问题、回答和工具原始结果，逐条标注有工具依据、部分依据或无依据（可关闭以节省调用）。
- 多流派会诊：对话页「回答方式」可选「多流派会诊」。八字、紫微斗数、奇门与择时三位专家各自只用本流派工具排盘、写报告，综合者再依据报告回答，并列出各流派的一致与分歧。专家原文和每一步工具调用都能展开查看。会诊会多次调用模型，费用高于单一助手。
- 未配置模型时页面会提示如何启用，其余工具照常使用。

**工作台体验（2026-10-11，对照天府的超越项见 [docs/research/SURPASS_TIANFU.md](docs/research/SURPASS_TIANFU.md)）：**
- 配色：右上角在跟随系统、浅色、深色之间切换，只在点击后记住选择。
- 紫微运限：紫微十二宫上方切换本命、大限、流年，宫名按该层重排，限干、年干四化以描边徽章叠加，三方四正连线跟随该层命宫；流年层同时标出大限与小限。
- 不知道出生时辰：勾选后时间按 12:00 占位，命盘页可一键比较十二个时辰的时柱、命宫、身宫、命宫主星与五行局，并标出全天不变的柱。
- 农历生日：出生资料里输入农历年月日（含闰月）与时辰，换算后填入公历。
- 奇门起局时刻：默认取此刻（本机时区），也可指定时间或沿用出生时间。
- 分享卡片：本机绘制 PNG，不上传；出生日期、时间默认不显示。打印或存为 PDF 有专门的打印样式。
- 手机上出生表单折叠成一行摘要，紫微盘横向滑动保持可读字号。
- 大运流年时间条：四柱下方横排十步大运（十神、干支、起止年份、起运年龄），点选一步大运展开其中十年流年；点某一年直接打开紫微盘的同年流年层。
- 四柱反查（`POST /api/pillars-to-dates`，MCP `pillars_to_dates`）：给出年月日柱（时柱可选），列出 1901–2099 年间所有对得上的出生时段，起止时刻用与排盘相同的计算逐秒校准；天干组合不合五虎遁、五鼠遁时直接说明不可能；每个时段可一键排盘。
- 命盘导入核对（`POST /api/chart-import-check`，MCP `chart_import_check`）：粘贴其他软件排出的命盘（简体或繁体），识别四柱、命宫、身宫、五行局、命主身主、各宫主星和生年四化，与玄枢逐项比对；有差异时换用常见的不同规则（23:00 换日、闰月归属、平太阳时或真太阳时、扣除夏令时，以及两两组合）重算，列出能完全复现对方命盘的规则，可一键套用。
- 今日历法（`POST /api/daily-almanac`，MCP `daily_almanac`）：按本机时间列出今天的四柱、农历、所在节气与距下一节气的进度、建除值日和月相（附下次满月、新月时刻）；生成命盘后再列出今天四柱对日主的十神，与本命四支的六冲、六合、同支，以及当前大运。页首有一行今日提示，点开即是完整卡片。只列历法事实，不打吉凶分、不给宜忌。卡片上可以选其他日期和时刻、逐日翻看；页面开着时整点自动刷新。
- 多人关系（`POST /api/group-relations`，MCP `group_relations`）：从当前命盘、本机档案和临时添加的成员里选 2 到 8 人，列出成员四柱、可筛选的关系图、日干十神矩阵（行看列）、天干五合、地支六合/六冲/六害/相刑/同支明细、成员间凑齐的三合与五行分布。时辰不详的成员不参与时柱比较。只标传统标签，不打匹配分、不排名。
- 规则差异对照（`POST /api/rule-matrix`，MCP `rule_sensitivity_matrix`）：把当前出生资料换成各家常见的不同规则（23:00 换日、闰月归属、平太阳时或真太阳时、扣除夏令时，以及两两组合）逐一重排，表格标出四柱、农历、命宫、身宫、五行局、命宫主星和生年四化里哪些格子会变、哪些在所有规则下都不变，并提示出生时刻离交节很近等情况；任一方案可一键套用到出生资料。不判断哪种规则正确。
- 节气与月相日历：`GET /api/solar-terms/{year}.ics?moon=true` 在二十四节气之外加入新月、上弦、满月、下弦的时刻；「历法日历」页和今日历法卡片都能直接下载。
- 性能：页面与静态资源 gzip 压缩，并按 ETag 校验缓存（未改动的文件返回 304）；API 与对话流不压缩。English、日本語与繁體的翻译表只在切换到该语言时才下载，简体中文首屏少下载约 245 KB。

**Python 3.15 与体验改造（2026-10-10）：** Windows 系统用户默认及本项目虚拟环境已升级至 Python 3.15.0，uv 更新为 0.13.0；旧 3.13.7 安装和虚拟环境保留回退。界面提供常用功能优先、搜索全部 22 项、五类快捷咨询、折叠选项、草稿保留与可复制的本地 MCP 配置。详情见 docs/research/UX_AUDIT.md。Linux Docker 仍使用已验证的 Python 3.12。

**发行包隐私：** 构建脚本不会包含 .artifacts 测试截图、.env.local 等真实环境配置或私钥文件；校验器也会拒绝这些路径。

**浏览器测试截图：** 默认保存到 Git 忽略的 .artifacts/browser-smoke/，不会覆盖仓库内的展示截图。仅在需要明确更新展示素材时，使用 scripts/browser_smoke.py --screenshots-dir screenshots。

**Windows/CI 验收（2026-10-10）：** 713 项 Python 测试通过、1 项环境条件跳过；25 项 MCP/REST 工具结果一致；真实 Chrome HTTP、Docker 多阶段构建与容器鉴权已实测通过。详见 TEST_REPORT.md。公网 OAuth/远程 MCP 和专业流派认证仍须独立验收。

**本地优先、独立实现、可测试的传统历法 / 八字 / 紫微（部分）/ 时家奇门（限定流派）计算和 AI Agent 工具平台。**

提供 Web 工作台、Python CLI、REST API、MCP Streamable HTTP + stdio、Agent Skills、JSON / ICS 导出以及可选浏览器端加密备份。**不依赖天府 AI 的私有接口、付费内容或源码，与该网站无官方关联。**

> 命理象征是传统文化范畴，**未获可靠的科学预测效力验证**。不得作为个人医疗、投资、法律、婚姻或其他重要决策依据。

**开发状态：未正式发布，版本始终固定为 `v.0.1.0`；功能更新不叠加版本号。**

**项目名称：** **玄枢 · XuanShu**；Python 包名、Docker 服务名和 MCP 服务标识统一为 `xuanshu`，命令行安装入口为 `xuanshu`。原浏览器档案首次打开时可无损复制到新的本地存储键，历史 AES-GCM 加密备份仍可导入；旧备份格式仅保留为兼容读取。名称尚未进行商标或域名可用性调查。

## 全工具验收与 Windows 本地检查（开发阶段）

新增严格的全工具契约审计：逐项测试 **33 个 MCP Tool 与对应 REST 的输出一致性**。未安装的可选 `iztro-py` 必须明确返回「依赖未安装」，不允许被计算成功计数。运行：

```bash
python scripts/full_functional_audit.py
python scripts/full_functional_audit.py --json
```

Windows 本机验收脚本位于 `scripts/windows_acceptance.ps1`。它只在当前项目 `.venv` 安装测试依赖，可选安装独立 `iztro-py==0.5.0` 与 Playwright，执行 pytest、全 MCP Tool→REST 对照、真实 loopback HTTP、CLI、Node WebCrypto 与本地 Chrome DOM。**Docker 是否能启动以实际 `docker info` 为准，脚本不会自动公开发布容器。**
在 Windows 测试时，`windows_acceptance.ps1` 还会执行 **Chrome 直接访问 Uvicorn HTTP** 的端到端检查（`scripts/windows_browser_e2e.py`），区别于页面请求桥接测试；此项不等于公网部署验收。

```powershell
cd A:\Project\ProjectWaiting\xuanshu
powershell -ExecutionPolicy Bypass -File .\scripts\windows_acceptance.ps1
```

这里的 25 工具对照是**接口可用性与一致性**，不是 25 种术数的独立正确性认证。公网 OAuth 登录、真实远程 ChatGPT/Claude MCP 客户端连接与 Docker 容器运行仍须单独完成。

## 项目交付矩阵

| 范围 | 已完成（实际接口/源码） | 重要限制 |
|---|---|---|
| 现代中国农历 | 1901–2099 年公历转农历、**农历反查公历（含闰月校验）**、24 节气时刻；连续 1–31 日查询；ICS 节气订阅文件 | 现代中国 UTC+8 月相和中气规则，不等于历朝全部历史历法 |
| 八字四柱 | 立春年界、**精确十二节令瞬间月界**、日时柱、子初换日选项、十神、藏干、纳音、地支传统关系、五行统计 | 不生成科学的性格、吉凶、喜用神判断 |
| 八字大运干支 | **顺逆方向**（可手动覆盖）、下一/上一十二节、三日一岁名义起运年龄、最多 12 个十年干支、近似时间轴 | 传统流派存在不同起运换算；**公历投影不是精确交运日**，不预测现实事件 |
| 地理与时制 | IANA 时区、DST 缺失/重叠时刻校验、经度平太阳时、真太阳时（均时差）、三套时制审计、出生时间误差区间离散采样、**秒级数值精度的模型边界地图**、两套排盘规则比较 | 秒级是模型断点定位精度，并非实际出生记录可靠精度；历史时区和流派边界有差异 |
| 紫微斗数 | 命/身宫、十二宫、五行局、十四主星、44 颗选定辅/杂曜（含本轮新增 26 颗）、四组十二神、命主身主、小限虚岁、宫干与生年四化、三方四正、大限年龄区间 | **原生盘不是**全星系专业盘；提供可选 iztro-py 独立扩展后端，但未做真实安装运行与逐星认证 |
| 年干四化 | 指定农历年十干四化映射至本命星曜宫位 | 不等同于完整流年命盘 |
| 连续年度对照 | **1–30 个命名农历年的四化叠加**、可按本命宫位筛选 | 仅静态映射，不等同完整流年或人生预测 |
| 建除十二值日 | **1–93 日传统月建值日查询**、节令日内分界标记、标签过滤 | 不给黄历吉凶与宜忌承诺 |
| 透明决策矩阵 | 用户自定义 2–8 方案、1–8 指标权重，0–5 主观评分、单指标敏感性 | 不使用命理评分，亦非现实成功概率 |
| 双人盘 | 4 组四柱和地支传统关系对照 | 不给虚假关系匹配分数 |
| Web 工作台 | **24 个视图**（含 AI 对话、择日择时），包含大运与边界地图、十二宫可点击、四化/时制查询、档案管理、JSON 导出 | 无云端账户/云同步 |
| 浏览器隐私 | 可选 localStorage 保存/删除；WebCrypto AES-256-GCM 加密导出/导入，PBKDF2 口令推导 | **保存到浏览器的记录是明文**；仅加密备份文件，不替代磁盘加密 |
| MCP / Agent | **30 Tools、17 Resources、15 Prompts、18 Skills**；HTTP+stdio 共用计算函数 | 外部 OAuth JWT 资源服务器；无实际授权服务器、租户隔离、主动 SSE 或公网连接验收 |
| 工程交付 | Docker、Compose、Windows PowerShell 启动、Linux/macOS shell、CLI、GitHub CI、pytest / MCP / HTTP 校验 | 永久公网 HTTPS 部署需使用自己的授权主机及域名 |

## 问题驱动咨询执行器（已实现，可运行的确定性工作流）

真实业务入口不再要求用户预先理解每个命理工具。一个问题将自动路由到 `natal` / `career` / `relationship` / `timing` / `decision` / `rules` 六类工作流，逐步检查缺少的资料、运行所需的现有计算引擎，并输出可查的 `tool_trace`、`tool_results`、`observations`、`missing_inputs`、`limitations` 与 Markdown。**这不等于自主 LLM Agent，也不自动推算人生结果。**

```bash
# 不向服务器保存资料；基于请求中的出生信息执行多工具计算
xuanshu consult --input examples/consultation-demo.json
```

REST：`POST /api/consultation`；MCP：`tools/call` 指定 `consultation_execute`；CLI：`xuanshu consult --input <file|->`；Web 工作台首个「AI 咨询工作流」页面可直接输入问题。机器生成的 `continuation` 只含意图、焦点宫、农历年与不超过 12 的轮次数；为了隐私，下轮**仍需重新提交出生资料**。`real_world_facts` 中用户自述只在本次执行中使用，标记为未经独立证实；他人资料的处理必须显式确认 `partner_authorized=true`。

参考：[真实执行与六场景验收](docs/research/CONSULTATION_EXECUTION_ACCEPTANCE.md) · [咨询规则资源](docs/rules/consultation.md) · [可复现输入](examples/consultation-demo.json)。

## 核心业务定位审计：从排盘计算到问题驱动的 AI 咨询（开发中）

通过公开资料与实际源码重新核对，玄枢的目标业务是**面向真实问题的东方术数文化咨询工作流**，而非只罗列计算工具：`问题澄清 → 校验时制 → 选择八字/紫微/奇门 → 规则与证据核对 → 现实条件与多方案分析 → 可追问的报告`。ChatGPT/Claude 可在它们的模型环境中编排这些 MCP 工具；**当前已实现确定性的咨询工作流执行器**（问题路由、按需调用工具、规则证据、输入缺失提示、客户端续问游标）；**仍无自主 LLM 推理、跨会话服务器记忆或真实在线计算 Plugin**。

- [完整业务差距审计与业务架构](docs/research/PRODUCT_BUSINESS_AUDIT.md)：分析公开参考产品的业务闭环、当前代码完成度、缺失的 Agent/知识库/长期记忆、专业流派和生产部署，以及按实际用户价值排序的工作包。
- [六类咨询场景的工作流与验收规范](docs/research/CONSULTATION_WORKFLOW_SPEC.md)：本命解释、职业年度、双人关系、候选择时、Life Path、多轮流派对照的工具规划、输入参数、证据层级和失败处理。
- **现在有真正可调用的咨询执行器**：`app/consultation.py` 的 `execute_consultation` 支持六种意图、必需资料澄清、工具编排、规则证据与 `continuation` 客户端续问游标；以 `POST /api/consultation`、MCP `consultation_execute`、CLI `xuanshu consult --input ...` 和 Web「AI 咨询工作流」调用。它运行确定性工具，不调用 LLM 或存储用户出生资料。

## 深度分析与公开参考（开发阶段新增，未发布）

补齐此前只有“计算结果 + 模块名”的分析弱点：新增**基于字段证据的八字/紫微跨体系规则审阅**，严格标注*哪些是计算事实、哪些只是传统规则、哪些还没有外部认证*。

- `POST /api/deep-review`、MCP `deep_evidence_review`、CLI `xuanshu deep-review`、Web「深度证据」使用同一确定性引擎。
- 选定十二宫中任意宫位，返回四柱/藏干/十神、六冲六合等结构标记、三方四正、生年四化和宫干飞化，以及可选农历年度四化叠加和已知时制边界。
- 每条 `findings[]` 提供**原始 JSON 字段路径 + 字段值 SHA-256 + 规则 ID + 限制说明**。响应保留 `input_parameters`（包括出生时间、时区、性别及流派选项），另给出八字/紫微完整计算对象的可重复 SHA-256 摘要，并包含 4 项内部一致性校验、官方/开源方法参考链接和 Markdown 导出。
- 自动识别八字的**立春年界**和原生紫微的**农历年界**何时不同；共用输入与历法不算两次独立证据。紫微运限会受性别参数影响；两次散列比较前须核对完整输入，摘要是校验值而非数字签名。报告可选 `include_deep_evidence=true` 追加证据审阅。
- 这是**文化规则下的结构分析，而非预测性人格画像、咨询效果或专业逐盘认证**。第三方公开参考只能证明相关计算口径/接口存在，不能证明星曜/排盘全部准确。

```bash
xuanshu deep-review --date 2024-02-07T12:00 --palace 官禄宫 --year 2026
# 或 POST /api/deep-review：{ "birth": { "birth_datetime": "2024-02-07T12:00" }, "focus_palace": "官禄宫", "lunar_year": 2026 }
```

具体证据方法见 [`docs/rules/evidence.md`](docs/rules/evidence.md)；功能对标、可信资料与未验收差距见 [`docs/research/FEATURES_AND_REFERENCES.md`](docs/research/FEATURES_AND_REFERENCES.md)；带输入与验证步骤的独立示例见 [`examples/DEEP_ANALYSIS_WALKTHROUGH.md`](examples/DEEP_ANALYSIS_WALKTHROUGH.md)。

## 专业紫微、外部奇门参考盘与插件集成（未发布，新增）

**原生引擎仍保留**，独立增加以下功能（不会悄悄替换历史命盘）：

- 专业紫微 **可选提供方**：`pip install 'xuanshu[professional]'` 安装独立 MIT 许可证 [`iztro-py`](https://github.com/spyfree/iztro-py)，在 `POST /api/ziwei-professional` 或 `ziwei_professional_chart` MCP 工具输入明确出生资料及可选公历目标日期/时辰，得到提供方本命与 `horoscope` 动态叠加；`xuanshu ziwei-pro --date ... --gender female --target ...` CLI 和「专业紫微」页也已接通。**当前隔离环境无法获取该可选依赖，因此只通过模拟提供方接口进行联调；不得把它写成真实专业盘已验收。** 返回包含来源、时区假设与提供方说明。
- **奇门参考盘逐宫校验**：`POST /api/qimen-reference-audit`、`qimen_reference_audit` MCP 工具及「奇门逐宫核验」页面，接受用户提供且注明出处的参考盘，最多 9 宫、逐字段核对地盘干/天盘干/暗干/门/星/神/空亡等。5 张公开 MIT 参考盘提供 6 个顶层字段和 9 个暗干，共 **75 个独立提供的比较字段**符合；其余字段和流派不自动标记一致，不能称为全门派已验收。
- **MCP Skills 导入**：扩展 `io.modelcontextprotocol/skills`（draft SEP-2640 的 OpenAI 子集），支持分页 `skills/list`、`skills/get`、`resources/read` 的原文与 SHA-256 校验，按平台扫描上限只暴露 **5 个优先工作流**。项目本身共有 18 个 Skills，均可通过 `scripts/build_plugin.py` 打成单独的私有技能插件包。
- **ChatGPT 私有插件**：已建立私有 `xuanshu` Skills 插件，但**尚未注册公网 MCP 连接**；使用它不会让 ChatGPT 神奇地执行本机 Python 计算。真实远程调用需要 HTTPS 部署和账户授权及客户端连接。

示例：

```bash
# 可选（环境可访问 PyPI 时）
python -m pip install '.[professional]'
python -m app.cli ziwei-pro --date 2000-08-16T04:00 --gender female --target 2024-02-10
python scripts/build_plugin.py  # 在项目外生成 xuanshu-chatgpt-plugin-v.0.1.0.zip
```

**ChatGPT/Claude 远程连接尚需真实 OAuth/HTTPS 环境，当前没有谎称其已通过。** 文档见 `docs/MCP_INTEGRATION.md` 和 `docs/ACCEPTANCE_GAPS.md`。

## 紫微本命盘扩展（部分能力，非全盘认证）

在既有 14 主星、18 颗辅助星不变的基础上，新增 26 颗选定辅助/杂曜、命主与身主、岁前/将前/长生/博士四组传统十二神，以及 1–120 虚岁小限位置索引（有性别参数才排与顺逆相关的序列）。结果可以通过既有紫微 REST/MCP/CLI 和 Web 十二宫查看。

原始 32 颗星及八字参考盘另行保留为不可覆盖的基准，新增部分有固定输出快照、结构约束与多 Python 哈希种子确定性测试。**26 颗新增星曜尚无跨独立专业排盘软件逐星验收；不能据此称为紫微全星系或具预测能力。**

## 5 分钟启动

需要 **Python 3.11+**、可安装 Python 依赖的系统（Windows / macOS / Linux）。

```bash
# 在仓库根目录
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

然后进入：

- Web：`http://127.0.0.1:8000/`
- API/Swagger：`http://127.0.0.1:8000/docs`
- MCP HTTP：`http://127.0.0.1:8000/mcp`
- 健康：`http://127.0.0.1:8000/health`
- 能力清单：`http://127.0.0.1:8000/api/capabilities`

**Docker 首次启动：先运行 `python scripts/init_docker_local.py` 生成仅保存在 `.env` 的随机访问令牌，再运行 `docker compose up --build`。** 宿主端口仅映射 `127.0.0.1:8000`；由于容器网桥连接来源不是回环 IP，Compose 默认采用**强令牌鉴权**而不是破坏本地模式安全策略。打开 Web 后在「API 访问令牌」输入 `.env` 中的 `MCP_BEARER_TOKEN`（页面仅暂存在内存，不会写入档案）。`python scripts/docker_smoke.py` 可在启动后验证接入。Linux/macOS/Windows 不使用 Docker 时，仍可用 `./start.sh` 或 `start.ps1` 在真实本机回环模式免令牌启动。

## 时家奇门结构排盘与外部 OAuth 资源鉴权

本轮是真正新增计算与鉴权源码，不是“完整术数平台”或已上线插件：

- **时家奇门拆补转盘（限定流派）**：24 节气三元局数、阴阳遁、九宫地盘三奇六仪、天盘干、九星八门八神、旬首、值符值使、空亡、固定中宫寄宫。已提供 `POST /api/qimen`、`qimen_hour_chart`、`python -m app.cli qimen` 和浏览器九宫图。**已对照另一开源项目 5 组 2026 盘的 6 项关键字段；尚缺完整逐宫和多流派验证，不包括置闰、飞盘、茅山等体系，也不应当称为奇门全面完成**。规则文档：[`docs/rules/qimen.md`](docs/rules/qimen.md)。
- **MCP OAuth 资源服务器验证**：提供 RFC 9728 发现元数据，支持外部签发的 RSA/ECDSA JWT 校验，包括 issuer / audience / exp / sub / scope、JWKS 轮换缓存、未授权挑战；在**离线模拟**下做了真实签名校验。并未提供独立 OAuth 登录/发码服务器，也未上线 HTTPS，更未完成 ChatGPT/Claude 登录集成。配置与威胁边界见 [`docs/rules/oauth.md`](docs/rules/oauth.md)。

```bash
python -m app.cli qimen --date 2024-06-15T14:30 --tz Asia/Shanghai
curl -s http://127.0.0.1:8000/api/qimen -H 'Content-Type: application/json' -d '{"moment":{"birth_datetime":"2024-06-15T14:30","timezone":"Asia/Shanghai"}}'
```

## 节令精度、大运及出生时间边界地图

本轮继续补齐两条真正可计算、可在 Web / REST / MCP / CLI 使用的工作流：

- **十年干支大运**：基于立春年干阴阳与明确的传统顺逆方向，从本命月柱沿六十甲子顺／逆排 1–12 柱；按相邻十二节令的**实际 UTC 时间差**换算三日一岁名义起运年龄，并明确公历时间轴仅为近似，不等于精准交运日或现实预测。
- **出生时刻边界地图**：以出生时刻为中心检查 ±1–120 分钟，针对当前已实现的命盘规则检测时辰、日期、DST 偏移与交节切换，输出按 UTC 排序的边界及每段代表性八字／部分紫微结果。与旧版每 N 分钟采样相比，更适合发现采样间隙里的模型切换。**一秒定位是计算分辨率，不代表实际出生记录能精确至秒。**
- **节令浮点边界修复**：八字月柱与建除月建统一按已求得的**天文节令时刻**判定，不再直接对太阳黄经做 `floor`，修复交节恰好发生时月柱滞后切换；大运出生时刻恰好等于节令时按零时差处理。新增覆盖 2000、2024、2033 年各十二节的前一微秒、交节当刻与后一微秒一致性回归。
- **综合报告可选扩展**：报告支持 `include_dayun=true`、`dayun_direction_override` 和 `birth_boundary_minutes`；默认不改变旧版报告结构。

示例（必须指定性别或者方向来决定传统大运顺逆）：

```bash
curl -s http://127.0.0.1:8000/api/dayun -H 'Content-Type: application/json' -d '{"birth":{"birth_datetime":"2000-08-16T04:00","gender":"male"},"periods":3}'
curl -s http://127.0.0.1:8000/api/birth-boundaries -H 'Content-Type: application/json' -d '{"birth":{"birth_datetime":"2000-08-16T00:58"},"uncertainty_minutes":8}'
curl -s http://127.0.0.1:8000/api/report -H 'Content-Type: application/json' -d '{"birth":{"birth_datetime":"2000-08-16T04:00","gender":"male"},"include_dayun":true,"birth_boundary_minutes":30}'
```

规则与计算局限：`docs/rules/dayun.md`、`docs/rules/boundary-map.md`、`docs/ADVANCED_AUDIT.md`。

## 工作流：独立历法 / 结构对照 / 决策

三个可在 **Web 工作台、REST API、MCP、Python CLI** 中直接调用的新工作流：

- **建除十二值日**：将交节月支与当日日支对应；跨节令日期有明显提示，不据此判断现实吉凶。
- **年度轨迹**：一张本命盘对照多年的农历年干四化，非流年全盘。
- **方案决策**：现实方案用用户提供的评分和权重比较，不调用命理得出排名。

REST 示例：

```bash
curl -s http://127.0.0.1:8000/api/day-officers -H 'Content-Type: application/json' -d '{"start_date":"2026-10-15","days":14}'
curl -s http://127.0.0.1:8000/api/annual-timeline -H 'Content-Type: application/json' -d '{"birth":{"birth_datetime":"2000-08-16T04:00"},"start_lunar_year":2024,"years":5}'
curl -s http://127.0.0.1:8000/api/decision-matrix -H 'Content-Type: application/json' -d '{"question":"比较方案","criteria":[{"name":"成本","weight":2}],"options":[{"name":"A","ratings":{"成本":3}},{"name":"B","ratings":{"成本":4}}]}'
```

规则和证据：`docs/rules/jianchu.md`、`docs/rules/timeline.md`、`docs/rules/decision.md`。

## 新增 Python CLI

```bash
python -m app.cli bazi --date 2000-08-16T04:00 --tz Asia/Shanghai
python -m app.cli qimen --date 2024-06-15T14:30 --tz Asia/Shanghai
python -m app.cli combined --date 2024-02-10T01:20 --longitude 104.0667 --time-mode apparent_solar
python -m app.cli time-audit --date 2024-02-10T01:20 --longitude 104.0667
python -m app.cli annual --date 2000-08-16T04:00 --year 2026
python -m app.cli terms --year 2026
python -m app.cli lunar --date 2024-02-10
python -m app.cli gregorian --year 2024 --month 1 --day 1
python -m app.cli birth-window --date 2024-02-10T01:20 --radius 30 --step 5
python -m app.cli quality-audit --date 2057-09-28T12:00
python -m app.cli dayun --date 2000-08-16T04:00 --gender male --periods 10
python -m app.cli dayun --date 2000-08-16T04:00 --direction reverse --periods 6
python -m app.cli birth-boundaries --date 2000-08-16T00:58 --radius 8
python -m app.cli report --date 2000-08-16T04:00 --gender male --include-dayun --boundary-radius 15
python -m app.cli officers --date 2026-10-15 --days 14 --filter 建 开
python -m app.cli timeline --date 2000-08-16T04:00 --year 2024 --years 10 --palace 命宫
python -m app.cli decide --input ./example-decision.json  # 文件须符合下方 decision-matrix JSON 结构；也支持 --input - 从 stdin 读取
python -m app.cli deep-review --date 2024-02-07T12:00 --palace 官禄宫 --year 2026
python -m app.cli tools
```

## REST API

| 请求 | 用途 |
|---|---|
| `POST /api/qimen` | 限定流派的时家奇门拆补转盘九宫排布（仍缺跨流派外部逐宫验证） |
| `POST /api/dayun` | 传统起运方向、三日一岁、十年干支和非精确公历投影（1–12 柱） |
| `POST /api/birth-boundaries` | 误差区间 ±1–120 分钟中已实现规则的时间切换及分段代表盘 |
| `POST /api/report` | 可追溯综合报告，可选择加入大运、出生时间边界地图与 `include_deep_evidence` 规则追溯 |
| `POST /api/deep-review` | 八字与原生紫微结构的详细证据引用、已知冲突辨析和内部一致性审计 |
| `POST /api/day-officers` | 传统建除十二值日标签（1–93 日、含节令交接提示） |
| `POST /api/annual-timeline` | 连续农历纪年四化在本命宫位上的静态映射 |
| `POST /api/decision-matrix` | 多方案加权评分与单指标剔除敏感性 |
| `POST /api/bazi` | 八字四柱、藏干和地支关系 |
| `POST /api/ziwei` | 紫微部分本命盘 |
| `POST /api/combined` | 两套同时排盘 |
| `POST /api/analyze` | 非预测性文化规则说明 |
| `POST /api/calendar` | 中国历法日历（1–31 天） |
| `POST /api/pair` | 两人四柱结构对照 |
| `POST /api/rule-matrix` | 同一出生资料在各种常见规则下逐字段对照 |
| `POST /api/group-relations` | 2 到 8 人的十神、天干五合、地支关系与三合对照 |
| `POST /api/daily-almanac` | 某一时刻的四柱、农历、节气进度、建除值日与月相，可附本命对照 |
| `POST /api/pillars-to-dates` | 四柱反查 1901–2099 年间的出生时段 |
| `POST /api/chart-import-check` | 外部命盘逐项核对并找出对方所用规则 |
| `POST /api/palace` | 特定紫微宫位详情 |
| `POST /api/lunar-to-gregorian` | 农历年/月/日及闰月标识反查公历 |
| `POST /api/birth-window` | 对出生时间前后误差区间采样，列出观测到的不同命盘 |
| `POST /api/quality-audit` | 排盘输入质量、节令/时辰边界、太阳时跨日和远期农历不确定性提示 |
| `POST /api/annual` | 目标农历年的四化星与本命宫位映射 |
| `POST /api/time-audit` | 三种时制计算对照（必填经度） |
| `POST /api/rules-compare` | 两套出生参数的规则差异 |
| `GET /api/solar-terms/{year}` | 24 节气 |
| `GET /api/solar-terms/{year}.ics` | 节气 ICS 日历导出；加 `?moon=true` 同时导出四种主要月相 |
| `GET /api/lunar/{YYYY-MM-DD}` | 单日公历转农历 |
| `GET /api/capabilities` | 真实能力和限制 |

`BirthInput` 基础输入：

```json
{
  "birth_datetime": "2024-02-10T01:20",
  "timezone": "Asia/Shanghai",
  "gender": "female",
  "late_zi_day_rollover": false,
  "leap_month_second_half_as_next": true,
  "time_mode": "apparent_solar",
  "longitude": 104.0667,
  "latitude": null
}
```

`time_mode` 支持 `clock`（默认，**不需要**经度）、`mean_solar`、`apparent_solar`。后两者必须提供 `longitude`（东正西负，±180°），不自动定位或上传地理位置。注意夏令时重复时间：请传入带 UTC offset 的 ISO 时间（如 `2024-10-27T02:30+02:00`）。纬度仅保存输入字段元数据，**不参与计算**。

示例：

```bash
curl -s http://127.0.0.1:8000/api/combined \
 -H 'Content-Type: application/json' \
 -d '{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai","gender":"female"}'
```

## ChatGPT / Claude / Codex 与 Skills

- MCP 服务器 **33 个 Tools、17 个 Markdown Resources、15 个 Prompts**，位于 `app/mcp.py`；**18 个 Agent Skills** 在 `skills/`。
- `python -m app.stdio` 可作为 Claude Desktop / Codex 的 MCP 子进程。
- 公网宿主需要**公网 HTTPS URL + 合适鉴权方式 + 用户自行授权连接**。此工程还没有公共服务地址或安装到 ChatGPT / Claude 账户。
- MCP 支持新版 **`2026-07-28` 无握手元数据机制**和旧版 `2025-03-26`、`2025-06-18`、`2025-11-25` 握手机制（stdio / 无状态 HTTP JSON）。新版校验请求元数据中的版本和 `clientCapabilities` 对象、`MCP-Protocol-Version`、`Mcp-Method` 和必要的 `Mcp-Name` 头；列表与规则读取回复带缓存提示；支持外部 OAuth JWT 资源服务器（需提供商与 HTTPS），不提供内建授权码登录服务、主动 SSE 订阅或需要多轮模型交互的扩展。
- 对接说明、Claude Desktop 和 Codex 配置示例：[`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md)。

## 数据和安全

**默认服务器不保存出生信息，不依赖数据库。** 浏览器可主动保存到该设备的 `localStorage`（明文），删除时从本浏览器移除。加密备份时，WebCrypto 在**浏览器本地**使用 PBKDF2-SHA256（250000 次）和 AES-256-GCM；口令不会发送服务端。备份口令丢失则不能解密。明文 JSON 导出仍须妥善保管。请注意公共电脑、恶意浏览器扩展程序、代理日志、XSS、操作系统备份等隐私风险。

本地模式现对 HTTP Host 做白名单检查（只允许回环/显式受信任主机），并校验 REST 与 MCP 的浏览器 Origin，以降低 DNS 重绑定风险；自定义本地主机名须显式添加到 `ASTRO_ALLOWED_HOSTS`。

REST/MCP 可配置静态 Bearer（`MCP_BEARER_TOKEN`）；本机浏览器 Origin 必须匹配**当前 Host 和端口**，容器鉴权模式在 Compose 配置显式允许的来源内运行；MCP 严格 Origin 白名单（`MCP_ALLOWED_ORIGINS`），响应具有基本 CSP、no-store 和禁嵌入头，64KiB **实际请求流上限**（包括 chunked 请求）。**不等于完成商用安全审计**；发布到公网前必须参考 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)，配置反向代理、请求大小上限、TLS、Host 校验、限流、鉴权和告警。`DEPLOYMENT_MODE=public` 必须配置至少 32 字符的 `MCP_BEARER_TOKEN` **或完整外部 OAuth 环境变量**，以及显式 `ASTRO_ALLOWED_HOSTS`，否则拒绝服务；启用 Token 时所有 `/api/*` 接口也要求鉴权。此校验不代替反向代理限流。**公网 Bearer 模式的静态 Web 工作台没有安全的用户登录入口；不能把服务器主令牌直接写进浏览器源码或 localStorage，需另建 OAuth/会话机制。**

## 校验与实现边界

- 对照基准 `2000-08-16 04:00 Asia/Shanghai`（iztro 官方公开示例）：八字 `庚辰 / 甲申 / 丙午 / 庚寅`，命宫午、身宫戌、木三局。
- 另将香港天文台 **2024、2033 年共 26 个独立农历月首**加入固定回归，并显式标出 **2057、2089、2097** 年公开的新月日界风险。质量检查默认敏感窗口 **15 分钟**。详见 [`docs/ADVANCED_AUDIT.md`、`docs/DEEP_AUDIT.md`](docs/DEEP_AUDIT.md)；
- 采用 Swiss Ephemeris Moshier 模式计算节气、月相和均时差；**不能将现有测试结果等同于全 1901–2099 专业历法认证或全流派紫微验证**。
- 八字立春 / 月令规则、紫微四化流派、经度校正及禁预测原则详见 `docs/rules/`。
- 当前没有完成：**奇门全流派/外部逐宫验收、紫微全星系与全运限、私有知识库、云端多用户账户、OAuth 授权服务器/实际远程登录、永久公网上线及跨客户端正式 Plugin 安装**。必须在有可靠规则来源和外部参考数据时再纳入已完成范围。

## 独立联调与可复现检查

```bash
python -m pytest -q
python scripts/http_smoke.py            # 真实 Uvicorn HTTP + REST + MCP 回归
node --check static/app.js && node --check static/vault.js
node tests/vault_smoke.cjs               # WebCrypto 加密/解密/篡改防护
python scripts/init_docker_local.py       # 可选：Docker 首次创建随机令牌
# docker compose up -d --build && python scripts/docker_smoke.py  # 可选：需 Docker CLI
python scripts/browser_smoke.py         # 可选：本机需安装 Playwright + /usr/bin/chromium
python scripts/build_release.py         # 将完整源码打包到上级目录
```

`browser_smoke.py` 在真正的 Chromium 中执行 UI 交互，通过 Python 桥接调用实际 FastAPI TestClient；**不是公网网络 E2E**。实际测试数与环境详情详见 `TEST_REPORT.md`。发现与未完成项的严重级别见 [`docs/ADVANCED_AUDIT.md`、`docs/DEEP_AUDIT.md`](docs/DEEP_AUDIT.md)。

## 工程文件

`app/` 计算、输入校验与接口（`advanced.py` 含大运与边界图）；`static/` 本地 Web；`skills/` 18 个 Skill；`docs/rules/` 可访问规则资源；`tests/` 测试；`.github/workflows/ci.yml` CI；`Dockerfile`/`compose.yaml` 容器文件；`scripts/build_release.py` 可复现 ZIP 打包与 SHA-256 校验（执行 `make release`）。正式能力状态以 `GET /api/capabilities` 和 `TEST_REPORT.md` 为准。

**许可**：项目 AGPL-3.0-only。Swiss Ephemeris / pyswisseph 为 AGPL / 商业双许可，**闭源或商业部署前必须自行核对授权义务**。详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 安装包完整性与跨时区农历边界（当前开发阶段）

除源码 ZIP 与 Docker 外，支持生成标准 Python wheel。**不同于过去只能在源码目录运行的安装方式**，构建时将 `static/`、`docs/rules/`、`skills/` 复制进 Python 安装包，安装后 Web 页面、MCP 资源及 Agent Skills 不依赖当前工作目录：

```bash
python -m pip wheel . --no-build-isolation --no-deps -w dist
python -m pip install dist/xuanshu-0.1.0-py3-none-any.whl
xuanshu tools
uvicorn app.main:app --host 127.0.0.1 --port 8000
python scripts/wheel_smoke.py   # 在源码仓库中执行：临时独立安装并验证 wheel
```

分发包名与可执行命令为 `xuanshu`；内部兼容的 Python 模块路径暂为 `app.*`，保持原有 stdio / CLI 配置不失效。wheel 的 PEP 440 版本字符串必须为 `0.1.0`，项目未发布标签始终为 **`v.0.1.0`**。

为避免不同出生地时区的农历日界歧义，质量审计现同时输出**出生地有效日期**与**相同绝对瞬间的北京时间日期及农历**。例如 2024-02-09 20:00（Europe/Rome）对应北京时间 2024-02-10 03:00；前者按所在地公历日查询为农历十二月三十，后者按北京日界查询为正月初一。两种习惯口径可产生不同命盘；**工具只显示差异并提示复核，不偷偷修改用户选择的流派规则**。

REST/MCP 的 JSON 输入新增统一校验：拒绝 `NaN` / `Infinity`、浮点溢出、重复对象键、非法 UTF-16 代理项和过深嵌套，防止畸形请求触发 HTTP 500。请求体上限保持 64 KiB，不会上传、保存出生数据到服务器文件。
