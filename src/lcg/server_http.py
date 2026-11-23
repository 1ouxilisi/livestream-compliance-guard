# -*- coding: utf-8 -*-
"""
lcg.server_http —— 远程 MCP（Streamable HTTP）入口，含健康检查与可选 Bearer 鉴权。

- MCP 端点：POST/GET ``/mcp``（FastMCP streamable-http 默认路径）；
- 健康检查：GET ``/healthz``（始终放行，用于负载均衡/探活）；
- 鉴权：设置环境变量 ``LCG_BEARER_TOKEN``（单 Key，向后兼容）或
  ``LCG_BEARER_TOKENS``（逗号分隔多 Key）后，除 /healthz 外的请求必须带
  ``Authorization: Bearer <key>``，否则返回 401；均未设置则本地开放（仅限可信内网）。
  本层只做静态 Key 校验，不做账号注册 / 登录 / 角色体系；Key 与租户用量的挂钩属后续
  平台化能力，见 ``docs/DEPLOYMENT.md``。
- 监听：``LCG_HTTP_HOST``（默认 0.0.0.0）、``LCG_HTTP_PORT``（默认 8000）。

运行：
    pip install ".[http]"          # 或 pip install uvicorn
    LCG_BEARER_TOKEN=xxx python -m lcg.server_http
依赖传输层（mcp/starlette/uvicorn）；规则核心仍零依赖。
"""
from __future__ import annotations

import os
from typing import Any

from starlette.responses import JSONResponse
from starlette.routing import Route

from . import __version__, rules_store
from .server_stdio import create_mcp

_PUBLIC_PATHS = {"/healthz"}


def _parse_tokens(explicit: "str | list[str] | None") -> set[str]:
    """合并显式入参与环境变量，得到合法 Bearer Key 集合（去空白、去空串）。"""
    tokens: set[str] = set()

    def _add(value: Any) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                _add(item)
            return
        for part in str(value or "").split(","):
            part = part.strip()
            if part:
                tokens.add(part)

    _add(explicit if explicit is not None else os.environ.get("LCG_BEARER_TOKEN", ""))
    _add(os.environ.get("LCG_BEARER_TOKENS", ""))
    return tokens


class BearerAuthASGI:
    """纯 ASGI 鉴权中间件（不缓冲响应体，兼容 MCP 的 SSE/流式响应）。"""

    def __init__(self, app: Any, tokens: "set[str] | None" = None) -> None:
        self.app = app
        self.tokens = tokens or set()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not self.tokens or scope.get("path") in _PUBLIC_PATHS:
            return await self.app(scope, receive, send)
        headers = {k.decode("latin1").lower(): v.decode("latin1")
                   for k, v in scope.get("headers", [])}
        authorization = headers.get("authorization", "")
        expected = {f"Bearer {key}" for key in self.tokens}
        if authorization in expected:
            return await self.app(scope, receive, send)
        resp = JSONResponse(
            {"error": "unauthorized", "detail": "missing or invalid Bearer token"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"})
        await resp(scope, receive, send)


async def healthz(request) -> JSONResponse:  # noqa: ARG001
    return JSONResponse({
        "status": "ok",
        "service": "livestream-compliance-guard",
        "version": __version__,
        "rules_version": rules_store.meta().get("version"),
        "rule_count": len(rules_store.all_rules()),
    })


def build_app(token: "str | list[str] | None" = None):
    """构造 Starlette app（测试可直接用 ASGI in-process 或 uvicorn 承载）。"""
    tokens = _parse_tokens(token)
    # 每次构建全新 FastMCP 实例：Streamable HTTP 会话管理器每实例只能启动一次
    app = create_mcp().streamable_http_app()
    # 健康检查置于 MCP 路由之前（路径不冲突）
    app.router.routes.insert(0, Route("/healthz", healthz, methods=["GET"]))
    if tokens:
        app.add_middleware(BearerAuthASGI, tokens=tokens)
    return app


def run() -> None:
    import uvicorn

    host = os.environ.get("LCG_HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("LCG_HTTP_PORT", "8000"))
    uvicorn.run(build_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
