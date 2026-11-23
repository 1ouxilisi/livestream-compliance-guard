# -*- coding: utf-8 -*-
"""
lcg.ledger —— 审计 / 反馈本地持久化的 DSN 判定与 SQLite 连接工厂（零第三方依赖）。

路径分流：
  · ``:memory:`` 或 ``.db / .sqlite / .sqlite3`` 结尾 → SQLite 后端；
  · 其余（``.jsonl`` / ``.json`` / 普通文件路径）→ JSONL 文本后端（现状兼容）。

SQLite 连接按 DSN 缓存复用；写异常由调用方吞掉并返回 False，不抛给主检测流程。
"""
from __future__ import annotations

import sqlite3
import threading
from typing import Dict, Optional

_SQLITE_EXTS = (".db", ".sqlite", ".sqlite3")
_LOCK = threading.Lock()
_CONNS: Dict[str, sqlite3.Connection] = {}


def is_sqlite_dsn(dsn: Optional[str]) -> bool:
    """路径指向 SQLite 库（内存库或 .db/.sqlite/.sqlite3 文件）时返回 True。"""
    raw = (dsn or "").strip()
    if not raw:
        return False
    if raw == ":memory:":
        return True
    return raw.lower().endswith(_SQLITE_EXTS)


def connect(dsn: str) -> sqlite3.Connection:
    """按 DSN 取缓存连接；连接失效时重建。``:memory:`` 为独立内存库。"""
    raw = dsn.strip()
    with _LOCK:
        conn = _CONNS.get(raw)
        if conn is not None:
            try:
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                _CONNS.pop(raw, None)
        conn = sqlite3.connect(raw, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _CONNS[raw] = conn
        return conn


def close_all() -> None:
    """关闭并清空全部缓存连接（测试隔离 / 进程退出用）。"""
    with _LOCK:
        for conn in _CONNS.values():
            try:
                conn.close()
            except sqlite3.Error:
                pass
        _CONNS.clear()
