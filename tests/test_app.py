from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from pskreporter_local.app import create_app
from pskreporter_local.models import ParsedReports, QueryDirection
from pskreporter_local.parser import parse_reception_reports
from pskreporter_local.service import ReportsService

FIXTURES = Path(__file__).parent / "fixtures"


class LookbackOptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_lookback = False
        self.current_value: str | None = None
        self.options: list[tuple[str, str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "select" and attributes.get("id") == "lookback":
            self.in_lookback = True
        elif tag == "option" and self.in_lookback:
            self.current_value = attributes.get("value")
            self.options.append(
                (self.current_value or "", "", "selected" in attributes)
            )

    def handle_data(self, data: str) -> None:
        if self.in_lookback and self.current_value is not None and data.strip():
            value, _, selected = self.options[-1]
            self.options[-1] = (value, data.strip(), selected)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option":
            self.current_value = None
        elif tag == "select" and self.in_lookback:
            self.in_lookback = False


class FakePskClient:
    def __init__(self, parsed: ParsedReports) -> None:
        self.parsed = parsed
        self.queries = []

    async def fetch(self, query):
        self.queries.append(query)
        return self.parsed

    @property
    def calls(self) -> int:
        return len(self.queries)


def build_client(parsed: ParsedReports) -> tuple[TestClient, FakePskClient]:
    fake = FakePskClient(parsed)
    clock = lambda: datetime(2026, 8, 5, 18, 0, tzinfo=UTC)
    service = ReportsService(fake, cache_ttl_seconds=300, clock=clock)
    return TestClient(create_app(reports_service=service)), fake


def test_health_and_home_page() -> None:
    client, _ = build_client(ParsedReports(()))
    with client:
        health = client.get("/api/health")
        home = client.get("/")
        stylesheet = client.get("/assets/styles.css")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert home.status_code == 200
    assert "PSK Reporter" in home.text
    assert stylesheet.status_code == 200


def test_lookback_options_match_psk_reporter() -> None:
    client, _ = build_client(ParsedReports(()))
    with client:
        home = client.get("/")

    parser = LookbackOptionParser()
    parser.feed(home.text)
    assert parser.options == [
        ("86400", "24 hours", False),
        ("43200", "12 hours", False),
        ("21600", "6 hours", False),
        ("10800", "3 hours", False),
        ("7200", "2 hours", False),
        ("3600", "1 hour", True),
        ("1800", "30 minutes", False),
        ("900", "15 minutes", False),
    ]


def test_reports_are_normalized_filtered_and_cached() -> None:
    parsed = parse_reception_reports((FIXTURES / "reports.xml").read_bytes())
    client, fake = build_client(parsed)

    with client:
        first = client.get("/api/reports?callsign=kf6ufo&lookback_seconds=3600")
        second = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=3600&band=20m&mode=ft8"
        )

    assert first.status_code == 200
    assert first.json()["status"] == "ok"
    assert first.json()["report_count"] == 2
    assert first.json()["cache_hit"] is False
    assert first.json()["query"]["callsign"] == "KF6UFO"
    assert first.json()["query"]["directions"] == ["sent_by"]
    assert first.json()["reports"][0]["directions"] == ["sent_by"]
    assert first.json()["xml_trace"][0]["direction"] == "sent_by"
    assert first.json()["xml_trace"][0]["cache_hit"] is False

    assert second.status_code == 200
    assert second.json()["report_count"] == 1
    assert second.json()["cache_hit"] is True
    assert second.json()["reports"][0]["band"] == "20m"
    assert fake.calls == 1


def test_both_directions_make_separate_cached_queries_and_merge_reports() -> None:
    parsed = parse_reception_reports((FIXTURES / "reports.xml").read_bytes())
    client, fake = build_client(parsed)

    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=900"
            "&sent_by=true&recv_by=true"
        )
        cached = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=900"
            "&sent_by=true&recv_by=true"
        )

    assert response.status_code == 200
    assert response.json()["report_count"] == 2
    assert response.json()["cache_status"] == "live"
    assert response.json()["query"]["directions"] == [
        "sent_by",
        "recv_by",
    ]
    assert response.json()["reports"][0]["directions"] == [
        "sent_by",
        "recv_by",
    ]
    assert [entry["direction"] for entry in response.json()["xml_trace"]] == [
        "sent_by",
        "recv_by",
    ]
    assert cached.json()["cache_status"] == "cached"
    assert fake.calls == 2
    assert {query.direction for query in fake.queries} == {
        QueryDirection.SENT_BY,
        QueryDirection.RECV_BY,
    }


def test_valid_empty_results_are_distinct() -> None:
    client, _ = build_client(parse_reception_reports((FIXTURES / "empty.xml").read_bytes()))
    with client:
        response = client.get("/api/reports?callsign=KF6UFO")

    assert response.status_code == 200
    assert response.json()["status"] == "empty"
    assert response.json()["reports"] == []


def test_invalid_callsign_has_stable_error_shape() -> None:
    client, fake = build_client(ParsedReports(()))
    with client:
        response = client.get("/api/reports?callsign=NOT-A-CALL")

    assert response.status_code == 422
    assert response.json()["status"] == "invalid_query"
    assert fake.calls == 0


def test_at_least_one_direction_is_required() -> None:
    client, fake = build_client(ParsedReports(()))
    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO"
            "&sent_by=false&recv_by=false"
        )

    assert response.status_code == 422
    assert response.json()["message"] == "Select Sent by, Recv by, or both."
    assert fake.calls == 0
