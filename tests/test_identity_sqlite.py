# -*- coding: utf-8 -*-
"""SQLite 身份持久化后端：口径与内存实现一致，且落盘重启不丢。"""
import pytest

from lcg.identity import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ApiKey,
    InMemoryIdentityStore,
    SQLiteIdentityStore,
    identity_store_from_env,
)


def _key(key: str = "sk-test", tenant_id: str = "t1",
         role: str = ROLE_OPERATOR, user_id: str = "u1") -> ApiKey:
    return ApiKey(key=key, tenant_id=tenant_id, role=role, user_id=user_id)


def test_register_and_resolve(tmp_path):
    store = SQLiteIdentityStore(str(tmp_path / "id.db"))
    store.register_key(_key(key="k1", tenant_id="t1",
                            role=ROLE_ADMIN, user_id="u9"))
    ident = store.resolve("k1")
    assert ident is not None
    assert ident.tenant_id == "t1"
    assert ident.role == ROLE_ADMIN
    assert ident.user_id == "u9"
    store.close()


def test_resolve_unknown_returns_none():
    store = SQLiteIdentityStore(":memory:")
    assert store.resolve("ghost") is None
    store.close()


def test_revoke_deactivates_and_is_idempotent(tmp_path):
    store = SQLiteIdentityStore(str(tmp_path / "r.db"))
    store.register_key(_key())
    assert store.revoke("sk-test") is True
    assert store.resolve("sk-test") is None
    assert store.revoke("sk-test") is False
    assert store.revoke("ghost") is False
    store.close()


def test_touch_updates_last_used(tmp_path):
    store = SQLiteIdentityStore(str(tmp_path / "t.db"))
    store.register_key(_key())
    store.touch("sk-test", "2026-11-23T12:00:00Z")
    rows = store.list_keys()
    assert rows[0].last_used_at == "2026-11-23T12:00:00Z"
    store.touch("ghost", "2026-11-23T12:00:00Z")
    store.close()


def test_list_keys_filter_by_tenant_and_returns_copy(tmp_path):
    store = SQLiteIdentityStore(str(tmp_path / "l.db"))
    store.register_key(_key(key="k1", tenant_id="t1"))
    store.register_key(_key(key="k2", tenant_id="t2"))
    store.register_key(_key(key="k3", tenant_id="t1"))

    assert len(store.list_keys()) == 3
    t1 = store.list_keys("t1")
    assert {r.key for r in t1} == {"k1", "k3"}

    # 返回的是拷贝：外部改动不回写内部状态
    t1[0].active = False
    assert store.resolve(t1[0].key) is not None
    store.close()


def test_register_rejects_unknown_role():
    store = SQLiteIdentityStore(":memory:")
    with pytest.raises(ValueError):
        store.register_key(_key(role="superuser"))
    store.close()


def test_persists_across_reopen(tmp_path):
    db = str(tmp_path / "persist.db")
    first = SQLiteIdentityStore(db)
    first.register_key(_key(key="k1", tenant_id="t1", role=ROLE_ADMIN))
    first.touch("k1", "2026-11-23T12:00:00Z")
    first.close()

    second = SQLiteIdentityStore(db)
    ident = second.resolve("k1")
    assert ident is not None and ident.tenant_id == "t1"
    rows = second.list_keys()
    assert rows[0].last_used_at == "2026-11-23T12:00:00Z"
    second.close()


def test_factory_defaults_to_inmemory(monkeypatch):
    monkeypatch.delenv("LCG_IDENTITY_DSN", raising=False)
    store = identity_store_from_env()
    assert isinstance(store, InMemoryIdentityStore)


def test_factory_builds_sqlite(tmp_path, monkeypatch):
    db = str(tmp_path / "factory.db")
    monkeypatch.setenv("LCG_IDENTITY_DSN", db)
    store = identity_store_from_env()
    assert isinstance(store, SQLiteIdentityStore)
    store.register_key(_key())
    assert store.resolve("sk-test") is not None
    store.close()
