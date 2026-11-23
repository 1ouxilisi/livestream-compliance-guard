# -*- coding: utf-8 -*-
"""Cache protocol and in-memory implementation: hit, miss, delete, keys, clear, TTL."""
import time

from lcg.cache import CacheStore, InMemoryCache


def test_set_get_hit():
    cache = InMemoryCache()
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}


def test_get_miss_returns_none():
    cache = InMemoryCache()
    assert cache.get("ghost") is None


def test_delete():
    cache = InMemoryCache()
    cache.set("k", 1)
    cache.delete("k")
    assert cache.get("k") is None
    cache.delete("ghost")


def test_keys_and_clear():
    cache = InMemoryCache()
    cache.set("a", 1)
    cache.set("b", 2)
    assert sorted(cache.keys()) == ["a", "b"]
    cache.clear()
    assert cache.keys() == []


def test_expired_entry_evicted_on_get():
    cache = InMemoryCache()
    cache.set("k", 1, ttl=1)
    cache._items["k"] = (1, time.time() - 1)
    assert cache.get("k") is None
    assert "k" not in cache.keys()


def test_no_ttl_entry_never_expires():
    cache = InMemoryCache()
    cache.set("k", 1, ttl=None)
    cache._items["k"] = (1, None)
    assert cache.get("k") == 1


def test_in_memory_cache_satisfies_protocol():
    cache: CacheStore = InMemoryCache()
    cache.set("k", "x")
    assert cache.get("k") == "x"
    assert "k" in cache.keys()
    cache.delete("k")
    cache.clear()
