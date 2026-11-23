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

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        if isinstance(self.store, InMemoryQuotaStore):
            return self.store.snapshot()
        return {}
