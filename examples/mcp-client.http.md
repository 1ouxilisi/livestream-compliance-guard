# 远程 MCP（Streamable HTTP）客户端配置

> 远程入口已内置（v0.2.0）：`python -m lcg.server_http`（先 `pip install ".[http]"` 或安装 uvicorn）。
> MCP 端点为 `/mcp`，健康检查为 `/healthz`；设置环境变量 `LCG_BEARER_TOKEN` 即开启 Bearer 鉴权，
> 不设置则本地开放（仅限可信内网/本机）。

## 1. 启动服务
```bash
# 本机开放（仅可信内网）
python -m lcg.server_http

# 公网：务必设置 token（Linux/macOS）
LCG_BEARER_TOKEN=sk-xxx LCG_HTTP_PORT=8000 python -m lcg.server_http
```
```powershell
# Windows PowerShell
$env:LCG_BEARER_TOKEN='sk-xxx'; python -m lcg.server_http
```

## 2. 健康检查（无需鉴权）
```bash
curl -s http://localhost:8000/healthz
# {"status":"ok","service":"livestream-compliance-guard","version":"0.9.0",
#  "rules_version":"v1.5","rule_count":20}
```

## 3. MCP 客户端配置（URL / Token 按部署替换）
```json
{
  "mcpServers": {
    "livestream-compliance-guard": {
      "url": "https://<your-domain>/mcp",
      "headers": { "Authorization": "Bearer <LCG_BEARER_TOKEN>" }
    }
  }
}
```
未设置 `LCG_BEARER_TOKEN` 时可省略 `headers`。

## 4. 用 curl 验证 tools/list
```bash
curl -s http://localhost:8000/mcp \
  -H "Authorization: Bearer <LCG_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## 5. 调用 scan_text（tools/call）
```bash
curl -s http://localhost:8000/mcp \
  -H "Authorization: Bearer <LCG_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"scan_text",
                 "arguments":{"text":"本品100%保真收藏必涨","industry":"jadeite","platform":"douyin"}}}'
```

> 配额与计量在网关层实现；支付由外部渠道处理，本示例不含支付集成。
