# MCP OAuth 资源服务器：外部授权提供商

当前实现只负责 **JWT 资源服务器的验证与 RFC 9728 发现**：不提供 OAuth 授权服务器、用户密码注册、令牌颁发、客户端动态注册、云端账户数据库或管理控制台。

部署环境必须设置 `DEPLOYMENT_MODE=public`、`ASTRO_ALLOWED_HOSTS`，并同时配置：

- `ASTRO_PUBLIC_BASE_URL=https://astro.example.com`
- `ASTRO_OAUTH_ISSUER=https://id.example.com`
- `ASTRO_OAUTH_JWKS_URL=https://id.example.com/.well-known/jwks.json`，必须与 issuer 同 HTTPS 主机
- `ASTRO_OAUTH_AUDIENCE=https://astro.example.com/mcp`（必须等于公网基址加 `/mcp`）

OAuth 开启后，未授权请求返回带 `resource_metadata` 和 `scope="astro:read"` 的 `WWW-Authenticate`；公开 `/.well-known/oauth-protected-resource` 和 `/.well-known/oauth-protected-resource/mcp` 发现文档包含 `authorization_servers`。JWT 必须是受信任 `RS256/ES256`、含 `kid`、签名有效，精确的 `iss`、`aud`、到期时间、非空 `sub` 和 `astro:read` scope。JWKS 通过提供商的 HTTPS 地址拉取并缓存，失败时拒绝访问。

**限制**：不实现授权码 + PKCE 客户端、动态客户端注册、OAuth refresh、租户资源隔离或私有云账户。正式连接 ChatGPT、Claude 前需要一套已发布的可信 OAuth 发行者、实际公网 HTTPS、外部登录、回调和互通测试。固定 Bearer 令牌可在**未启用 OAuth 时**作为独立开发机制；一旦提供外部 OAuth 配置，静态令牌被禁用，不能绕过受众和 Scope 检查。它不是多用户 OAuth 方案。
