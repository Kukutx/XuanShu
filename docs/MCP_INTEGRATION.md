# ChatGPT / Claude / Codex MCP 接入 · 双版本支持

## 协议能力

同一 MCP 核心同时支持：

- **新版 `2026-07-28`**：无 `initialize` 握手、每个请求的 `params._meta` 必须包含协议版本和客户端能力对象 `io.modelcontextprotocol/clientCapabilities`。支持 `server/discover`，结果带 `resultType: complete` 和 `serverInfo`；`tools/list`、`prompts/list`、`resources/list`、`resources/read` 的新版回复带 `ttlMs`、`cacheScope`。HTTP 请求必须提供 `MCP-Protocol-Version`、`Mcp-Method`、必要时的 `Mcp-Name`，并与 JSON 正文一致。
- **旧版 `2025-11-25`、`2025-06-18`、`2025-03-26`**：支持 `initialize` 握手，并保留旧版工具/资源/提示结构。
- **传输**：`python -m app.stdio` 标准输入输出；`POST /mcp` Streamable HTTP，单对象 JSON；`GET/DELETE /mcp` 返回 405；不支持主动 SSE、会话订阅、内建 OAuth 发码/登录与多轮输入请求。

本实现只实现自身声明的上述子集。测试使用自编排的协议回归请求，**未声称通过官方 MCP 合规认证或完成全部 ChatGPT/Claude 远程插件安装**。

## 在 Web 工作台里自检与生成配置

打开工作台的「Agent 集成」页：页面用 2026-07-28 的 `server/discover` 和 2025-11-25 的 `initialize` 实际连接本服务，再读取 `tools/list`、`prompts/list`、`resources/list`、`skills/list`，逐步写出结果和耗时；选择客户端（Claude Desktop、Claude Code、Codex、HTTP 直连）和系统并填入项目文件夹，即可复制对应的配置或命令。工具目录里每个工具都有可复制的 `tools/call` 示例和「试运行」，示例使用固定的演示出生资料。页面填写的项目文件夹不保存、不上传；配置文本里的令牌只写成环境变量占位。

## 使用 Claude Desktop 连接本地 stdio

在配置文件中把示例绝对路径替换为下载项目的实际路径：

```json
{
  "mcpServers": {
    "xuanshu": {
      "command": "/ABSOLUTE/PATH/.venv/bin/python",
      "args": ["-m", "app.stdio"],
      "env": {"PYTHONPATH": "/ABSOLUTE/PATH/PROJECT"}
    }
  }
}
```

Windows 将 `command` 指向 `.venv\\Scripts\\python.exe`。Claude 客户端版本不同可能使用不同的配置入口。

## Codex 本地 stdio 示例

```toml
[mcp_servers.xuanshu]
command = "/ABSOLUTE/PATH/.venv/bin/python"
args = ["-m", "app.stdio"]
[mcp_servers.xuanshu.env]
PYTHONPATH = "/ABSOLUTE/PATH/PROJECT"
```

## 调用新版无握手 `server/discover`

```bash
curl http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: server/discover' \
  -d '{"jsonrpc":"2.0","id":"discover-1","method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"curl","version":"1"},"io.modelcontextprotocol/clientCapabilities":{}}}}'
```

## 新版工具调用：农历反查

```bash
curl http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: lunar_to_gregorian' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"lunar_to_gregorian","arguments":{"lunar_year":2024,"lunar_month":1,"lunar_day":1},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}'
```

## 旧版握手回归

```bash
curl http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'
```

## 远程接入前置条件

需要受控 HTTPS 域名、有效的服务端鉴权、严格 Host/Origin 策略、限流、日志隐私策略及客户端所要求的授权方式。此项目支持**固定 Bearer Token**或配置外部发行者的 OAuth JWT **资源服务器**；不包含 OAuth 授权服务器、用户登录、正式 ChatGPT/Claude 连接验收。用户必须在客户端主动连接，项目不会自动安装进任何账号。公网模式参考 [`DEPLOYMENT.md`](DEPLOYMENT.md)。

技术依据：MCP 2026-07-28 官方传输和协议版本规范：
- https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http

## 外部 OAuth 发现与时家奇门工具

- 奇门工具名称 `qimen_hour_chart`，入参 `{"moment":{"birth_datetime":"2024-06-15T14:30","timezone":"Asia/Shanghai"}}`，其他流派不在实现范围。
- 具备外部授权提供商时，可以开启基于 JWT 的资源服务器验证，RFC 9728 元数据端点为 `/.well-known/oauth-protected-resource/mcp`。这并不启动 OAuth 授权码流程或完成 App 注册；配置细节见 `rules/oauth.md`。


## 可审计的 MCP Skills 扩展（未公开发布）

支持 ChatGPT 对 MCP SEP-2640 的有界静态 Skills 导入：`initialize` 和 `server/discover` 声明 `capabilities.extensions.io.modelcontextprotocol/skills`，提供 `skills/list`（分页两个条目）、`skills/get` 与 `resources/read` 原文，并由返回的 UTF-8 内容生成 SHA-256 摘要。由于 ChatGPT 单次 Scan Tools 最多接收五个 Skills，线上导入目录固定为五个高优先级工作流；项目完整 Skills 共十八个。

`python scripts/build_plugin.py` 导出包含十八个 `skills/` 的可移植私有 Plugin 归档，**不创建虚构的远程 MCP URL**。私有插件已在 ChatGPT 创建，但它目前只有 Skills、不能直接执行联网命理计算；要启用计算工具，仍需授权公网 HTTPS MCP 服务并在 ChatGPT/Claude 中实际连接。


## 新增带证据引用的深度分析工具（开发阶段）

`deep_evidence_review` MCP 工具接受 `birth`（与 `BirthInput` 相同）、`focus_palace`（十二宫）、可选 `lunar_year` 和 `include_quality`。对应 REST 为 `POST /api/deep-review`，CLI 为 `xuanshu deep-review`；新增 `astro://rules/evidence` 规则资源及 `deep-evidence-review` Prompt。

Agent **必须**逐条保留 `findings[].evidence` 的字段路径及 SHA-256、`rule_ids`、`limit`，并引用返回的 `references` 的适用范围；**禁止**把方法 URL 当成该用户盘的独立验算或预测准确率。项目当前共 25 Tools / 17 Resources / 15 Prompts / 18 Skills（固定版本 `v.0.1.0`）。


## 可执行咨询 Agent 的 MCP 入口（固定 `v.0.1.0`）

通过 `tools/call` 使用 `consultation_execute`，参数例如 `{"question":"2027年工作方向","birth":{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai"}}`。返回真实执行的 `tool_trace`、证据结构 `observations`（含来源路径与校验摘要）、`verification` 和缺失信息。下轮可提交 `continuation` 和本轮必要出生参数。规则资源 `astro://rules/consultation`。

**限制：** 无 LLM 自主推理、无服务端记忆、无公网 HTTPS/OAuth 客户端授权；私人 Skills 包不是已连通远程计算的插件。
