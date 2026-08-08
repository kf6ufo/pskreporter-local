from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum

CALLSIGN_PATTERN = re.compile(r"^[A-Z0-9]+(?:/[A-Z0-9]+)*$")
FREQUENCY_RANGE_PATTERN = re.compile(r"^(\d+)-(\d+)$")
SUPPORTED_LOOKBACK_SECONDS = frozenset({900, 1800, 3600})


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
    lookback_seconds: int = 900
    direction: QueryDirection = QueryDirection.SENT_BY
    upstream_mode: str | None = None
    report_limit: int | None = None
    reception_reports_only: bool = True
    exclude_active_monitors: bool = True
    include_reports_without_locator: bool = True
    frequency_range: str | None = None
    include_statistics: bool = False
    modify_grid: bool = False
    last_sequence_number: int | None = None

    @classmethod
    def normalized(
        cls,
        callsign: str,
        lookback_seconds: int,
        direction: QueryDirection = QueryDirection.SENT_BY,
        *,
        upstream_mode: str | None = None,
        report_limit: int | None = None,
        reception_reports_only: bool = True,
        exclude_active_monitors: bool = True,
        include_reports_without_locator: bool = True,
        frequency_range: str | None = None,
        include_statistics: bool = False,
        modify: str | None = None,
        last_sequence_number: int | None = None,
    ) -> "ReportQuery":
        call = callsign.strip().upper()
        if not 3 <= len(call) <= 20 or not CALLSIGN_PATTERN.fullmatch(call):
            raise InvalidQuery(
                "Callsign must be 3-20 letters, digits, or slash-separated parts."
            )
        if lookback_seconds not in SUPPORTED_LOOKBACK_SECONDS:
            raise InvalidQuery("Lookback must be 900, 1800, or 3600 seconds.")
        normalized_mode = upstream_mode.strip().upper() if upstream_mode else None
        if normalized_mode and len(normalized_mode) > 20:
            raise InvalidQuery("Upstream mode must be 20 characters or fewer.")
        if report_limit is not None and not 1 <= report_limit <= 10_000:
            raise InvalidQuery("Report limit must be between 1 and 10,000.")

        normalized_range = frequency_range.strip() if frequency_range else None
        if normalized_range:
            match = FREQUENCY_RANGE_PATTERN.fullmatch(normalized_range)
            if match is None or int(match.group(1)) > int(match.group(2)):
                raise InvalidQuery(
                    "Frequency range must be lowerHz-upperHz, with the lower value first."
                )
        normalized_modify = modify.strip().lower() if modify else None
        if normalized_modify not in {None, "grid"}:
            raise InvalidQuery("Modify must be empty or grid.")
        if last_sequence_number is not None and last_sequence_number < 0:
            raise InvalidQuery("Last sequence number cannot be negative.")

        return cls(
            callsign=call,
            lookback_seconds=lookback_seconds,
            direction=direction,
            upstream_mode=normalized_mode,
            report_limit=report_limit,
            reception_reports_only=reception_reports_only,
            exclude_active_monitors=exclude_active_monitors,
            include_reports_without_locator=include_reports_without_locator,
            frequency_range=normalized_range,
            include_statistics=include_statistics,
            modify_grid=normalized_modify == "grid",
            last_sequence_number=last_sequence_number,
        )


@dataclass(frozen=True)
class ReceptionReport:
    spot_time_utc: str
    sender_call: str
    receiver_call: str
    sender_locator: str | None
    receiver_locator: str | None
    sender_region: str | None
    sender_dxcc: str | None
    receiver_latitude: float | None
    receiver_longitude: float | None
    frequency_hz: int
    snr_db: int | None
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
    requested_report_limit: int | None = None
    report_limit_reached: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedReports:
    reports: tuple[ReceptionReport, ...]
    warnings: tuple[str, ...] = ()
    xml_trace: XmlTrace | None = None
