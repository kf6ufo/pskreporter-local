from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import httpx

from .config import Settings
from .models import ParsedReports, ReportQuery, XmlTrace
from .parser import InvalidPskXml, parse_reception_reports

MAX_TRACE_XML_CHARS = 200_000


class PskReporterUnavailable(RuntimeError):
    """The PSK Reporter service could not provide a usable HTTP response."""

    def __init__(self, message: str, xml_trace: XmlTrace | None = None) -> None:
        super().__init__(message)
        self.xml_trace = xml_trace


class PskReporterClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings

    async def fetch(self, query: ReportQuery) -> ParsedReports:
        report_limit = query.report_limit or self._settings.report_limit
        params: dict[str, str | int] = {
            query.direction.api_parameter: query.callsign,
            "flowStartSeconds": -query.lookback_seconds,
            "rptlimit": report_limit,
            "rronly": int(query.reception_reports_only),
            "noactive": int(query.exclude_active_monitors),
            "nolocator": int(query.include_reports_without_locator),
        }
        if query.upstream_mode:
            params["mode"] = query.upstream_mode
        if query.frequency_range:
            params["frange"] = query.frequency_range
        if query.include_statistics:
            params["statistics"] = 1
        if query.modify_grid:
            params["modify"] = "grid"
        if query.last_sequence_number is not None:
            params["lastseqno"] = query.last_sequence_number
        if self._settings.app_contact:
            params["appcontact"] = self._settings.app_contact

        display_params = {
            key: "[redacted]" if key == "appcontact" else value
            for key, value in params.items()
        }
        safe_request_url = str(
            httpx.URL(self._settings.query_url, params=display_params)
        )
        started = perf_counter()
        try:
            response = await self._http_client.get(
                self._settings.query_url,
                params=params,
                headers={
                    "Accept": "application/xml",
                    "User-Agent": "pskreporter-local/0.1.0",
                },
                timeout=httpx.Timeout(
                    self._settings.http_timeout_seconds,
                    connect=min(3.0, self._settings.http_timeout_seconds),
                ),
            )
        except httpx.RequestError as exc:
            trace = XmlTrace(
                direction=query.direction.value,
                request_url=safe_request_url,
                http_status=None,
                elapsed_ms=round((perf_counter() - started) * 1000),
                response_bytes=0,
                raw_xml="",
                requested_report_limit=report_limit,
                error=exc.__class__.__name__,
            )
            raise PskReporterUnavailable(
                "PSK Reporter is unavailable or returned a network error.",
                xml_trace=trace,
            ) from exc

        raw_xml = response.content.decode("utf-8", errors="replace")
        trace = XmlTrace(
            direction=query.direction.value,
            request_url=safe_request_url,
            http_status=response.status_code,
            elapsed_ms=round((perf_counter() - started) * 1000),
            response_bytes=len(response.content),
            raw_xml=raw_xml[:MAX_TRACE_XML_CHARS],
            raw_xml_truncated=len(raw_xml) > MAX_TRACE_XML_CHARS,
            requested_report_limit=report_limit,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_trace = XmlTrace(
                **{
                    **trace.to_dict(),
                    "error": f"HTTP {response.status_code}",
                }
            )
            raise PskReporterUnavailable(
                "PSK Reporter is unavailable or returned an HTTP error.",
                xml_trace=error_trace,
            ) from exc

        if len(response.content) > self._settings.max_xml_bytes:
            raise InvalidPskXml(
                "The XML response exceeded the configured size limit.",
                xml_trace=trace,
            )
        try:
            parsed = parse_reception_reports(response.content)
        except InvalidPskXml as exc:
            raise InvalidPskXml(str(exc), xml_trace=trace) from exc
        trace = replace(
            trace,
            report_limit_reached=len(parsed.reports) >= report_limit,
        )
        return ParsedReports(
            reports=parsed.reports,
            warnings=parsed.warnings,
            xml_trace=trace,
        )
