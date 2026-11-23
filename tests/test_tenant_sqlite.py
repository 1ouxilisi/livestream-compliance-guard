# -*- coding: utf-8 -*-
"""SQLite 配额/用量持久化后端：配额口径与内存实现一致，且落盘重启不丢。"""
from lcg.tenant import (
    InMemoryQuotaStore,
    SQLiteQuotaStore,
    Tenant,
    quota_store_from_env,
)


def _register(store, **kw):
    store.register(Tenant(id="t1", name="一号", **kw))


def test_consume_success_and_accumulate(tmp_path):
    db = tmp_path / "q.db"
    store = SQLiteQuotaStore(str(db))
    _register(store, quota_calls=10, quota_tokens=1000)
    assert store.consume("t1", calls=2, tokens=300) is True
    usage = store.usage("t1")
    assert usage.calls == 2 and usage.tokens == 300
    store.close()


def test_consume_unknown_tenant_rejected():
    store = SQLiteQuotaStore(":memory:")
    assert store.consume("nope", calls=1) is False
    store.close()


def test_inactive_tenant_rejected(tmp_path):
    store = SQLiteQuotaStore(str(tmp_path / "i.db"))
    _register(store, active=False)
    assert store.consume("t1", calls=1) is False
    store.close()


def test_call_quota_exceeded(tmp_path):
    store = SQLiteQuotaStore(str(tmp_path / "c.db"))
    _register(store, quota_calls=2)
    assert store.consume("t1", calls=2) is True
    assert store.consume("t1", calls=1) is False
    store.close()


def test_token_quota_exceeded(tmp_path):
    store = SQLiteQuotaStore(str(tmp_path / "t.db"))
    _register(store, quota_tokens=500)
    assert store.consume("t1", calls=1, tokens=500) is True
    assert store.consume("t1", calls=1, tokens=1) is False
    store.close()


def test_zero_quota_means_unlimited(tmp_path):
    store = SQLiteQuotaStore(str(tmp_path / "u.db"))
    _register(store, quota_calls=0, quota_tokens=0)
    for _ in range(5):
        assert store.consume("t1", calls=1, tokens=100) is True
    assert store.usage("t1").calls == 5
    store.close()


def test_snapshot_per_tenant(tmp_path):
    store = SQLiteQuotaStore(str(tmp_path / "s.db"))
    _register(store)
    store.register(Tenant(id="t2", name="二号"))
    store.consume("t1", calls=3, tokens=120)
    store.consume("t2", calls=1, tokens=40)
    snap = store.snapshot()
    assert snap["t1"] == {"calls": 3, "tokens": 120}
    assert snap["t2"] == {"calls": 1, "tokens": 40}
    store.close()


def test_persists_across_reopen(tmp_path):
    db = str(tmp_path / "persist.db")
    first = SQLiteQuotaStore(db)
    _register(first, quota_calls=100, quota_tokens=10000)
    assert first.consume("t1", calls=4, tokens=260) is True
    first.close()

    # 重新打开同一文件：租户与已累计用量仍在
    second = SQLiteQuotaStore(db)
    assert second.get("t1") is not None
    usage = second.usage("t1")
    assert usage.calls == 4 and usage.tokens == 260
    assert second.consume("t1", calls=1, tokens=40) is True
    assert second.usage("t1").calls == 5
    second.close()


def test_factory_defaults_to_inmemory(monkeypatch):
    monkeypatch.delenv("LCG_STORE_DSN", raising=False)
    store = quota_store_from_env()
    assert isinstance(store, InMemoryQuotaStore)


def test_factory_builds_sqlite(tmp_path, monkeypatch):
    db = str(tmp_path / "factory.db")
    monkeypatch.setenv("LCG_STORE_DSN", db)
    store = quota_store_from_env()
    assert isinstance(store, SQLiteQuotaStore)
    store.register(Tenant(id="t1", name="一号"))
    assert store.consume("t1", calls=1) is True
    store.close()
