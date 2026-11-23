# -*- coding: utf-8 -*-
"""远程 Streamable HTTP 入口：healthz、Bearer 鉴权、MCP 握手（真实本地随机端口）。"""
import asyncio
import json

import pytest

pytest.importorskip("mcp")
uvicorn = pytest.importorskip("uvicorn")

from lcg import server_http  # noqa: E402


async def _serve(token, meter=None, key_tenants=None):
    config = uvicorn.Config(
        server_http.build_app(token=token, meter=meter, key_tenants=key_tenants),
        host="127.0.0.1", port=0, log_level="critical")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    return server, task, port


async def _stop(server, task):
    server.should_exit = True
    await task


@pytest.mark.asyncio
async def test_healthz_and_open_mcp():
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    server, task, port = await _serve("")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"http://127.0.0.1:{port}/healthz")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok" and body["rule_count"] == 20

        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (rd, wr, _):
            async with ClientSession(rd, wr) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert {"scan_text", "scan_livestream", "compliance_rules", "safe_rewrite",
                        "scan_smart", "rewrite_smart"} <= names
                res = await session.call_tool(
                    "scan_text",
                    {"text": "100%保真，加微信", "industry": "general", "platform": "douyin"})
                assert json.loads(res.content[0].text)["risk_level"] == "high"
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_bearer_enforced():
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    server, task, port = await _serve("secret-token")
    try:
        async with httpx.AsyncClient() as client:
            # healthz 始终放行
            assert (await client.get(f"http://127.0.0.1:{port}/healthz")).status_code == 200
            # /mcp 无凭证 / 错凭证 -> 401
            assert (await client.post(f"http://127.0.0.1:{port}/mcp")).status_code == 401
            assert (await client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": "Bearer wrong"})).status_code == 401

        # 正确 Bearer 才能握手（新 API 通过外部 httpx.Client 带请求头）
        auth_client = httpx.AsyncClient(
            headers={"Authorization": "Bearer secret-token"})
        async with auth_client as http_client, \
                streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp",
                    http_client=http_client) as (rd, wr, _):
            async with ClientSession(rd, wr) as session:
                await session.initialize()
                assert len((await session.list_tools()).tools) == 6
    finally:
        await _stop(server, task)


def test_parse_tokens_explicit_and_env(monkeypatch):
    monkeypatch.delenv("LCG_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("LCG_BEARER_TOKENS", raising=False)
    assert server_http._parse_tokens("a, b ,,c") == {"a", "b", "c"}
    assert server_http._parse_tokens(["x", " y "]) == {"x", "y"}
    monkeypatch.setenv("LCG_BEARER_TOKEN", "single")
    monkeypatch.setenv("LCG_BEARER_TOKENS", "k1, k2")
    assert server_http._parse_tokens(None) == {"single", "k1", "k2"}


def test_parse_key_tenants(monkeypatch):
    monkeypatch.delenv("LCG_KEY_TENANTS", raising=False)
    parsed = server_http._parse_key_tenants("k1=tenant_a, k2 = tenant_b , bad,,=x")
    assert parsed == {"k1": "tenant_a", "k2": "tenant_b"}
    monkeypatch.setenv("LCG_KEY_TENANTS", "envk=envtenant")
    assert server_http._parse_key_tenants(None) == {"envk": "envtenant"}


@pytest.mark.asyncio
async def test_meter_records_mapped_tenant():
    import httpx

    from lcg.tenant import Tenant, UsageMeter

    meter = UsageMeter()
    meter.store.register(Tenant(id="tenant_a", name="甲"))
    meter.store.register(Tenant(id="tenant_b", name="乙"))
    mapping = {"ka": "tenant_a", "kb": "tenant_b"}

    server, task, port = await _serve(["ka", "kb"], meter=meter, key_tenants=mapping)
    try:
        async with httpx.AsyncClient() as client:
            # healthz 始终放行且不计费
            await client.get(f"http://127.0.0.1:{port}/healthz")
            # 映射 Key 放行并按 Key 记入对应租户
            await client.post(f"http://127.0.0.1:{port}/mcp",
                              headers={"Authorization": "Bearer ka"})
            await client.post(f"http://127.0.0.1:{port}/mcp",
                              headers={"Authorization": "Bearer kb"})
            # 错误 Key 401，不计费
            wrong = await client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": "Bearer nope"})
            assert wrong.status_code == 401

        snap = meter.snapshot()
        assert snap["tenant_a"]["calls"] == 1
        assert snap["tenant_b"]["calls"] == 1
        assert set(snap) == {"tenant_a", "tenant_b"}
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_multi_key_bearer():
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    server, task, port = await _serve(["key-a", "key-b"])
    try:
        async with httpx.AsyncClient() as client:
            assert (await client.post(f"http://127.0.0.1:{port}/mcp")).status_code == 401
            assert (await client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": "Bearer nope"})).status_code == 401

        # 任一合法 Key 均可握手
        auth_client = httpx.AsyncClient(
            headers={"Authorization": "Bearer key-b"})
        async with auth_client as http_client, \
                streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp",
                    http_client=http_client) as (rd, wr, _):
            async with ClientSession(rd, wr) as session:
                await session.initialize()
                assert len((await session.list_tools()).tools) == 6
    finally:
        await _stop(server, task)

