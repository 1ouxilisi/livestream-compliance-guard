# -*- coding: utf-8 -*-
"""账号 / 角色 / API Key 内存身份骨架：登记、解析、停用、最近使用、租户过滤。"""
import pytest

from lcg.identity import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ApiKey,
    InMemoryIdentityStore,
)


def _key(key: str = "sk-test", tenant_id: str = "t1",
         role: str = ROLE_OPERATOR, user_id: str = "u1") -> ApiKey:
    return ApiKey(key=key, tenant_id=tenant_id, role=role, user_id=user_id)


def test_register_and_resolve_identity():
    store = InMemoryIdentityStore()
    store.register_key(_key(key="k1", tenant_id="t1",
                            role=ROLE_ADMIN, user_id="u9"))
    ident = store.resolve("k1")
    assert ident is not None
    assert ident.tenant_id == "t1"
    assert ident.role == ROLE_ADMIN
    assert ident.user_id == "u9"


def test_resolve_unknown_returns_none():
    store = InMemoryIdentityStore()
    assert store.resolve("ghost") is None


def test_revoke_deactivates_and_is_idempotent():
    store = InMemoryIdentityStore()
    store.register_key(_key())
    assert store.revoke("sk-test") is True
    assert store.resolve("sk-test") is None
    assert store.revoke("sk-test") is False
    assert store.revoke("ghost") is False


def test_touch_updates_last_used():
    store = InMemoryIdentityStore()
    store.register_key(_key())
    store.touch("sk-test", "2026-11-23T12:00:00Z")
    rows = store.list_keys()
    assert rows[0].last_used_at == "2026-11-23T12:00:00Z"
    store.touch("ghost", "2026-11-23T12:00:00Z")


def test_list_keys_filter_by_tenant_and_returns_copy():
    store = InMemoryIdentityStore()
    store.register_key(_key(key="k1", tenant_id="t1"))
    store.register_key(_key(key="k2", tenant_id="t2"))
    store.register_key(_key(key="k3", tenant_id="t1"))

    assert len(store.list_keys()) == 3
    t1 = store.list_keys("t1")
    assert {r.key for r in t1} == {"k1", "k3"}

    t1[0].active = False
    assert store.resolve(t1[0].key) is not None


def test_register_rejects_unknown_role():
    store = InMemoryIdentityStore()
    with pytest.raises(ValueError):
        store.register_key(_key(role="superuser"))
