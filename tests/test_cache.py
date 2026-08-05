import asyncio
from datetime import UTC, datetime, timedelta

from pskreporter_local.cache import AsyncTtlCache


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 5, 18, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def test_cache_reuses_value_for_at_least_five_minutes() -> None:
    async def scenario() -> None:
        clock = FakeClock()
        cache: AsyncTtlCache[str, int] = AsyncTtlCache(300, clock=clock)
        calls = 0

        async def factory() -> int:
            nonlocal calls
            calls += 1
            return calls

        first = await cache.get_or_create("KF6UFO:3600", factory)
        clock.now += timedelta(seconds=299)
        second = await cache.get_or_create("KF6UFO:3600", factory)
        clock.now += timedelta(seconds=2)
        third = await cache.get_or_create("KF6UFO:3600", factory)

        assert first.value == 1
        assert first.hit is False
        assert second.value == 1
        assert second.hit is True
        assert third.value == 2
        assert third.hit is False
        assert calls == 2

    asyncio.run(scenario())


def test_cache_rejects_shorter_ttl() -> None:
    try:
        AsyncTtlCache[str, int](299)
    except ValueError as exc:
        assert "five minutes" in str(exc)
    else:
        raise AssertionError("A cache shorter than five minutes was accepted")
