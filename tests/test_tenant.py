# -*- coding: utf-8 -*-
"""租户配额与用量计量内存骨架：注册、扣减、超额拒绝、用量快照。"""
from lcg.tenant import InMemoryQuotaStore, Tenant, UsageMeter


def _store_with(tenant: Tenant) -> InMemoryQuotaStore:
    store = InMemoryQuotaStore()
    store.register(tenant)
    return store


def test_consume_success_and_accumulate():
    store = _store_with(Tenant(id="t1", name="一号", quota_calls=10, quota_tokens=1000))
    assert store.consume("t1", calls=2, tokens=300) is True
    usage = store.usage("t1")
    assert usage.calls == 2
    assert usage.tokens == 300


def test_consume_unknown_tenant_rejected():
    store = InMemoryQuotaStore()
    assert store.consume("nope", calls=1) is False


def test_inactive_tenant_rejected():
    store = _store_with(Tenant(id="t1", name="一号", active=False))
    assert store.consume("t1", calls=1) is False


def test_call_quota_exceeded():
    store = _store_with(Tenant(id="t1", name="一号", quota_calls=2))
    assert store.consume("t1", calls=2) is True
    assert store.consume("t1", calls=1) is False  # 2+1 > 2


def test_token_quota_exceeded():
    store = _store_with(Tenant(id="t1", name="一号", quota_tokens=500))
    assert store.consume("t1", calls=1, tokens=500) is True
    assert store.consume("t1", calls=1, tokens=1) is False


def test_zero_quota_means_unlimited():
    store = _store_with(Tenant(id="t1", name="一号", quota_calls=0, quota_tokens=0))
    for _ in range(5):
        assert store.consume("t1", calls=1, tokens=100) is True
    assert store.usage("t1").calls == 5


def test_snapshot_per_tenant():
    store = _store_with(Tenant(id="t1", name="一号"))
    store.register(Tenant(id="t2", name="二号"))
    store.consume("t1", calls=3, tokens=120)
    store.consume("t2", calls=1, tokens=40)
    snap = store.snapshot()
    assert snap["t1"] == {"calls": 3, "tokens": 120}
    assert snap["t2"] == {"calls": 1, "tokens": 40}


def test_usage_meter_record_and_snapshot():
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号"))
    assert meter.record("t1", calls=2, tokens=80) is True
    assert meter.snapshot()["t1"] == {"calls": 2, "tokens": 80}


def test_consume_never_raises_on_unknown():
    store = InMemoryQuotaStore()
    # 未注册 / 异常入参都应返回 False 而非抛错
    assert store.consume("ghost") is False


def test_meter_check_pass_for_active_within_quota():
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号", quota_calls=10))
    assert meter.check("t1", calls=1) == (True, "ok")


def test_meter_check_unknown_tenant():
    meter = UsageMeter()
    assert meter.check("ghost", calls=1) == (False, "unknown_tenant")


def test_meter_check_disabled_tenant():
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号", active=False))
    assert meter.check("t1", calls=1) == (False, "tenant_disabled")


def test_meter_check_exceeded_calls():
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号", quota_calls=2))
    assert meter.record("t1", calls=2) is True
    assert meter.check("t1", calls=1) == (False, "quota_exceeded")


def test_meter_check_exceeded_tokens():
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号", quota_tokens=100))
    assert meter.record("t1", calls=1, tokens=100) is True
    assert meter.check("t1", calls=1, tokens=1) == (False, "token_exceeded")


def test_meter_check_tokens_zero_means_unlimited():
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号", quota_tokens=0))
    assert meter.check("t1", calls=1, tokens=99999) == (True, "ok")
