# -*- coding: utf-8 -*-
"""公开演示端点：/demo 单页、/demo/analyze 纯规则检测、限流与输入校验（真实本地端口）。"""
import asyncio

import pytest

pytest.importorskip("mcp")
uvicorn = pytest.importorskip("uvicorn")

from lcg import server_http  # noqa: E402


async def _serve(token=""):
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


@pytest.fixture(autouse=True)
def _reset_rate_windows():
    """限流窗口是进程级状态，用例之间必须隔离，否则互相打满 429。"""
    server_http._demo_windows.clear()
    yield
    server_http._demo_windows.clear()


@pytest.mark.asyncio
async def test_demo_page_is_public_html():
    import httpx

    server, task, port = await _serve()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"http://127.0.0.1:{port}/demo")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/html")
            body = r.text
            assert "Content Moderation Guard" in body
            assert "demo/analyze" in body          # 前端确实指向该端点
            assert "rules-only" in body            # 不暗示已带语义层
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_demo_analyze_flags_high_risk_and_rewrites():
    import httpx

    server, task, port = await _serve()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"http://127.0.0.1:{port}/demo/analyze",
                json={"text": "这款减肥茶三天瘦十斤，绝对安全无副作用。",
                      "industry": "food", "platform": "douyin"})
            assert r.status_code == 200
            data = r.json()
            assert data["mode"] == "rules_only"
            assert data["detect"]["risk_level"] in {"high", "medium"}
            assert data["detect"]["count"] >= 1
            assert data["detect"]["llm"]["status"] == "disabled"   # 绝不调模型
            assert data["rewrite"] is not None
            assert data["rewrite"]["rewrite_mode"] == "rules_only"
            assert isinstance(data["rule_count"], int) and data["rule_count"] > 0
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_demo_analyze_clean_input_skips_rewrite():
    import httpx

    server, task, port = await _serve()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"http://127.0.0.1:{port}/demo/analyze",
                json={"text": "本品为普通食品，热量已标注，请按包装说明食用。"})
            assert r.status_code == 200
            data = r.json()
            assert data["detect"]["risk_level"] == "clean"
            assert data["rewrite"] is None
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"text": ""},
    {"text": "   "},
    {"text": 123},
    {"text": "x" * (server_http._DEMO_MAX_CHARS + 1)},
    {"text": "正常文本", "industry": "unknown-industry"},
])
async def test_demo_analyze_rejects_bad_input(payload):
    import httpx

    server, task, port = await _serve()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"http://127.0.0.1:{port}/demo/analyze",
                                  json=payload)
            assert r.status_code == 400
            assert r.json()["error"] == "bad_request"
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_demo_analyze_rejects_non_json_body():
    import httpx

    server, task, port = await _serve()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"http://127.0.0.1:{port}/demo/analyze",
                                  content=b"not-json",
                                  headers={"Content-Type": "text/plain"})
            assert r.status_code == 400
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_demo_rate_limited():
    import httpx

    server, task, port = await _serve()
    try:
        async with httpx.AsyncClient() as client:
            codes = []
            for _ in range(server_http._DEMO_RATE_LIMIT + 1):
                r = await client.post(f"http://127.0.0.1:{port}/demo/analyze",
                                      json={"text": "测试限流"})
                codes.append(r.status_code)
            assert codes[:-1] == [200] * server_http._DEMO_RATE_LIMIT
            assert codes[-1] == 429
    finally:
        await _stop(server, task)


@pytest.mark.asyncio
async def test_demo_stays_public_when_token_configured():
    """配了 Bearer 后 /mcp 要鉴权，但演示页必须仍然对买家开放。"""
    import httpx

    server, task, port = await _serve(token="sk-test")
    try:
        async with httpx.AsyncClient() as client:
            assert (await client.get(f"http://127.0.0.1:{port}/demo")).status_code == 200
            r = await client.post(f"http://127.0.0.1:{port}/demo/analyze",
                                  json={"text": "加微信领红包"})
            assert r.status_code == 200
            # 未带 Key 访问 MCP 仍应被拦
            assert (await client.post(f"http://127.0.0.1:{port}/mcp",
                                      json={})).status_code == 401
    finally:
        await _stop(server, task)
