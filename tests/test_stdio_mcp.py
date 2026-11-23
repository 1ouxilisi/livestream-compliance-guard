# -*- coding: utf-8 -*-
"""B9：通过 stdio 子进程做真实 MCP 协议握手、工具列举与调用、非法入参错误。"""
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_stdio_mcp_contract():
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    params = StdioServerParameters(
        command=sys.executable, args=[str(ROOT / "server.py")], env=env)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert {"scan_text", "scan_livestream", "compliance_rules", "safe_rewrite",
                    "scan_smart", "rewrite_smart"} <= names

            res = await session.call_tool(
                "scan_text",
                {"text": "100%保真，加微信私下交易", "industry": "general", "platform": "douyin"})
            data = json.loads(res.content[0].text)
            assert data["risk_level"] == "high"

            # 非法 industry 必须以工具错误返回，而不是静默落到默认词库
            bad = await session.call_tool(
                "scan_text", {"text": "干净", "industry": "nope", "platform": "douyin"})
            assert getattr(bad, "isError", False) is True
