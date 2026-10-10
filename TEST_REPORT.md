# XuanShu v.0.1.0 · 实际测试及正式验收边界

测试日：2026-10-10。**这是持续开发的固定版本，不是正式发布。**

## Windows 本机最新验收（2026-10-10，版本保持 v.0.1.0）

- 代码实际目录：`A:\Project\ProjectWaiting\xuanshu`；在 Windows Python 3.13 隔离环境执行。
- `pytest`：**711 passed、1 skipped**。跳过项仅为未安装 iztro 时的条件测试；本机已安装 iztro，专业紫微真实工具入口和 25 项 REST/MCP 对照全部通过。
- **25/25 MCP Tools**：与对应 REST 计算结果一致，零失败；此为接口验收，不代表多流派的外部专业认证。
- Uvicorn 独立进程：**39 次本机 TCP HTTP 请求**通过，包含 REST、MCP 和静态资源。
- Chromium 154：既有页面桥接回归 **25 次 FastAPI 调用**通过；新增无桥接、浏览器直接访问本机 TCP 的 E2E **7 次 HTTP API 调用**通过，桌面与移动端均无 JS/网络异常。
- Node WebCrypto AES-256-GCM：加密、解密、错误口令、篡改检测及旧版备份导入均通过。
- **Docker 容器未完成实际启动验收**：本机有 Docker CLI，但 Linux Engine 在检查时尚未启动。公网 HTTPS/OAuth、真实 ChatGPT/Claude 远程 MCP、所有流派的独立排盘认证同样不在上述通过范围。
- 这些结果只说明目前受测路径通过，不应理解为所有功能和生产环境全部完成。

## 本次全功能接口与 Windows 接受测试补强（2026-10-10，版本未变）

- 新增 `scripts/full_functional_audit.py`：将全部 **25 个 MCP 工具**纳入强制清单，比较各工具经 2026 MCP HTTP `tools/call` 与 REST 的结构化结果。当前隔离云端 **24 个成功结果一致、0 不一致**，专业紫微作为可选依赖缺失而正确返回错误；此前仅计算端的内部测试不能说明全部 RPC 与 REST 一致。
- Windows DevMate 实际检测：`A:\Project\ProjectWaiting` 存在；Python 3.13、uv、Git、Node 和 Docker CLI 均在 PATH；**Docker Engine 未运行**。在用户的隔离 `uv run --with iztro-py` 中，独立验证 `iztro-py 0.5.0` 可下载安装，`astro.by_solar` 与 `horoscope` 方法均可调用。后者是提供方 API 冒烟测试，**还不是本项目完整适配器和逐星结果的验收**。
- 新增 `scripts/windows_acceptance.ps1`，用于工程转入 Windows 后执行项目隔离安装、pytest、25 工具审计、本机 TCP、CLI、Chrome DOM、Node AES-GCM；未能在源码尚未传至 Windows 之前声称在该目录通过。
- 现有云端基线 `python -m pytest -q`、`scripts/http_smoke.py` 与 `scripts/browser_smoke.py` 均通过；HTTP 烟雾 **47 请求**、Chromium 桥接 **25 调用**。`full_functional_audit.py` 为独立补充，不构成远程 OAuth / Docker / 学术流派认证。

## 本次实际咨询运行时交付（2026-10-10，同一固定版本）

- **新增运行时，不再只有指导 Prompt**：`app/consultation.py` 的 `execute_consultation` 可解析本命、年度职业、双人关系、候选时间、评分方案、规则争议六类问题并选择真实计算链，缺少资料按 `needs_input/partial` 返回；`status=completed` 只表示所需计算步骤已执行，非现实咨询或预测已被科学证实。
- **多轮、隐私与证据**：用户端游标仅携带意图、宫位、年度和轮数，服务器不会保存出生记录或聊天消息；二人盘需明确使用权限。现实经历标记为用户提供、未经核实。证据保留路径、规则 ID、方法参考和 SHA-256；内部一致性检查与外部认证完全分开。
- **已接入**：REST `POST /api/consultation`、MCP `consultation_execute`（兼容旧握手和 2026 协议）、CLI `xuanshu consult --input ...`、Web 第一个问题驱动工作台，及 `astro://rules/consultation` 规则资源。现有 **25 Tools / 17 Resources / 15 Prompts / 18 Skills，Web 22 个视图**；版本仍为 `v.0.1.0`。
- **实际验收结果**：`python -m pytest -q -o addopts=''` **710/710 项通过**；本机 Uvicorn **47 次 HTTP 请求**，Chromium **25 次真实 DOM 到 FastAPI 桥接调用**、0 JS 页面异常，Node WebCrypto AES-GCM 测试通过，wheel 独立安装中 Web/REST/MCP HTTP+stdio/CLI 均通过。以上不等于公网浏览器网络端到端测试。
- **外部验收尚未通过**：真实公网 HTTPS/OAuth、Claude 与 ChatGPT 远程 MCP 注册及调用、可选专业紫微库真实运行、全奇门流派、生产账号记忆/租户隔离和 Docker 启动。这些仍是独立验收项。

