from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum

CALLSIGN_PATTERN = re.compile(r"^[A-Z0-9]+(?:/[A-Z0-9]+)*$")


class InvalidQuery(ValueError):
    """The requested report query is invalid."""


class QueryDirection(StrEnum):
    RECV_BY = "recv_by"
    SENT_BY = "sent_by"

    @property
    def api_parameter(self) -> str:
        if self is QueryDirection.RECV_BY:
            return "receiverCallsign"
        return "senderCallsign"


@dataclass(frozen=True)
class ReportQuery:
    callsign: str
    lookback_seconds: int = 3600
    direction: QueryDirection = QueryDirection.SENT_BY

    @classmethod
    def normalized(
        cls,
        callsign: str,
        lookback_seconds: int,
        direction: QueryDirection = QueryDirection.SENT_BY,
    ) -> "ReportQuery":
        call = callsign.strip().upper()
        if not 3 <= len(call) <= 20 or not CALLSIGN_PATTERN.fullmatch(call):
            raise InvalidQuery(
                "Callsign must be 3-20 letters, digits, or slash-separated parts."
            )
        if not 60 <= lookback_seconds <= 86_400:
            raise InvalidQuery("Lookback must be between 60 and 86400 seconds.")
        return cls(callsign=call, lookback_seconds=lookback_seconds, direction=direction)


@dataclass(frozen=True)
class ReceptionReport:
    spot_time_utc: str
    sender_call: str
    receiver_call: str
    sender_locator: str | None
    receiver_locator: str | None
    receiver_latitude: float | None
    receiver_longitude: float | None
    frequency_hz: int
    band: str | None
    mode: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class XmlTrace:
    direction: str
    request_url: str
    http_status: int | None
    elapsed_ms: int
    response_bytes: int
    raw_xml: str
    raw_xml_truncated: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedReports:
    reports: tuple[ReceptionReport, ...]
    warnings: tuple[str, ...] = ()
    xml_trace: XmlTrace | None = None
