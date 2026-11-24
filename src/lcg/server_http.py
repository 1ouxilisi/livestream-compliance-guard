# -*- coding: utf-8 -*-
"""
lcg.server_http —— 远程 MCP（Streamable HTTP）入口，含健康检查与可选 Bearer 鉴权。

- MCP 端点：POST/GET ``/mcp``（FastMCP streamable-http 默认路径）；
- 健康检查：GET ``/healthz``（始终放行，用于负载均衡/探活）；
- 鉴权：设置环境变量 ``LCG_BEARER_TOKEN``（单 Key，向后兼容）或
  ``LCG_BEARER_TOKENS``（逗号分隔多 Key）后，除 /healthz 外的请求必须带
  ``Authorization: Bearer <key>``，否则返回 401；均未设置则本地开放（仅限可信内网）。
  本层做静态 Key 校验、Key→租户映射（``LCG_KEY_TENANTS``）与配额预检：
  停用 / 未注册返回 403、调用次数超额返回 429；放行后记一次 calls，pipeline 结束回填
  LLM token 用量（存储由 ``LCG_STORE_DSN`` 选择内存 / SQLite）。不做账号注册 / 登录 /
  角色体系，也不做按租户词库 / 数据隔离，见 ``docs/DEPLOYMENT.md``。
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

from . import __version__, request_ctx, rules_store
from .server_stdio import create_mcp
from .tenant import UsageMeter, quota_store_from_env

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


def _parse_key_tenants(raw: "str | None" = None) -> dict[str, str]:
    """解析 ``LCG_KEY_TENANTS``（逗号分隔 ``key=tenant_id``）为 Key→租户映射。

    非法片段（不含 ``=``、空 key / tenant）跳过；未配置时返回空映射，即所有 Key
    不计入特定租户配额。
    """
    mapping: dict[str, str] = {}
    value = os.environ.get("LCG_KEY_TENANTS", "") if raw is None else raw
    for part in str(value or "").split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, tenant = part.partition("=")
        key, tenant = key.strip(), tenant.strip()
        if key and tenant:
            mapping[key] = tenant
    return mapping


def _parse_key_roles(raw: "str | None" = None) -> dict[str, str]:
    """解析 ``LCG_KEY_ROLES``（逗号分隔 ``key=role``）为 Key→角色映射。

    非法片段跳过；未配置时返回空映射，即请求上下文不带角色，工具守卫按未鉴权放行。
    角色合法性由身份层在权限校验时统一校验。
    """
    mapping: dict[str, str] = {}
    value = os.environ.get("LCG_KEY_ROLES", "") if raw is None else raw
    for part in str(value or "").split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, role = part.partition("=")
        key, role = key.strip(), role.strip()
        if key and role:
            mapping[key] = role
    return mapping


class BearerAuthASGI:
    """纯 ASGI 鉴权中间件（不缓冲响应体，兼容 MCP 的 SSE/流式响应）。

    鉴权通过后按 Key 映射租户做配额预检：停用 / 未注册返回 403，调用次数超额返回 429；
    放行后记一次请求级 calls，并把 (meter, tenant) 挂入请求上下文供 pipeline 回填 token 用量。
    计量异常或未映射 Key 不阻断请求。
    """

    def __init__(self, app: Any, tokens: "set[str] | None" = None,
                 meter: "UsageMeter | None" = None,
                 key_tenants: "dict[str, str] | None" = None,
                 key_roles: "dict[str, str] | None" = None) -> None:
        self.app = app
        self.tokens = tokens or set()
        self.meter = meter
        self.key_tenants = key_tenants or {}
        self.key_roles = key_roles or {}

    def _authorize(self, key: str) -> "tuple[str | None, JSONResponse | None]":
        """鉴权通过后做配额预检：返回 (tenant_id, None) 放行，(None, response) 拦截。"""
        tenant = self.key_tenants.get(key)
        if self.meter is None or not tenant:
            return tenant, None
        ok, reason = self.meter.check(tenant, calls=1)
        if ok:
            return tenant, None
        if reason in ("quota_exceeded", "token_exceeded"):
            status, error = 429, "rate_limited"
        else:
            status, error = 403, "forbidden"
        return None, JSONResponse(
            {"error": error, "detail": reason}, status_code=status)

    def _record_calls(self, tenant: str) -> None:
        if self.meter is None:
            return
        try:
            self.meter.record(tenant, calls=1)
        except Exception:
            # 计量异常不阻断主流程，与计量层容错口径一致
            pass

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not self.tokens or scope.get("path") in _PUBLIC_PATHS:
            return await self.app(scope, receive, send)
        headers = {k.decode("latin1").lower(): v.decode("latin1")
                   for k, v in scope.get("headers", [])}
        authorization = headers.get("authorization", "")
        prefix = "Bearer "
        key = authorization[len(prefix):] if authorization.startswith(prefix) else ""
        if key in self.tokens:
            tenant, blocked = self._authorize(key)
            if blocked is not None:
                return await blocked(scope, receive, send)
            ctx_token = None
            if tenant:
                self._record_calls(tenant)
            # 身份（key_id）与租户配额解耦：鉴权通过即挂载，便于审计到人；
            # 未映射租户时 tenant_id 留空，计量回填自动跳过。
            ctx_token = request_ctx.set_request(
                request_ctx.RequestContext(
                    tenant_id=tenant or "", meter=self.meter, key_id=key,
                    role=self.key_roles.get(key, "")))
            try:
                return await self.app(scope, receive, send)
            finally:
                if ctx_token is not None:
                    request_ctx.reset(ctx_token)
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


def build_app(token: "str | list[str] | None" = None,
              key_tenants: "str | dict[str, str] | None" = None,
              meter: "UsageMeter | None" = None,
              key_roles: "str | dict[str, str] | None" = None):
    """构造 Starlette app（测试可直接用 ASGI in-process 或 uvicorn 承载）。

    - ``key_tenants``：``key=tenant`` 映射；传字符串走 ``LCG_KEY_TENANTS`` 同款解析，
      传 dict 直接使用；未配置则 Key 不归属特定租户、不计配额。
    - ``key_roles``：``key=role`` 映射；传字符串走 ``LCG_KEY_ROLES`` 同款解析，
      传 dict 直接使用；未配置则请求上下文不带角色，工具守卫按未鉴权放行。
    - ``meter``：可注入计量器（测试用）；默认按 ``LCG_STORE_DSN`` 建配额存储。
    """
    tokens = _parse_tokens(token)
    # 每次构建全新 FastMCP 实例：Streamable HTTP 会话管理器每实例只能启动一次
    app = create_mcp().streamable_http_app()
    # 健康检查置于 MCP 路由之前（路径不冲突）
    app.router.routes.insert(0, Route("/healthz", healthz, methods=["GET"]))
    if tokens:
        if isinstance(key_tenants, dict):
            mapping = dict(key_tenants)
        else:
            mapping = _parse_key_tenants(key_tenants)
        role_mapping = (dict(key_roles) if isinstance(key_roles, dict)
                        else _parse_key_roles(key_roles))
        store_meter = meter or UsageMeter(quota_store_from_env())
        app.add_middleware(BearerAuthASGI, tokens=tokens, meter=store_meter,
                           key_tenants=mapping, key_roles=role_mapping)
    return app


def run() -> None:
    import uvicorn

    host = os.environ.get("LCG_HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("LCG_HTTP_PORT", "8000"))
    uvicorn.run(build_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
