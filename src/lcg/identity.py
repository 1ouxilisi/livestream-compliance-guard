# -*- coding: utf-8 -*-
"""lcg.identity: account / role / API Key identity skeleton.

Boundary:
  * Key -> tenant / role / operator mapping; default in-memory, with an
    optional local SQLite backend (``LCG_IDENTITY_DSN``) that persists on disk.
    No password hash, no login/register UI, no cross-process sharing.
  * Production identity must implement ``IdentityStore`` against an external
    identity service; see docs/DEPLOYMENT.md.
  * Role is a label carried to audit trails; role-based endpoint gating is not
    implemented in this round.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Protocol

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER)


def validate_role(role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"unsupported role={role!r}, expected: {', '.join(ROLES)}")
    return role


@dataclass
class ApiKey:
    key: str
    tenant_id: str
    role: str = ROLE_VIEWER
    user_id: str = ""
    active: bool = True
    created_at: str = ""
    last_used_at: Optional[str] = None


@dataclass
class ResolvedIdentity:
    key: str
    tenant_id: str
    role: str
    user_id: str


class IdentityStore(Protocol):
    """Identity storage protocol; swappable for DB / external identity later."""

    def register_key(self, api_key: ApiKey) -> None: ...

    def resolve(self, key: str) -> Optional[ResolvedIdentity]: ...

    def revoke(self, key: str) -> bool: ...

    def touch(self, key: str, when: str) -> None: ...

    def list_keys(self, tenant_id: Optional[str] = None) -> List[ApiKey]: ...


class InMemoryIdentityStore:
    """In-memory identity map (thread-safe; cleared on restart, non-persistent)."""

    def __init__(self) -> None:
        self._keys: Dict[str, ApiKey] = {}
        self._lock = threading.Lock()

    def register_key(self, api_key: ApiKey) -> None:
        validate_role(api_key.role)
        with self._lock:
            self._keys[api_key.key] = api_key

    def resolve(self, key: str) -> Optional[ResolvedIdentity]:
        with self._lock:
            ak = self._keys.get(key)
            if ak is None or not ak.active:
                return None
            return ResolvedIdentity(
                key=ak.key,
                tenant_id=ak.tenant_id,
                role=ak.role,
                user_id=ak.user_id,
            )

    def revoke(self, key: str) -> bool:
        with self._lock:
            ak = self._keys.get(key)
            if ak is None or not ak.active:
                return False
            ak.active = False
            return True

    def touch(self, key: str, when: str) -> None:
        with self._lock:
            ak = self._keys.get(key)
            if ak is not None:
                ak.last_used_at = when

    def list_keys(self, tenant_id: Optional[str] = None) -> List[ApiKey]:
        with self._lock:
            rows = list(self._keys.values())
            if tenant_id is not None:
                rows = [r for r in rows if r.tenant_id == tenant_id]
            return [replace(ak) for ak in rows]


class SQLiteIdentityStore:
    """基于 sqlite3 标准库的 Key 身份持久化后端（可选，零第三方依赖）。

    - ``dsn`` 为文件路径时 Key 映射落盘、重启不丢；传 ``:memory:`` 为进程内内存库。
    - 仅为本机单进程持久化骨架：不做账号鉴权、密码哈希、跨进程 / 网络共享；
      生产身份仍需对接外部身份服务（见 ``docs/DEPLOYMENT.md``）。
    - 行为口径与 :class:`InMemoryIdentityStore` 一致：停用 / 未知 Key 解析为 None，
      停用操作幂等，列表返回拷贝不回写内部状态。
    """

    def __init__(self, dsn: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(dsn, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key          TEXT PRIMARY KEY,
                    tenant_id    TEXT NOT NULL,
                    role         TEXT NOT NULL,
                    user_id      TEXT NOT NULL DEFAULT '',
                    active       INTEGER NOT NULL DEFAULT 1,
                    created_at   TEXT NOT NULL DEFAULT '',
                    last_used_at TEXT
                )
                """
            )

    def _row_to_key(self, row: sqlite3.Row) -> ApiKey:
        return ApiKey(
            key=row["key"],
            tenant_id=row["tenant_id"],
            role=row["role"],
            user_id=row["user_id"],
            active=bool(row["active"]),
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
        )

    def register_key(self, api_key: ApiKey) -> None:
        validate_role(api_key.role)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO api_keys "
                "(key, tenant_id, role, user_id, active, created_at, last_used_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    api_key.key, api_key.tenant_id, api_key.role, api_key.user_id,
                    1 if api_key.active else 0, api_key.created_at, api_key.last_used_at,
                ),
            )

    def resolve(self, key: str) -> Optional[ResolvedIdentity]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM api_keys WHERE key = ?", (key,)
            ).fetchone()
        if row is None or not row["active"]:
            return None
        return ResolvedIdentity(
            key=row["key"],
            tenant_id=row["tenant_id"],
            role=row["role"],
            user_id=row["user_id"],
        )

    def revoke(self, key: str) -> bool:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT active FROM api_keys WHERE key = ?", (key,)
            ).fetchone()
            if row is None or not row["active"]:
                return False
            self._conn.execute(
                "UPDATE api_keys SET active = 0 WHERE key = ?", (key,)
            )
            return True

    def touch(self, key: str, when: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE key = ?", (when, key)
            )

    def list_keys(self, tenant_id: Optional[str] = None) -> List[ApiKey]:
        with self._lock:
            if tenant_id is None:
                rows = self._conn.execute(
                    "SELECT * FROM api_keys ORDER BY key"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY key",
                    (tenant_id,),
                ).fetchall()
        return [self._row_to_key(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def identity_store_from_env(dsn: Optional[str] = None) -> IdentityStore:
    """按环境变量 ``LCG_IDENTITY_DSN`` 选择身份存储；未配置时返回进程内存实现。

    - 未配置 / 空：``InMemoryIdentityStore``（默认，重启清空）；
    - 文件路径 / ``:memory:``：``SQLiteIdentityStore`` 落盘或内存库。
    """
    raw = (dsn or os.environ.get("LCG_IDENTITY_DSN") or "").strip()
    if not raw:
        return InMemoryIdentityStore()
    return SQLiteIdentityStore(raw)


# --- RBAC action matrix (skeleton) -----------------------------------------
#
# 动作分级：
#   ``read``   扫描 / 查询规则等只读动作；
#   ``write``  改写 / 反馈等会产出建议或留痕的动作；
#   ``admin``  管理 Key / 租户等管理动作（当前工具集尚未暴露管理端点，预留）。
#
# 边界：角色动作矩阵为本地单进程骨架；不替代外部身份服务的鉴权与审计。
ACTION_READ = "read"
ACTION_WRITE = "write"
ACTION_ADMIN = "admin"
ACTIONS = (ACTION_READ, ACTION_WRITE, ACTION_ADMIN)

_ROLE_ACTIONS: Dict[str, frozenset] = {
    ROLE_VIEWER: frozenset({ACTION_READ}),
    ROLE_OPERATOR: frozenset({ACTION_READ, ACTION_WRITE}),
    ROLE_ADMIN: frozenset({ACTION_READ, ACTION_WRITE, ACTION_ADMIN}),
}

# MCP 工具名 → 所需动作；新增工具时必须在此登记，未登记工具拒绝放行。
TOOL_ACTIONS: Dict[str, str] = {
    "scan_text": ACTION_READ,
    "scan_livestream": ACTION_READ,
    "compliance_rules": ACTION_READ,
    "scan_smart": ACTION_READ,
    "safe_rewrite": ACTION_WRITE,
    "rewrite_smart": ACTION_WRITE,
}


def actions_for_role(role: str) -> frozenset:
    """返回角色被允许的动作集合；非法角色抛 ``ValueError``。"""
    validate_role(role)
    return _ROLE_ACTIONS[role]


def can(role: str, action: str) -> bool:
    """角色是否被允许执行某动作；非法动作 / 角色抛 ``ValueError``。"""
    if action not in ACTIONS:
        raise ValueError(f"unsupported action={action!r}, expected: {', '.join(ACTIONS)}")
    return action in actions_for_role(role)


def require_permission(role: str, action: str) -> None:
    """越权时抛 ``PermissionError``；放行不做任何事。``role`` 为空表示未启用鉴权。"""
    if not role:
        return
    if not can(role, action):
        raise PermissionError(f"role {role!r} is not allowed to {action}")


def action_for_tool(tool_name: str) -> str:
    """按 MCP 工具名取所需动作；未登记工具抛 ``ValueError``。"""
    try:
        return TOOL_ACTIONS[tool_name]
    except KeyError:
        raise ValueError(f"unknown tool={tool_name!r}") from None
