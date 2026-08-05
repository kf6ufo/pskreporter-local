from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .cache import AsyncTtlCache
from .client import PskReporterClient
from .models import ParsedReports, ReportQuery


@dataclass(frozen=True)
class FetchPayload:
    parsed: ParsedReports
    fetched_at: datetime


@dataclass(frozen=True)
class ReportsResult:
    payload: FetchPayload
    cache_hit: bool
    cache_expires_at: datetime


class ReportsService:
    def __init__(
        self,
        client: PskReporterClient,
        cache_ttl_seconds: int = 300,
        clock=None,
    ) -> None:
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cache: AsyncTtlCache[ReportQuery, FetchPayload] = AsyncTtlCache(
            cache_ttl_seconds,
            clock=self._clock,
        )

    async def get_reports(self, query: ReportQuery) -> ReportsResult:
        async def fetch() -> FetchPayload:
            parsed = await self._client.fetch(query)
            return FetchPayload(parsed=parsed, fetched_at=self._clock())

        cached = await self._cache.get_or_create(query, fetch)
        return ReportsResult(
            payload=cached.value,
            cache_hit=cached.hit,
            cache_expires_at=cached.expires_at,
        )
