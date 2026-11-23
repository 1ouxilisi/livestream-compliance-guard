# -*- coding: utf-8 -*-
"""远程 Streamable HTTP 入口：healthz、Bearer 鉴权、MCP 握手（真实本地随机端口）。"""
import asyncio
import json

import pytest

pytest.importorskip("mcp")
uvicorn = pytest.importorskip("uvicorn")

from lcg import server_http  # noqa: E402


async def _serve(token):
    config = uvicorn.Config(
        server_http.build_app(token=token),
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
