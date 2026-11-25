# -*- coding: utf-8 -*-
"""
lcg.server_stdio —— MCP stdio 传输服务器。

把规则引擎暴露为 6 个 MCP 工具：
- scan_text(text, industry, platform)：单条文本风险扫描（纯规则，确定性）
- scan_livestream(transcript, industry, platform)：整场直播逐句扫描
- compliance_rules(industry, platform)：查询当前生效规则
- safe_rewrite(text, industry, platform)：命中词替换建议（纯规则）
- scan_smart(text, industry, platform, use_llm)：规则硬底线＋LLM 语义融合检测（无 key 自动降级）
- rewrite_smart(text, industry, platform, use_llm)：LLM 自然整句改写＋复检，失败回退规则替换

工具注册集中在 create_mcp() 工厂：stdio 使用模块级单例 mcp，远程 HTTP 入口
每次构建新实例（FastMCP 的 Streamable HTTP 会话管理器每个实例只能启动一次）。

行业键：内置 jadeite/general/food/cosmetics，外加 rules/plugins/*.json 里声明的任意
industry（scripts/new_plugin.py 生成即生效，无需改代码）。传未知行业会在入参校验阶段
报错并列出当前可选值。

运行（在项目根目录）：
    python server.py            # 对外兼容入口
    python -m lcg.server_stdio  # 模块直跑
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP

from . import engine, pipeline, request_ctx
from .identity import action_for_tool, require_permission

SERVER_NAME = "livestream-compliance-guard"


def _guard(tool_name: str) -> None:
    """按当前请求上下文的角色校验工具动作；无上下文（stdio / 未启用鉴权）时放行。"""
    ctx = request_ctx.current()
    role = ctx.role if ctx else ""
    require_permission(role, action_for_tool(tool_name))


def create_mcp() -> FastMCP:
    """创建一个注册好全部工具的 FastMCP 实例（stdio/HTTP 各自独立调用）。"""
    mcp = FastMCP(SERVER_NAME)

    @mcp.tool()
    def scan_text(
        text: str,
        industry: str = "jadeite",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
    ) -> Dict[str, Any]:
        """扫描单条直播/短视频文本，返回风险等级、命中明细与处置建议。

        industry 可为内置四类（jadeite/general/food/cosmetics），也可为自建插件包的行业键。
        """
        _guard("scan_text")
        return engine.detect(text, industry=industry, platform=platform)

    @mcp.tool()
    def scan_livestream(
        transcript: List[Dict[str, str]],
        industry: str = "jadeite",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
    ) -> Dict[str, Any]:
        """扫描整场直播逐句文本。transcript 为 [{seq, speaker, text}, ...]。"""
        _guard("scan_livestream")
        return engine.scan_batch(transcript, industry=industry, platform=platform)

    @mcp.tool()
    def compliance_rules(
        industry: str = "jadeite",
        platform: Optional[Literal["douyin", "kuaishou", "shipinhao", "taobao"]] = None,
    ) -> Dict[str, Any]:
        """返回当前生效的合规规则与规则库版本，供客户端展示/同步。

        industry 支持内置四类与任意已加载插件包行业键。
        """
        _guard("compliance_rules")
        return engine.get_rules(industry=industry, platform=platform)

    @mcp.tool()
    def safe_rewrite(
        text: str,
        industry: str = "jadeite",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
    ) -> Dict[str, Any]:
        """对命中词给出替换建议、改写全文并复检风险；正式话术请人工复核。"""
        _guard("safe_rewrite")
        return engine.suggest_rewrite(text, industry=industry, platform=platform)

    @mcp.tool()
    def scan_smart(
        text: str,
        industry: str = "general",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """规则硬底线＋LLM 语义融合扫描：识别谐音/拆字/emoji/近义暗示等规避表达。

        规则永远先跑且不可被 LLM 降低；未配置模型 key、超时或返回异常时自动回退纯规则
        （mode=rules_only），正常融合时 mode=rules_plus_llm。
        """
        _guard("scan_smart")
        return pipeline.analyze(text, industry=industry, platform=platform, use_llm=use_llm)

    @mcp.tool()
    def rewrite_smart(
        text: str,
        industry: str = "general",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """优先用 LLM 生成保留卖点的自然合规话术并规则复检；不可用或复检不通过则回退规则替换。"""
        _guard("rewrite_smart")
        return pipeline.smart_rewrite(text, industry=industry, platform=platform, use_llm=use_llm)

    return mcp


# 模块级单例：供 stdio run() 与直接 import 使用
mcp = create_mcp()


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
