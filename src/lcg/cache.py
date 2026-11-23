# -*- coding: utf-8 -*-
"""lcg.cache: swappable cache protocol and in-memory cache."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class CacheStore(Protocol):
    def get(self, key: str) -> Optional[Any]: ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...

    def delete(self, key: str) -> None: ...

    def keys(self) -> List[str]: ...

    def clear(self) -> None: ...


class InMemoryCache:
    """Process-local cache with optional TTL; expired entries are evicted lazily."""

    def __init__(self) -> None:
        self._items: Dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _expires_at(ttl: Optional[int]) -> Optional[float]:
        if ttl is None or ttl <= 0:
            return None
        return time.time() + ttl

    @staticmethod
    def _is_expired(expires_at: Optional[float], now: float) -> bool:
        return expires_at is not None and now >= expires_at

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if self._is_expired(expires_at, time.time()):
                del self._items[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._items[key] = (value, self._expires_at(ttl))

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def keys(self) -> List[str]:
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._items.items()
                       if self._is_expired(exp, now)]
            for k in expired:
                del self._items[k]
            return list(self._items.keys())

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
