import asyncio
from pathlib import Path

import httpx
import pytest

from pskreporter_local.client import PskReporterClient, PskReporterUnavailable
from pskreporter_local.config import Settings
from pskreporter_local.models import QueryDirection, ReportQuery
from pskreporter_local.parser import InvalidPskXml

FIXTURES = Path(__file__).parent / "fixtures"


def test_client_sends_documented_query_parameters_for_each_direction() -> None:
    async def scenario() -> None:
        observed_requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            observed_requests.append(request)
            return httpx.Response(200, content=(FIXTURES / "empty.xml").read_bytes())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = PskReporterClient(
                http_client,
                Settings(app_contact="operator@example.test", report_limit=250),
            )
            hearing_me = await client.fetch(
                ReportQuery(
                    "KF6UFO",
                    3600,
                    QueryDirection.SENT_BY,
                )
            )
            i_hear = await client.fetch(
                ReportQuery(
                    "KF6UFO",
                    3600,
                    QueryDirection.RECV_BY,
                )
            )

        assert hearing_me.reports == ()
        assert i_hear.reports == ()
        assert hearing_me.xml_trace is not None
        assert hearing_me.xml_trace.direction == "sent_by"
        assert hearing_me.xml_trace.http_status == 200
        assert hearing_me.xml_trace.response_bytes > 0
        assert hearing_me.xml_trace.requested_report_limit == 250
        assert hearing_me.xml_trace.report_limit_reached is False
        assert "<receptionReports" in hearing_me.xml_trace.raw_xml
        assert len(observed_requests) == 2
        sender_params = observed_requests[0].url.params
        receiver_params = observed_requests[1].url.params
        assert sender_params["senderCallsign"] == "KF6UFO"
        assert "receiverCallsign" not in sender_params
        assert receiver_params["receiverCallsign"] == "KF6UFO"
        assert "senderCallsign" not in receiver_params
        params = sender_params
        assert params["flowStartSeconds"] == "-3600"
        assert params["rptlimit"] == "250"
        assert params["rronly"] == "1"
        assert params["noactive"] == "1"
        assert params["nolocator"] == "1"
        assert params["appcontact"] == "operator@example.test"
        assert observed_requests[0].headers["accept"] == "application/xml"

    asyncio.run(scenario())


def test_client_marks_a_filled_report_limit_as_truncated() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=(FIXTURES / "reports.xml").read_bytes(),
            )
        )
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = PskReporterClient(http_client, Settings(report_limit=2))
            parsed = await client.fetch(ReportQuery("KF6UFO", 3600))

        assert len(parsed.reports) == 2
        assert parsed.xml_trace is not None
        assert parsed.xml_trace.requested_report_limit == 2
        assert parsed.xml_trace.report_limit_reached is True

    asyncio.run(scenario())


def test_client_sends_editable_advanced_query_parameters() -> None:
    async def scenario() -> None:
        observed_request: httpx.Request | None = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal observed_request
            observed_request = request
            return httpx.Response(200, content=(FIXTURES / "empty.xml").read_bytes())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = PskReporterClient(http_client, Settings(report_limit=1000))
            parsed = await client.fetch(
                ReportQuery.normalized(
                    "KF6UFO",
                    900,
                    upstream_mode="ft8",
                    report_limit=75,
                    reception_reports_only=False,
                    exclude_active_monitors=False,
                    include_reports_without_locator=False,
                    frequency_range="28000000-29700000",
                    include_statistics=True,
                    modify="grid",
                    last_sequence_number=12345,
                )
            )

        assert observed_request is not None
        params = observed_request.url.params
        assert params["mode"] == "FT8"
        assert params["rptlimit"] == "75"
        assert params["rronly"] == "0"
        assert params["noactive"] == "0"
        assert params["nolocator"] == "0"
        assert params["frange"] == "28000000-29700000"
        assert params["statistics"] == "1"
        assert params["modify"] == "grid"
        assert params["lastseqno"] == "12345"
        assert parsed.xml_trace is not None
        assert parsed.xml_trace.requested_report_limit == 75

    asyncio.run(scenario())


def test_client_distinguishes_http_and_xml_failures() -> None:
    async def fetch_with(response: httpx.Response) -> None:
        transport = httpx.MockTransport(lambda _: response)
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = PskReporterClient(http_client, Settings())
            await client.fetch(ReportQuery("KF6UFO", 3600))

    with pytest.raises(PskReporterUnavailable):
        asyncio.run(fetch_with(httpx.Response(503)))

    with pytest.raises(InvalidPskXml):
        asyncio.run(
            fetch_with(httpx.Response(200, content=(FIXTURES / "malformed.xml").read_bytes()))
        )
