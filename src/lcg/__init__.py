# -*- coding: utf-8 -*-
"""
lcg —— livestream-compliance-guard 规则引擎包（能力标准件 ①）。

分层：
  models.py        枚举常量、入参校验、等长(全角/繁简)与紧凑(阻断符)归一化（零依赖）
  rules_store.py   加载核心包 rules.v1.json ＋ rules/plugins/*.json 行业插件并聚合
                   （JSON 事实源，零依赖）
  engine.py        检测 / 批量聚合 / 改写 / 规则查询（纯逻辑，零依赖；规则硬底线）
  llm.py           LLM 语义层客户端（OpenAI 兼容，可选依赖；无 key/故障可降级）
  pipeline.py      规则硬底线＋LLM 融合编排（analyze / smart_rewrite）
  server_stdio.py  FastMCP stdio 入口（依赖 mcp）
  server_http.py   Streamable HTTP + Bearer 鉴权入口（依赖 mcp/uvicorn）

根目录 server.py 是保持向后兼容的薄 shim，re-export 本包的公共 API。
"""
from . import engine
from .models import (
    INDUSTRIES,
    PLATFORMS,
    RISK_LEVELS,
    SEV_ORDER,
    normalize_text,
    validate_context,
)
from .rules_store import (
    RULES_PATH,
    active_rules,
    all_rules,
    load_payload,
    replacements,
)

__version__ = "0.7.1"

__all__ = [
    "__version__",
    "INDUSTRIES",
    "PLATFORMS",
    "RISK_LEVELS",
    "SEV_ORDER",
    "normalize_text",
    "validate_context",
    "RULES_PATH",
    "load_payload",
    "all_rules",
    "active_rules",
    "replacements",
    "engine",
]