详细接口与实测场景：`docs/research/CONSULTATION_EXECUTION_ACCEPTANCE.md`。

## 本次业务目标重新对齐及回归（2026-10-10 · 版本仍为 v.0.1.0）

- **重新确认目标**：玄枢最终应是由 ChatGPT/Claude 执行的**问题驱动的东方术数文化咨询 Agent 工具链**，而不是以工具数和页面数衡量的排盘网站；本次交付是公开资料与真实代码形成的产品业务审计，不虚报为自主 Agent Runtime 完成。
- **新交付**：`docs/research/PRODUCT_BUSINESS_AUDIT.md`（完整产品差距、代码定位、隐私/安全与优先级），`docs/research/CONSULTATION_WORKFLOW_SPEC.md`（六类咨询业务场景、输入、具体工具链与验收）。
- **真实修改**：原有 `structured-dossier` Skill 增强为问题驱动总控与证据报告指令；MCP 原 `prepare-report` Prompt 按关注问题规划工具、处理流派差异，保持 **24 Tools / 16 Resources / 15 Prompts / 18 Skills** 不变。新增 3 项工作流契约回归，不等于实际六场景已在 ChatGPT/Claude 中实现。
- **Python 自动化**：`python -m pytest -q -o addopts=''` **697 项通过**（含新增 3 项）。
- **真实 HTTP**：本机 Uvicorn 实际 TCP **43 次请求**通过，新增验证 `prompts/get` 通过 MCP 2026 协议读取问题驱动的 `prepare-report`。
- **Chrome**：Chromium 144 桌面/移动交互、22 次真实 FastAPI TestClient 请求桥接通过，无 JS 异常；该项**不等于**浏览器直接联网 E2E。
- **隔离安装**：本机独立 wheel 安装、Web / MCP HTTP+stdio / CLI、规则资源和本轮两份研究文档均可读取；AES-GCM/WebCrypto 旧备份兼容测试通过。
- **关键未完成**：无真正的 LLM Coordinator、生产长期记忆、已验证的全部流派、真实在线 ChatGPT/Claude MCP 授权、Docker 运行成功证据。本机升级的 Skills ZIP 尚未重新发布到此前注册的私有 ChatGPT Plugin：Plugin Creator 对同版本更新会自动增加补丁版本，违反本项目的版本冻结要求，因此未调用注册更新。


## 本轮证据追溯深度研究与真实回归（2026-10-10）

| 验收目标 | 当前结果 | 未经验证的边界 |
|---|---|---|
| 697 项自动化回归 | `python -m pytest -q` **697 项通过、0 失败**，包含新增 42 项证据/宫位/年度/模型及打包校验 | 单元测试与内部不变量不证明流派完全正确 |
| 深度证据结构 | 四柱、藏干/十神、地支结构、焦点宫位、三方四正、生年/宫干四化、年界冲突、可选年份与质量审计；提供 10 条方法参考、SHA-256 与 JSON 字段路径 | 参考网址为方法说明，不等于完整命盘已由第三方独立认证 |
| 实际 TCP HTTP + MCP 2026 | 43 个本机 HTTP 请求，新的 `/api/deep-review`、`/api/report` 深度选项、`tools/call` 与 `astro://rules/evidence` 真实通过 | loopback Uvicorn 不是公开 HTTPS/OAuth 客户端验收 |
| Chromium 控件 | 22 次页面→FastAPI 桥接调用；新页切换宫位/年份、参考链接、非法年份；桌面及移动视图与报告深度选项通过，0 JS 异常 | 该环境阻止浏览器直连 localhost；不是浏览器网络 E2E |
| Wheel 独立安装 | 临时独立安装后，新端点、新资源、CLI、深度调研文档及完整输入示例和 MCP HTTP+stdio 均通过 | 只验证基础生产依赖，专业紫微可选依赖尚未真实验盘 |
| 对照演示 | 2024-02-07（立春后/春节前）八字甲辰 vs 原生紫微癸卯；参考来源按规则类型明确区分 | 这属于口径差异而非“命运”或独立验证 |

研究文档：`docs/research/FEATURES_AND_REFERENCES.md`；规则接口：`docs/rules/evidence.md`；示例：`examples/DEEP_ANALYSIS_WALKTHROUGH.md`。版本固定 **`v.0.1.0`**，并未正式上线。

## 本次实测

