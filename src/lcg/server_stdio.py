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

运行（在项目根目录）：
    python server.py            # 对外兼容入口
    python -m lcg.server_stdio  # 模块直跑
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP

from . import engine, pipeline

SERVER_NAME = "livestream-compliance-guard"


def create_mcp() -> FastMCP:
    """创建一个注册好全部工具的 FastMCP 实例（stdio/HTTP 各自独立调用）。"""
    mcp = FastMCP(SERVER_NAME)

    @mcp.tool()
    def scan_text(
        text: str,
        industry: Literal["jadeite", "general", "food", "cosmetics"] = "jadeite",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
    ) -> Dict[str, Any]:
        """扫描单条直播/短视频文本，返回风险等级、命中明细与处置建议。"""
        return engine.detect(text, industry=industry, platform=platform)

    @mcp.tool()
    def scan_livestream(
        transcript: List[Dict[str, str]],
        industry: Literal["jadeite", "general", "food", "cosmetics"] = "jadeite",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
    ) -> Dict[str, Any]:
        """扫描整场直播逐句文本。transcript 为 [{seq, speaker, text}, ...]。"""
        return engine.scan_batch(transcript, industry=industry, platform=platform)

    @mcp.tool()
    def compliance_rules(
        industry: Literal["jadeite", "general", "food", "cosmetics"] = "jadeite",
        platform: Optional[Literal["douyin", "kuaishou", "shipinhao", "taobao"]] = None,
    ) -> Dict[str, Any]:
        """返回当前生效的合规规则与规则库版本，供客户端展示/同步。"""
        return engine.get_rules(industry=industry, platform=platform)

    @mcp.tool()
    def safe_rewrite(
        text: str,
        industry: Literal["jadeite", "general", "food", "cosmetics"] = "jadeite",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
    ) -> Dict[str, Any]:
        """对命中词给出替换建议、改写全文并复检风险；正式话术请人工复核。"""
        return engine.suggest_rewrite(text, industry=industry, platform=platform)

    @mcp.tool()
    def scan_smart(
        text: str,
        industry: Literal["jadeite", "general", "food", "cosmetics"] = "general",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """规则硬底线＋LLM 语义融合扫描：识别谐音/拆字/emoji/近义暗示等规避表达。

        规则永远先跑且不可被 LLM 降低；未配置模型 key、超时或返回异常时自动回退纯规则
        （mode=rules_only），正常融合时 mode=rules_plus_llm。
        """
        return pipeline.analyze(text, industry=industry, platform=platform, use_llm=use_llm)

    @mcp.tool()
    def rewrite_smart(
        text: str,
        industry: Literal["jadeite", "general", "food", "cosmetics"] = "general",
        platform: Literal["douyin", "kuaishou", "shipinhao", "taobao"] = "douyin",
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """优先用 LLM 生成保留卖点的自然合规话术并规则复检；不可用或复检不通过则回退规则替换。"""
        return pipeline.smart_rewrite(text, industry=industry, platform=platform, use_llm=use_llm)

    return mcp


# 模块级单例：供 stdio run() 与直接 import 使用
mcp = create_mcp()


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
