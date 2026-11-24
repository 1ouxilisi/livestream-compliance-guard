# deploy/ —— 部署与上线（P1）

## 两条路线，按语言选
| 路线 | 平台 | 适合 | 说明 |
|---|---|---|---|
| **Python（最省事，推荐先跑通）** | Railway / Render / Fly.io，或腾讯云/阿里云轻量服务器 + Docker | 现有 FastMCP 直接搬 | 支持长驻进程与 Docker，按用量付费，国内访问选腾讯云 |
| **TypeScript（中期，全球边缘）** | Cloudflare Workers | 追求免费额度、全球低延迟、官方 MCP/OAuth 一等支持 | 用 TS 写薄传输层，规则读同一份 `rules/*.json`，核心资产不重写 |

## 公开演示页（v0.9.1 新增，买家可直接打开）
镜像内已有两个免鉴权路由，专门用来公开演示：

| 路由 | 方法 | 作用 |
|---|---|---|
| `/demo` | GET | 单页前端：贴一段话 → 立刻出风险等级、命中词、改写建议 |
| `/demo/analyze` | POST | 演示用 JSON 端点，`{"text":"...","industry":"general","platform":"douyin"}` |

设计约束（不要在演示里破坏它们）：
- `/demo/analyze` **固定 rules-only**（`use_llm=False`），公开无限次被刷也不消耗 token；
  交付版才在其上叠 LLM 语义层。
- 服务端强制 `2000` 字符上限与每 IP 每分钟 `20` 次限流，前端 `maxlength` 只是提示。
- 配了 `LCG_BEARER_TOKEN` 后 `/mcp` 照样要鉴权，但 `/demo` 与 `/healthz` 保持公开——
  演示页必须让没凭据的买家点得开。

本地起：
```bash
PYTHONPATH=src python -m uvicorn lcg.server_http:build_app --factory --host 0.0.0.0 --port 8000
# 浏览器打开 http://127.0.0.1:8000/demo
```
公网给买家看时记得：只暴露 `/demo` 与 `/healthz`，`/mcp` 始终开 Key。

## 远程化进度（v0.2.0 已内置传输与单令牌鉴权）
- [x] **传输**：`python -m lcg.server_http`（`pip install ".[http]"`）已提供 Streamable HTTP，挂载 `/mcp`，另有免鉴权探活 `/healthz`。
- [x] **鉴权（单令牌）**：设置 `LCG_BEARER_TOKEN` 即对 `/mcp` 强制 `Authorization: Bearer <token>`（纯 ASGI 中间件，不缓冲、兼容 SSE 流式）；客户端配置见 `examples/mcp-client.http.md`。
- [ ] **配置外置**：模型 key、`LCG_BEARER_TOKEN` 走平台 Secret / 环境变量（见 `.env.example`），不写进镜像。
- [ ] **OAuth / 多租户**：Cloudflare 官方 OAuth Provider，或网关层多令牌与配额。
- [ ] **计量与配额**：网关统计 tools/call 次数 → 订阅核减或额度扣减；支付由外部渠道处理，不自研。

## 运行时依赖
- 模型：硅基流动（国内）/ OpenRouter（海外），OpenAI 兼容，多模型路由 + 大模型兜底。
- 存储：Supabase（调用记录/向量）、Cloudflare R2 或腾讯云 COS（审计报告、日志）。
- 可观测：Langfuse（trace）、Sentry（异常）、UptimeRobot（在线率），报警可接 IM webhook（如 Slack/飞书）。

## 从 GitHub 自动部署（思路，P1 落地）
- **Railway/Render/腾讯云**：在平台控制台关联 GitHub 仓库，push main 即构建（用本目录 Dockerfile），无需在 CI 里存部署密钥。
- **Cloudflare（TS）**：仓库加 `wrangler.toml`，在 GitHub Secrets 配 `CLOUDFLARE_API_TOKEN`，Actions 里 `npx wrangler deploy`。
- 域名/DNS/CDN/证书：海外 Cloudflare 一站式（免费）；国内业务用腾讯云/阿里云并完成备案。

## 托管型 MCP 平台（省运维，可作分发副本）
可选用托管型 MCP 目录/平台部署；魔搭 Studio 仅用于演示，不作生产 SLA。
