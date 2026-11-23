# -*- coding: utf-8 -*-
"""
lcg.tenant —— 租户配额与用量计量的**进程内骨架**（零第三方依赖）。

边界（重要）：
  · 本模块只是多租户 / 配额计费的**内存抽象骨架**：注册租户、扣减调用次数与 token、
    累计用量；**不做账号体系、不做登录鉴权、不持久化、不跨进程共享**，重启即清空。
  · 生产多租户需外置存储（数据库 / Redis）、API Key 签发与轮换、按租户隔离词库与
    审计数据，这些均未实现，演进方向见 ``docs/DEPLOYMENT.md``。
  · token 计量来自 LLM 层 usage 透传；纯规则调用 tokens 记 0。

配额口径：``quota_calls`` / ``quota_tokens`` 为 0 表示不限量；超出配额或租户停用
时 ``consume`` 返回 False，调用方应据此拒绝或降级，而不是在本模块内抛错中断服务。
"""
from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Protocol


@dataclass
class Tenant:
    id: str
    name: str
    plan: str = "free"
    quota_calls: int = 0      # 0 = 不限调用次数
    quota_tokens: int = 0     # 0 = 不限 token
    active: bool = True


@dataclass
class UsageRecord:
    calls: int = 0
    tokens: int = 0


class QuotaStore(Protocol):
    """配额存储协议；将来可替换为数据库 / Redis 实现。"""

    def register(self, tenant: Tenant) -> None: ...

    def get(self, tenant_id: str) -> Optional[Tenant]: ...

    def consume(self, tenant_id: str, calls: int, tokens: int) -> bool: ...

    def usage(self, tenant_id: str) -> UsageRecord: ...


