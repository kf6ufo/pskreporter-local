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
