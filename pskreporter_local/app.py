from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .client import PskReporterClient, PskReporterUnavailable
from .config import Settings
from .models import InvalidQuery, QueryDirection, ReportQuery
from .parser import InvalidPskXml
from .service import ReportsResult, ReportsService

STATIC_DIR = Path(__file__).parent / "static"


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _result_trace(query: ReportQuery, result: ReportsResult) -> dict[str, object]:
    trace = result.payload.parsed.xml_trace
    entry = trace.to_dict() if trace is not None else {
        "direction": query.direction.value,
        "request_url": None,
        "http_status": None,
        "elapsed_ms": None,
        "response_bytes": None,
        "raw_xml": "",
        "raw_xml_truncated": False,
        "requested_report_limit": None,
        "report_limit_reached": False,
        "error": None,
    }
    entry.update(
        {
            "cache_hit": result.cache_hit,
            "fetched_at_utc": _utc_text(result.payload.fetched_at),
            "lookback_seconds": query.lookback_seconds,
            "parsed_report_count": len(result.payload.parsed.reports),
        }
    )
    return entry


def _error_trace(error: Exception) -> list[dict[str, object]]:
    trace = getattr(error, "xml_trace", None)
    return [trace.to_dict()] if trace is not None else []


def create_app(
    reports_service: ReportsService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_file()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if reports_service is not None:
            application.state.reports_service = reports_service
            yield
            return

        async with httpx.AsyncClient(follow_redirects=False) as http_client:
            client = PskReporterClient(http_client, resolved_settings)
            application.state.reports_service = ReportsService(
                client,
                cache_ttl_seconds=resolved_settings.cache_ttl_seconds,
            )
            yield

    application = FastAPI(
        title="pskreporter-local",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
    )
    application.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "pskreporter-local",
            "version": __version__,
        }

    @application.get("/api/config", include_in_schema=False)
    async def browser_config() -> dict[str, object]:
        return {
            "default_callsign": resolved_settings.default_callsign,
            "report_limit": resolved_settings.report_limit,
        }

    @application.get("/api/reports")
    async def reports(
        request: Request,
        callsign: str = Query(min_length=3, max_length=20),
        lookback_seconds: int = Query(default=900, ge=900, le=3600),
        sent_by: bool = Query(default=True),
        recv_by: bool = Query(default=False),
        band: str | None = Query(default=None, max_length=12),
        mode: str | None = Query(default=None, max_length=20),
        upstream_mode: str | None = Query(default=None, max_length=20),
        rptlimit: int | None = Query(default=None, ge=1, le=10_000),
        rronly: bool = Query(default=True),
        noactive: bool = Query(default=True),
        nolocator: bool = Query(default=True),
        frange: str | None = Query(default=None, max_length=32),
        statistics: bool = Query(default=False),
        modify: str | None = Query(default=None, max_length=12),
        lastseqno: int | None = Query(default=None, ge=0),
    ) -> JSONResponse:
        directions: list[QueryDirection] = []
        if sent_by:
            directions.append(QueryDirection.SENT_BY)
        if recv_by:
            directions.append(QueryDirection.RECV_BY)
        if not directions:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "invalid_query",
                    "message": "Select Sent by, Recv by, or both.",
                    "reports": [],
                    "xml_trace": [],
                },
            )

        try:
            queries = [
                ReportQuery.normalized(
                    callsign,
                    lookback_seconds,
                    direction,
                    upstream_mode=upstream_mode,
                    report_limit=rptlimit or resolved_settings.report_limit,
                    reception_reports_only=rronly,
                    exclude_active_monitors=noactive,
                    include_reports_without_locator=nolocator,
                    frequency_range=frange,
                    include_statistics=statistics,
                    modify=modify,
                    last_sequence_number=lastseqno,
                )
                for direction in directions
            ]
        except InvalidQuery as exc:
            return JSONResponse(
                status_code=422,
                content={"status": "invalid_query", "message": str(exc), "reports": []},
            )

        service: ReportsService = request.app.state.reports_service
        try:
            results = await asyncio.gather(
                *(service.get_reports(query) for query in queries)
            )
        except PskReporterUnavailable as exc:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "upstream_unavailable",
                    "message": str(exc),
                    "reports": [],
                    "xml_trace": _error_trace(exc),
                },
            )
        except InvalidPskXml as exc:
            return JSONResponse(
                status_code=502,
                content={
                    "status": "invalid_upstream_xml",
                    "message": str(exc),
                    "reports": [],
                    "xml_trace": _error_trace(exc),
                },
            )

        normalized_band = band.strip().lower() if band else None
        normalized_mode = mode.strip().upper() if mode else None
        merged: dict[tuple[object, ...], dict[str, object]] = {}
        warnings: list[str] = []
        truncated = False
        for query, result in zip(queries, results, strict=True):
            warnings.extend(
                f"{query.direction.value}: {warning}"
                for warning in result.payload.parsed.warnings
            )
            trace = result.payload.parsed.xml_trace
            if trace is not None and trace.report_limit_reached:
                truncated = True
                report_limit = trace.requested_report_limit or len(
                    result.payload.parsed.reports
                )
                warnings.append(
                    f"{query.direction.value}: PSK Reporter returned the configured "
                    f"{report_limit:,}-report limit. The selected "
                    "lookback may be incomplete; increase rptlimit in Advanced query "
                    "options (or its report_limit default in config.json) if needed."
                )
            for report in result.payload.parsed.reports:
                identity = (
                    report.spot_time_utc,
                    report.sender_call,
                    report.receiver_call,
                    report.frequency_hz,
                    report.mode,
                )
                if identity not in merged:
                    merged[identity] = {
                        **report.to_dict(),
                        "directions": [query.direction.value],
                    }
                else:
                    report_directions = merged[identity]["directions"]
                    if (
                        isinstance(report_directions, list)
                        and query.direction.value not in report_directions
                    ):
                        report_directions.append(query.direction.value)

        filtered = [
            report
            for report in merged.values()
            if (normalized_band is None or report["band"] == normalized_band)
            and (normalized_mode is None or report["mode"] == normalized_mode)
        ]
        filtered.sort(key=lambda report: str(report["spot_time_utc"]), reverse=True)
        oldest_report_utc = min(
            (str(report["spot_time_utc"]) for report in merged.values()),
            default=None,
        )
        status = "ok" if filtered else "empty"
        cache_hits = [result.cache_hit for result in results]
        cache_status = (
            "cached"
            if all(cache_hits)
            else "mixed"
            if any(cache_hits)
            else "live"
        )
        fetched_at = max(result.payload.fetched_at for result in results)
        cache_expires_at = min(result.cache_expires_at for result in results)
        xml_trace = [
            _result_trace(query, result)
            for query, result in zip(queries, results, strict=True)
        ]
        return JSONResponse(
            content={
                "status": status,
                "query": {
                    "callsign": queries[0].callsign,
                    "lookback_seconds": queries[0].lookback_seconds,
                    "directions": [direction.value for direction in directions],
                    "band": normalized_band,
                    "mode": normalized_mode,
                    "upstream_mode": queries[0].upstream_mode,
                    "rptlimit": queries[0].report_limit,
                    "rronly": queries[0].reception_reports_only,
                    "noactive": queries[0].exclude_active_monitors,
                    "nolocator": queries[0].include_reports_without_locator,
                    "frange": queries[0].frequency_range,
                    "statistics": queries[0].include_statistics,
                    "modify": "grid" if queries[0].modify_grid else None,
                    "lastseqno": queries[0].last_sequence_number,
                },
                "reports": filtered,
                "report_count": len(filtered),
                "oldest_report_utc": oldest_report_utc,
                "truncated": truncated,
                "fetched_at_utc": _utc_text(fetched_at),
                "cache_hit": all(cache_hits),
                "cache_status": cache_status,
                "cache_expires_at_utc": _utc_text(cache_expires_at),
                "warnings": warnings,
                "xml_trace": xml_trace,
            }
        )

    return application


app = create_app()