class InMemoryQuotaStore:
    """进程内配额与用量存储（线程安全；重启清空，非持久化）。"""

    def __init__(self) -> None:
        self._tenants: Dict[str, Tenant] = {}
        self._usage: Dict[str, UsageRecord] = {}
        self._lock = threading.Lock()

    def register(self, tenant: Tenant) -> None:
        with self._lock:
            self._tenants[tenant.id] = tenant
            self._usage.setdefault(tenant.id, UsageRecord())

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def _within_quota(self, tenant: Tenant, usage: UsageRecord,
                      calls: int, tokens: int) -> bool:
        if tenant.quota_calls > 0 and usage.calls + calls > tenant.quota_calls:
            return False
        if tenant.quota_tokens > 0 and usage.tokens + tokens > tenant.quota_tokens:
            return False
        return True

    def consume(self, tenant_id: str, calls: int = 0, tokens: int = 0) -> bool:
        """扣减配额；成功返回 True，超额 / 停用 / 未注册返回 False（不抛异常）。"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None or not tenant.active:
                return False
            usage = self._usage.setdefault(tenant_id, UsageRecord())
            if not self._within_quota(tenant, usage, calls, tokens):
                return False
            usage.calls += calls
            usage.tokens += tokens
            return True

    def usage(self, tenant_id: str) -> UsageRecord:
        return self._usage.get(tenant_id, UsageRecord())

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        """返回各租户当前用量快照（供报表 / 计费对账骨架使用）。"""
        with self._lock:
            return {tid: {"calls": u.calls, "tokens": u.tokens}
                    for tid, u in self._usage.items()}


class UsageMeter:
    """按租户记录用量的薄封装；底层可替换为任意 QuotaStore 实现。"""

    def __init__(self, store: Optional[QuotaStore] = None) -> None:
        self.store: QuotaStore = store or InMemoryQuotaStore()

    def record(self, tenant_id: str, calls: int = 0, tokens: int = 0) -> bool:
        return self.store.consume(tenant_id, calls=calls, tokens=tokens)

    def check(self, tenant_id: str, calls: int = 1,
              tokens: int = 0) -> tuple[bool, str]:
        """放行前预检：未注册 / 停用 / 调用次数超额返回 ``(False, reason)``。

        - ``unknown_tenant``：Key 映射到的租户未在配额表注册；
        - ``tenant_disabled``：租户被停用；
        - ``quota_exceeded``：剩余调用次数不足；
        - ``token_exceeded``：预估 token 超出 token 配额（调用前未知时不传 ``tokens``）。

        token 在请求前通常不可知，HTTP 入口只按 calls 预检；token 属软计量——回填时
        超额只不累计，不阻断已放行请求。预检不扣减，扣减由 ``record`` 完成；存储异常
        不抛错，按放行处理（避免存储故障阻断全部流量），原因记为 ``store_error``。
        """
        try:
            tenant = self.store.get(tenant_id)
            if tenant is None:
                return False, "unknown_tenant"
            if not tenant.active:
                return False, "tenant_disabled"
            usage = self.store.usage(tenant_id)
            if tenant.quota_calls > 0 and usage.calls + calls > tenant.quota_calls:
                return False, "quota_exceeded"
            if tokens > 0 and tenant.quota_tokens > 0 \
                    and usage.tokens + tokens > tenant.quota_tokens:
                return False, "token_exceeded"
        except Exception:
            return True, "store_error"
        return True, "ok"

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        snap = getattr(self.store, "snapshot", None)
        return snap() if callable(snap) else {}


class SQLiteQuotaStore:
    """基于 sqlite3 标准库的配额 / 用量持久化后端（可选，零第三方依赖）。

    - ``dsn`` 为文件路径时用量落盘、重启不丢；传 ``:memory:`` 为进程内内存库。
    - 仅为本机单进程持久化骨架：不做账号鉴权、不做跨进程 / 网络共享；生产多租户
      仍需外置数据库、Key 签发与按租户隔离（见 ``docs/DEPLOYMENT.md``）。
    """

    def __init__(self, dsn: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(dsn, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id    TEXT PRIMARY KEY,
                    name         TEXT NOT NULL,
                    plan         TEXT NOT NULL DEFAULT 'free',
                    quota_calls  INTEGER NOT NULL DEFAULT 0,
                    quota_tokens INTEGER NOT NULL DEFAULT 0,
                    active       INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS usage (
                    tenant_id TEXT PRIMARY KEY,
                    calls     INTEGER NOT NULL DEFAULT 0,
                    tokens    INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def register(self, tenant: Tenant) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO tenants "
                "(tenant_id, name, plan, quota_calls, quota_tokens, active) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tenant.id, tenant.name, tenant.plan, tenant.quota_calls,
                 tenant.quota_tokens, 1 if tenant.active else 0),
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO usage (tenant_id, calls, tokens) "
                "VALUES (?, 0, 0)", (tenant.id,),
            )

    def _row_to_tenant(self, row: sqlite3.Row) -> Tenant:
        return Tenant(
            id=row["tenant_id"],
            name=row["name"],
            plan=row["plan"],
            quota_calls=row["quota_calls"],
            quota_tokens=row["quota_tokens"],
            active=bool(row["active"]),
        )

    def get(self, tenant_id: str) -> Optional[Tenant]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
        return self._row_to_tenant(row) if row else None

    def _usage_row(self, tenant_id: str) -> UsageRecord:
        row = self._conn.execute(
            "SELECT calls, tokens FROM usage WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        if row is None:
            return UsageRecord()
        return UsageRecord(calls=row["calls"], tokens=row["tokens"])

    def consume(self, tenant_id: str, calls: int = 0, tokens: int = 0) -> bool:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
            if row is None or not row["active"]:
                return False
            tenant = self._row_to_tenant(row)
            usage = self._usage_row(tenant_id)
            if tenant.quota_calls > 0 and usage.calls + calls > tenant.quota_calls:
                return False
            if tenant.quota_tokens > 0 and usage.tokens + tokens > tenant.quota_tokens:
                return False
            self._conn.execute(
                "INSERT INTO usage (tenant_id, calls, tokens) VALUES (?, ?, ?) "
                "ON CONFLICT(tenant_id) DO UPDATE SET "
                "calls = calls + excluded.calls, tokens = tokens + excluded.tokens",
                (tenant_id, calls, tokens),
            )
            return True

    def usage(self, tenant_id: str) -> UsageRecord:
        with self._lock:
            return self._usage_row(tenant_id)

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT tenant_id, calls, tokens FROM usage"
            ).fetchall()
        return {r["tenant_id"]: {"calls": r["calls"], "tokens": r["tokens"]}
                for r in rows}

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def quota_store_from_env(dsn: Optional[str] = None) -> QuotaStore:
    """按环境变量 ``LCG_STORE_DSN`` 选择配额存储；未配置时返回进程内存实现。

    - 未配置 / 空：``InMemoryQuotaStore``（默认，重启清空）；
    - 文件路径：``SQLiteQuotaStore`` 落盘持久化；
    - ``:memory:``：SQLite 内存库（进程内，不落文件）。
    """
    raw = (dsn or os.environ.get("LCG_STORE_DSN") or "").strip()
    if not raw:
        return InMemoryQuotaStore()
    return SQLiteQuotaStore(raw)
