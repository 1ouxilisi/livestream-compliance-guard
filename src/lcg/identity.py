# -*- coding: utf-8 -*-
"""lcg.identity: account / role / API Key in-memory identity skeleton.

Boundary:
  * Key -> tenant / role / operator in-memory mapping only; no password hash,
    no login/register UI, no persistence, no cross-process sharing.
  * Production identity must implement ``IdentityStore`` against an external
    identity service; see docs/DEPLOYMENT.md.
  * Role is a label carried to audit trails; role-based endpoint gating is not
    implemented in this round.
"""
from __future__ import annotations

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
