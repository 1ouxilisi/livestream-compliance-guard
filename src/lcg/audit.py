# -*- coding: utf-8 -*-
"""
lcg.audit —— 检测/改写结果的本地审计留痕（零第三方依赖，可选启用）。

设计原则：
  · **默认关闭**：未设置环境变量 ``LCG_AUDIT_LOG``（JSONL 文件路径）时不落盘，
    与规则核心“零配置可跑”一致；
  · **不拖垮主流程**：任何写盘异常都被吞掉并记录到返回值，绝不影响检测结果；
  · **可脱敏**：``LCG_AUDIT_REDACT=1`` 时不写入原始话术，仅保留长度与命中片段
    （片段截断），避免在审计日志里沉淀主播口播原文等敏感内容；
  · 每行一个 JSON 对象（JSONL），便于后续用 ``load_events`` 复核或导入报表。

注意：本模块只做本地结构化留痕，不做上传、不做远程汇聚；合规责任与数据留存
策略由部署方按自身业务与所在地法规确定。
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_MAX_MATCH = 20


def _log_path() -> Optional[Path]:
    raw = (os.environ.get("LCG_AUDIT_LOG") or "").strip()
    return Path(raw) if raw else None


def _redact_enabled() -> bool:
    return (os.environ.get("LCG_AUDIT_REDACT", "0").strip().lower()
            in ("1", "true", "yes", "on"))


def _clip(text: str, limit: int = _MAX_MATCH) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def _hits_summary(hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for h in hits or []:
        out.append({
            "category": str(h.get("category", "")),
            "severity": str(h.get("severity", "")),
            "source": str(h.get("source", "rule")),
            "match": _clip(str(h.get("match", ""))),
        })
    return out


def build_event(*, action: str, result: Dict[str, Any], text: str,
                redact: Optional[bool] = None) -> Dict[str, Any]:
    """从 detect/analyze/rewrite 结果提炼一条审计事件（不写盘）。"""
    use_redact = _redact_enabled() if redact is None else redact
    llm = result.get("llm") or {}
    event: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "industry": result.get("industry", ""),
        "platform": result.get("platform", ""),
        "risk_level": result.get("risk_level", ""),
        "mode": result.get("mode", "rule"),
        "count": result.get("count", len(result.get("hits", []))),
        "hits": _hits_summary(result.get("hits", [])),
        "llm": {
            "status": llm.get("status", ""),
            "model": llm.get("model", ""),
            "cached": llm.get("cached", False),
            "total_tokens": llm.get("total_tokens", 0),
        },
    }
    if use_redact:
        event["text_len"] = len(text or "")
        event["redacted"] = True
    else:
        event["text"] = text or ""
        event["redacted"] = False
    return event


def record(*, action: str, result: Dict[str, Any], text: str,
           path: Optional[str] = None, redact: Optional[bool] = None) -> bool:
    """把一条检测/改写结果追加到审计 JSONL；返回是否成功落盘。

    未配置路径时直接返回 False（视为禁用）；写盘异常不抛出。
    """
    target = Path(path) if path else _log_path()
    if target is None:
        return False
    event = build_event(action=action, result=result, text=text, redact=redact)
    line = json.dumps(event, ensure_ascii=False)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK, target.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True
    except OSError:
        return False


def load_events(path: str) -> List[Dict[str, Any]]:
    """读回审计 JSONL；损坏行跳过并继续，返回可解析的事件列表。"""
    p = Path(path)
    if not p.is_file():
        return []
    events: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