| 项目 | 实测证据 | 限制 |
|---|---|---|
| Python pytest | **697 / 697** 通过、零失败（`python -m pytest -q`） | 本地规则测试不是所有流派的学术认证 |
| 真实 Uvicorn HTTP | **43 次**真实 TCP 请求，覆盖新专业提供方失败处理、奇门参考盘 REST、旧 REST、MCP 2026、Skills 分页 / 获取、请求安全 | 仅 loopback HTTP，非公网 HTTPS |
| Chromium | Chromium 144 桌面及移动页面操作、**22 次**通过 TestClient 桥接的 FastAPI 请求，新增专业提供方缺失提示、奇门参考盘输入；无 JS 页面异常 | 使用页面→TestClient 桥接；不代表真实公网端到端浏览器测试 |
| Python wheel 隔离安装 | 临时目录构建并在另一个工作目录安装，Web、REST、MCP HTTP+stdio、24 CLI 工具、18 Skills 实际工作 | 可选 `iztro-py` 没有安装，不能据此证明它运行成功 |
| ChatGPT Plugin 私有注册 | 通过用户已连接的 Plugin Creator **创建私人 XuanShu 0.1.0 插件**，包含 18 个 Skills | 这不是已连接 MCP 的在线计算插件，也不是公共上架 |
| MCP Skill 扩展 | 5 个高优先级 Skills（分页 2+2+1），每个原文 `SKILL.md` 的 SHA-256 与目录条目逐字节对照一致；路径穿越、非法 cursor 拒绝 | SEP-2640 draft 的 OpenAI 导入子集，未通过公网 Scan Tools 客户端验证 |
| 奇门独立黄金盘 | 5 张公开 MIT 样本每张 6 个顶层字段和九宫各 1 个暗干，共 **75 个有出处的字段**与计算一致；新增逐字段比较工具验证并允许输出准确差异 | 不能代表其他九宫星/门/神字段、多个独立来源或不同流派正确 |
| 专业紫微可选适配 | 用模拟 `iztro-py` 提供方实测参数与结果透传，以及 REST/MCP/CLI/UI 缺依赖错误；没有无声回退到局部计算 | 当前环境无法从 PyPI 下载并真实运行 `iztro-py`；没有真实多流派逐星/动态盘认证 |
| Docker | 检查到 Windows 端存在 Docker 29.8.1 CLI，但引擎未启动（Docker Desktop Linux Engine 管道不可访问）；项目仍有容器 CI 和自检脚本 | **本次没有 Docker build/run 成功日志** |
| 外部 OAuth | 现有模拟 JWKS/JWT 验签、权限检查及资源发现测试继续通过 | **没有真实 IdP、HTTPS 域名、浏览器 PKCE 登录和 ChatGPT/Claude 客户端授权证据** |
| WebCrypto 本地备份 | Node WebCrypto 旧有 AES-256-GCM 往返、篡改和错误口令测试通过 | opt-in 的浏览器本地档案是明文 |

## 可复现命令

```bash
python -m pytest -q
python scripts/http_smoke.py
python scripts/browser_smoke.py
python scripts/wheel_smoke.py
python scripts/build_plugin.py
python -m app.cli deep-review --date 2024-02-07T12:00 --palace 官禄宫 --year 2026
python scripts/build_release.py
python scripts/build_release.py --verify ../xuanshu-v.0.1.0.zip
```

源代码目录固定 `xuanshu/`；包名和界面均保持 **`v.0.1.0`**。ChatGPT 私有 Skills 包为 `xuanshu-chatgpt-plugin-v.0.1.0.zip`；源码完整包为 `xuanshu-v.0.1.0.zip`。

## 尚未完成，禁止声称全部解决

1. **真实 iztro-py 安装和逐宫动态盘实测：** 可选第三方库的外网安装在本隔离环境受限；必须有实际运行输出及多套参考盘，不只是模拟对象。
2. **完整奇门所有流派认证：** 拆补转盘已实现且有部分外部基准；缺置闰、飞盘及其他流派与多异源**完整九宫**黄金盘。
3. **OAuth 真实登录与公网插件联调：** 已注册私有 Skills 插件但没有公网 MCP / HTTPS / 合法 OAuth IdP 配置。缺真实授权码/PKCE、Token 撤销、账号隔离及 ChatGPT/Claude 计算调用证据。
4. **Docker 真实启动与生产运维：** 本机 Docker daemon 不可用，隔离容器无 Docker；尚缺 Kubernetes/反向代理 WAF/限流网关、长期监控、真实安全审计及多用户账户系统。
5. **历法全部年份、多流派完全权威认证：** 本项目仅做现有证据覆盖范围内的独立计算，不访问、提取天府 AI 私有接口或源代码。

这些前置条件不能通过再增加几百条内部测试来替代。详见 `docs/ACCEPTANCE_GAPS.md`。
