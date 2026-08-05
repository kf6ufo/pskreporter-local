from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, TypeVar

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


@dataclass(frozen=True)
class CacheResult(Generic[ValueT]):
    value: ValueT
    hit: bool
    expires_at: datetime


@dataclass(frozen=True)
class _CacheEntry(Generic[ValueT]):
    value: ValueT
    expires_at: datetime


class AsyncTtlCache(Generic[KeyT, ValueT]):
    def __init__(
        self,
        ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl_seconds < 300:
            raise ValueError("PSK Reporter cache TTL must be at least five minutes.")
        self._ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._entries: dict[KeyT, _CacheEntry[ValueT]] = {}
        self._locks: dict[KeyT, asyncio.Lock] = {}

    async def get_or_create(
        self,
        key: KeyT,
        factory: Callable[[], Awaitable[ValueT]],
    ) -> CacheResult[ValueT]:
        now = self._clock()
        entry = self._entries.get(key)
        if entry is not None and entry.expires_at > now:
            return CacheResult(entry.value, True, entry.expires_at)

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = self._clock()
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                return CacheResult(entry.value, True, entry.expires_at)

            value = await factory()
            expires_at = self._clock() + self._ttl
            self._entries[key] = _CacheEntry(value, expires_at)
            return CacheResult(value, False, expires_at)
