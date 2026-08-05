from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    query_url: str = "https://retrieve.pskreporter.info/query"
    cache_ttl_seconds: int = 300
    report_limit: int = 1000
    http_timeout_seconds: float = 10.0
    max_xml_bytes: int = 5_000_000
    app_contact: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            query_url=os.getenv("PSKR_QUERY_URL", cls.query_url),
            cache_ttl_seconds=max(
                300, int(os.getenv("PSKR_CACHE_TTL_SECONDS", "300"))
            ),
            report_limit=max(1, int(os.getenv("PSKR_REPORT_LIMIT", "1000"))),
            http_timeout_seconds=max(
                1.0, float(os.getenv("PSKR_HTTP_TIMEOUT_SECONDS", "10"))
            ),
            max_xml_bytes=max(
                1024, int(os.getenv("PSKR_MAX_XML_BYTES", "5000000"))
            ),
            app_contact=os.getenv("PSKR_APP_CONTACT") or None,
        )
