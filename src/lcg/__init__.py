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
  ingest.py        异构 ASR/字幕片段归一为 scan_batch 契约（不做 ASR/OCR）
  aggregator.py    整场结果分布/类别/主播聚合与待整改清单（纯统计）
  feedback.py      误报/漏报/存疑本地 JSONL 记录与 CSV 导出（可选启用）
  audit.py         可选本地 JSONL 审计留痕（默认关闭、可脱敏；零依赖）
  sources.py       可插拔输入源协议与内存桩（不接真实 ASR/OCR、不发网络请求）
  tenant.py        租户配额与用量计量内存骨架（无持久化、无鉴权；演进见 DEPLOYMENT.md）
  identity.py      账号/角色/API Key 内存映射骨架（无登录注册、无持久化、不跨进程）
  cache.py         可插拔缓存协议与进程内内存实现（可选 TTL；外置 Redis 由部署方实现）
  server_stdio.py  FastMCP stdio 入口（依赖 mcp）
  server_http.py   Streamable HTTP + Bearer 鉴权入口（依赖 mcp/uvicorn）

根目录 server.py 是保持向后兼容的薄 shim，re-export 本包的公共 API。
"""
from . import cache, engine, identity
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

__version__ = "0.9.1"

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
    "identity",
    "cache",
]
