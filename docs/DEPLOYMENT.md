# 部署与安全清单

## 默认部署：本地优先

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

直接运行 Uvicorn 的本机模式无需 Token，但**仅接受真正来自回环接口的连接**。Docker 端口转发进容器后，应用通常看到 `172.x` 或 `192.168.x` 的网桥来源，因此原来的匿名本地 Compose 会返回 **403**，即使宿主端口只绑定 `127.0.0.1`。**不要把所有 RFC1918 地址作为匿名回环白名单**：错误的端口发布可能导致远程无鉴权访问。

Docker 使用经测试可执行的安全配置：

```bash
python scripts/init_docker_local.py  # 只在首次执行，独占创建 .env 和随机令牌
# 如果已有 .env，脚本会拒绝覆盖；手动检查原 Token 是否足够随机且至少32字符。
docker compose up --build -d
python scripts/docker_smoke.py       # 需要已经启动的 Docker 引擎
```

Compose 只对宿主 `127.0.0.1:8000` 发布，强制 `DEPLOYMENT_MODE=public` + 32 字符以上密钥 + 严格 Host/Origin 校验，从而允许**经鉴权**的容器网桥连接。Web 页面有不持久化的 API 令牌输入框，可以手动输入 `.env` 中的密钥。它不是多用户登录，也不能替代公网 HTTPS/OAuth。不要将 `.env` 提交到版本库。默认浏览器来源必须是当前 Host 与端口（不再错误放行任意 localhost 端口）。

## 私有公网 HTTPS：必要环境变量

1. **经过授权的服务器或云容器**，TLS 终结于可信反向代理；仅允许公网 443 入站，应用内部端口不直通公网。
2. 环境变量 `DEPLOYMENT_MODE=public`。
3. **静态令牌模式**：`MCP_BEARER_TOKEN` 使用**至少 32 个随机字符**；**或者**配置下文的外部 OAuth 资源服务器模式。不得在 URL、源码、日志或截图中暴露；定期轮换。启用后所有 `/api/*` 和 `/mcp` 路径都要求 `Authorization: Bearer <token>`。
4. `ASTRO_ALLOWED_HOSTS=astro.example.com`：列出反向代理转发的 Host 主机名（不含端口），不得使用通配 `*`；代理须保留并验证 Host。
5. `MCP_ALLOWED_ORIGINS=https://your-trusted-client.example`：有浏览器 Origin 请求时允许的精确来源列表。原生 MCP 客户端可能不发送 Origin；仍要验 Token。公网模式不隐含放行 localhost Origin。
6. 反向代理需要配置请求大小限制（不超过 64 KiB 或相同量级）、**IP/用户速率限制**、连接超时、并发保护、TLS、防火墙、可观察性与告警。应用内 64 KiB 实际请求流限制、Host/Origin 校验与静态令牌**不构成商用级网关防护**。
7. 遵循 AGPL-3.0、Swiss Ephemeris 的 AGPL/商业许可条款。闭源或商业场景先核对授权。

**重要：静态 Web 页面并没有输入服务器级 Bearer Token 的安全登录流程。** 启用公网 Token 时，浏览器页面通常无法直接使用受保护的 REST。不要把 Token 写入 HTML/JS 或浏览器 localStorage；需要用正式 OAuth 或独立会话授权前端。

本工程可验证外部 OAuth JWT，但**不提供 OAuth 授权服务器、登录界面、云端用户账户、租户权限、数据库记录同步或官方插件发布**。参考 `docs/rules/oauth.md`。这些必须单独实现并经过授权操作。

## 隐私事项

- 服务端按请求即时计算，不主动持久化出生信息。反向代理访问日志与诊断日志仍可能暴露 IP、时间、请求路径；**严禁记录 POST 明文出生数据**。
- 用户只有主动点「保存」才写入浏览器 localStorage（明文）；导出备份采用 WebCrypto AES-256-GCM 和 PBKDF2，口令不会上传服务端。
- 公共设备上的浏览器扩展、操作系统备份、恶意脚本与 XSS 仍可能威胁本地档案；备份密码丢失无法恢复。
- 医疗、投资、法律、关系、职业等重要决定不能基于未经验证的术数预测。

## 外部 OAuth 资源服务器配置（不含 OAuth 授权服务器）

如果已有合法可用的独立 OAuth/OIDC 提供商，需为其配置 `astro:read` scope、正确的 `aud=https://astro.example.com/mcp`、RS256/ES256 JWT、HTTPS JWKS，并设置：

```sh
DEPLOYMENT_MODE=public
ASTRO_ALLOWED_HOSTS=astro.example.com
ASTRO_PUBLIC_BASE_URL=https://astro.example.com
ASTRO_OAUTH_ISSUER=https://id.example.com
ASTRO_OAUTH_JWKS_URL=https://id.example.com/.well-known/jwks.json
ASTRO_OAUTH_AUDIENCE=https://astro.example.com/mcp
```

资源元数据端点 `/.well-known/oauth-protected-resource/mcp` 必须在公网上可访问。**只有开发环境中的离线签名/JWKS 模拟测试通过；没有部署、真实登录、跨供应商 OAuth 端到端验证。** 配置过程中不要使用示例域名或在仓库保存真实密钥。
