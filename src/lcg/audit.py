# -*- coding: utf-8 -*-
"""
lcg.audit —— 检测/改写结果的本地审计留痕（零第三方依赖，可选启用）。

设计原则：
  · **默认关闭**：未设置环境变量 ``LCG_AUDIT_LOG``（路径）时不落盘；
  · **不拖垮主流程**：任何写盘异常都被吞掉并记录到返回值，绝不影响检测结果；
  · **可脱敏**：``LCG_AUDIT_REDACT=1`` 时不写入原始话术，仅保留长度与命中片段；
  · **双后端**：路径为 ``:memory:`` 或 ``.db/.sqlite/.sqlite3`` 时写 SQLite，
    其余按 JSONL 文本追加；两种后端读回结构一致，便于复核或导入报表。

注意：本模块只做本地结构化留痕，不做上传、不做远程汇聚；合规责任与数据留存
策略由部署方按自身业务与所在地法规确定。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import ledger

_LOCK = threading.Lock()
_MAX_MATCH = 20

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    action      TEXT NOT NULL,
    industry    TEXT NOT NULL DEFAULT '',
    platform    TEXT NOT NULL DEFAULT '',
    risk_level  TEXT NOT NULL DEFAULT '',
    mode        TEXT NOT NULL DEFAULT 'rule',
    count       INTEGER NOT NULL DEFAULT 0,
    hits        TEXT NOT NULL DEFAULT '[]',
    llm         TEXT NOT NULL DEFAULT '{}',
    text_len    INTEGER,
    redacted    INTEGER NOT NULL DEFAULT 0,
    operator    TEXT NOT NULL DEFAULT '',
    key_id      TEXT NOT NULL DEFAULT '',
    text        TEXT
);
"""


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """旧库平滑补列：已存在的列不重复添加。"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(audit_events)")}
    for col in ("operator", "key_id"):
        if col not in cols:
            conn.execute(f"ALTER TABLE audit_events ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")


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
                redact: Optional[bool] = None,
                operator: str = "", key_id: str = "") -> Dict[str, Any]:
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
        "operator": operator or "",
        "key_id": key_id or "",
    }
    if use_redact:
        event["text_len"] = len(text or "")
        event["redacted"] = True
    else:
        event["text"] = text or ""
        event["redacted"] = False
    return event


def _insert_sqlite(conn: sqlite3.Connection, event: Dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO audit_events "
        "(ts, action, industry, platform, risk_level, mode, count, hits, llm, "
        " text_len, redacted, operator, key_id, text) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event["ts"], event["action"], event.get("industry", ""),
            event.get("platform", ""), event.get("risk_level", ""),
            event.get("mode", "rule"), event.get("count", 0),
            json.dumps(event.get("hits", []), ensure_ascii=False),
            json.dumps(event.get("llm", {}), ensure_ascii=False),
            event.get("text_len"), 1 if event.get("redacted") else 0,
            event.get("operator", ""), event.get("key_id", ""),
            event.get("text"),
        ),
    )


def _load_sqlite(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT ts, action, industry, platform, risk_level, mode, count, hits, "
        "llm, text_len, redacted, operator, key_id, text "
        "FROM audit_events ORDER BY id"
    ).fetchall()
    events: List[Dict[str, Any]] = []
    for row in rows:
        event: Dict[str, Any] = {
            "ts": row["ts"], "action": row["action"],
            "industry": row["industry"], "platform": row["platform"],
            "risk_level": row["risk_level"], "mode": row["mode"],
            "count": row["count"],
            "hits": json.loads(row["hits"] or "[]"),
            "llm": json.loads(row["llm"] or "{}"),
            "redacted": bool(row["redacted"]),
            "operator": row["operator"], "key_id": row["key_id"],
        }
        if event["redacted"]:
            event["text_len"] = row["text_len"] or 0
        else:
            event["text"] = row["text"] or ""
        events.append(event)
    return events


def record(*, action: str, result: Dict[str, Any], text: str,
           path: Optional[str] = None, redact: Optional[bool] = None,
           operator: str = "", key_id: str = "") -> bool:
    """追加一条检测/改写结果；返回是否成功落盘。

    未配置路径时直接返回 False（视为禁用）；写盘异常不抛出。路径为 SQLite DSN
    时入库 ``audit_events`` 表，否则追加 JSONL。
    """
    target = path if path is not None else (_log_path().as_posix() if _log_path() else "")
    if not target:
        return False
    event = build_event(action=action, result=result, text=text, redact=redact,
                        operator=operator, key_id=key_id)

    if ledger.is_sqlite_dsn(target):
        try:
            with _LOCK:
                conn = ledger.connect(target)
                conn.execute(_SCHEMA)
                _ensure_columns(conn)
                _insert_sqlite(conn, event)
                conn.commit()
            return True
        except sqlite3.Error:
            return False

    file_path = Path(target)
    line = json.dumps(event, ensure_ascii=False)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK, file_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True
    except OSError:
        return False


def load_events(path: str) -> List[Dict[str, Any]]:
    """读回审计事件；损坏行跳过，SQLite 与 JSONL 结构一致。"""
    if not path:
        return []
    if ledger.is_sqlite_dsn(path):
        try:
            with _LOCK:
                conn = ledger.connect(path)
                conn.execute(_SCHEMA)
                _ensure_columns(conn)
                return _load_sqlite(conn)
        except sqlite3.Error:
            return []
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


def query(path: str, *, industry: str = "", platform: str = "",
          action: str = "", risk_level: str = "", operator: str = "",
          key_id: str = "", since: str = "", limit: int = 0) -> List[Dict[str, Any]]:
    """按行业 / 平台 / 动作 / 风险 / 操作人 / Key / 起始时间过滤审计事件。

    条件为空表示不过滤；``since`` 按 ISO 时间字符串字典序比较；``limit > 0`` 时只返回
    最近 ``limit`` 条。底层读取复用 :func:`load_events`，JSONL 与 SQLite 一致。
    """
    events = load_events(path)
    out: List[Dict[str, Any]] = []
    for ev in events:
        if industry and ev.get("industry") != industry:
            continue
        if platform and ev.get("platform") != platform:
            continue
        if action and ev.get("action") != action:
            continue
        if risk_level and ev.get("risk_level") != risk_level:
            continue
        if operator and ev.get("operator") != operator:
            continue
        if key_id and ev.get("key_id") != key_id:
            continue
        if since and ev.get("ts", "") < since:
            continue
        out.append(ev)
    if limit > 0:
        out = out[-limit:]
    return out
