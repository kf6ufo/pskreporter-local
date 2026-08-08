from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pskreporter_local.app import create_app
from pskreporter_local.config import Settings
from pskreporter_local.models import ParsedReports, QueryDirection, XmlTrace
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


def build_client(
    parsed: ParsedReports,
    settings: Settings | None = None,
) -> tuple[TestClient, FakePskClient]:
    fake = FakePskClient(parsed)
    clock = lambda: datetime(2026, 8, 5, 18, 0, tzinfo=UTC)
    service = ReportsService(fake, cache_ttl_seconds=300, clock=clock)
    return TestClient(
        create_app(reports_service=service, settings=settings or Settings())
    ), fake


def test_health_and_home_page() -> None:
    client, _ = build_client(ParsedReports(()))
    with client:
        health = client.get("/api/health")
        home = client.get("/")
        stylesheet = client.get("/assets/styles.css")
        javascript = client.get("/assets/app.js")
        leaflet_stylesheet = client.get("/assets/vendor/leaflet-1.9.4.css")
        leaflet_javascript = client.get("/assets/vendor/leaflet-1.9.4.js")
        cluster_javascript = client.get(
            "/assets/vendor/leaflet.markercluster-1.4.1.js"
        )

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert home.status_code == 200
    assert stylesheet.status_code == 200
    assert javascript.status_code == 200
    assert leaflet_stylesheet.status_code == 200
    assert leaflet_javascript.status_code == 200
    assert cluster_javascript.status_code == 200
    assert 'const QRZ_CALLSIGN_URL = "https://www.qrz.com/db/";' in javascript.text
    assert 'link.rel = "noopener noreferrer";' in javascript.text
    assert 'appendQrzCallsignCell(row, "Sender", report.sender_call, senderIsOtherStation);' in javascript.text
    assert 'appendQrzCallsignCell(row, "Recv", report.receiver_call, receiverIsOtherStation);' in javascript.text
    assert "function copyCallsign(callsign, button)" in javascript.text
    assert 'document.execCommand("copy")' in javascript.text
    assert "PSK Reporter + ADIF" in home.text
    assert "SEE WHO’S ON THE AIR · FIND NEW CONTACTS" in home.text
    assert '<details id="station-query-panel" class="station-query-panel" open>' in home.text
    assert "Station &amp; Query" in home.text
    assert 'id="station-query-summary-context"' in home.text
    assert "LIVE ACTIVITY · LOG HISTORY" not in home.text
    assert "Report interval" in home.text
    assert "Refresh interval" in home.text
    assert '<input id="sent-by" name="sent_by" type="checkbox" checked>' in home.text
    assert '<input id="recv-by" name="recv_by" type="checkbox" checked>' in home.text
    assert '<select id="refresh-interval" name="refresh_interval_seconds">' in home.text
    assert '<option value="300">5 minutes</option>' in home.text
    assert '<option value="600" selected>10 minutes</option>' in home.text
    assert '<option value="900">15 minutes</option>' in home.text
    assert "<span>Lookback</span>" not in home.text
    assert "Requests are cached for at least five minutes." in home.text
    assert 'id="last-display-refresh-time">Not yet</time>' in home.text
    assert 'class="visually-hidden">Reception report query</h2>' in home.text
    assert '<p class="section-kicker">QUERY</p>' not in home.text
    assert '<h2 id="results-heading" class="results-title">Results</h2>' in home.text
    assert 'id="table-view-button"' in home.text
    assert 'id="map-view-button"' in home.text
    assert 'id="report-map"' in home.text
    assert 'id="map-summary"' in home.text
    assert 'id="clustered-map-button"' in home.text
    assert 'id="individual-map-button"' in home.text
    assert 'aria-label="Map marker display"' in home.text
    assert 'aria-label="Map marker legend"' in home.text
    assert '/assets/vendor/leaflet-1.9.4.js' in home.text
    assert '/assets/vendor/leaflet.markercluster-1.4.1.js' in home.text
    assert "Recent reception" not in home.text
    assert "Report time (UTC)" in home.text
    assert 'data-sort-key="spot_time_utc" aria-sort="descending"' in home.text
    assert 'data-sort-key="sender_call"' in home.text
    assert home.text.count('class="sort-button"') == 13
    assert 'id="sort-field"' in home.text
    assert 'id="sort-direction"' in home.text
    assert "Activate a column heading to change the sort order." in home.text
    assert "function sortedFilteredReports()" in javascript.text
    assert "function toggleReportSort(key)" in javascript.text
    assert "function groupedMapStations(visibleReports)" in javascript.text
    assert "function renderReportMap(visibleReports)" in javascript.text
    assert "function individualStationPositions(stations)" in javascript.text
    assert "function setMapMarkerMode(mode" in javascript.text
    assert 'const MAP_MARKER_MODE_STORAGE_KEY = "pskreporter-local.map-marker-mode";' in javascript.text
    assert 'MAP_OPPORTUNITY_RANK[station.state] * 10_000' in javascript.text
    assert "let mapNeedsInitialFit = true;" in javascript.text
    assert javascript.text.count("mapNeedsInitialFit = true") == 1
    assert "if (!mapNeedsInitialFit) return;" in javascript.text
    assert "mapShouldFit" not in javascript.text
    assert "const hasCurrentResults = reports.length > 0;" in javascript.text
    assert 'resultsPanel.setAttribute("aria-busy", "true");' in javascript.text
    assert 'resultsPanel.removeAttribute("aria-busy");' in javascript.text
    assert "Refresh failed; continuing to show the previous results." in javascript.text
    assert "\n    reports = [];" not in javascript.text
    assert 'marker.on("click", () => void openStationInspector(report));' in javascript.text
    assert 'th[aria-sort="descending"] .sort-button::after' in stylesheet.text
    assert "Sender grid" in home.text
    assert 'data-sort-key="receiver_call"' in home.text
    assert "Recv grid" in home.text
    assert "<th scope=\"col\">Transmitter</th>" not in home.text
    assert "Receiver grid" not in home.text
    assert "Sender region" in home.text
    assert "Sender DXCC" in home.text
    assert "sNR (dB)" in home.text
    assert "F (MHz)" in home.text
    assert "QSOs B/T" in home.text
    assert 'id="station-inspector"' in home.text
    assert 'id="copy-inspector-callsign"' in home.text
    assert "Your QSO history" in home.text
    assert "Equipment &amp; antenna" not in home.text
    assert "LoTW activity" not in home.text
    assert "function openStationInspector(report)" in javascript.text
    assert 'className = "qso-inspector-button"' in javascript.text
    assert 'row.classList.add("unworked-station-row")' in javascript.text
    assert ".unworked-station .qso-inspector-button" in stylesheet.text
    assert ".station-inspector::backdrop" in stylesheet.text
    assert ".copy-callsign-button" in stylesheet.text
    assert home.text.index('data-sort-key="band"') < home.text.index('data-sort-key="snr_db"')
    assert home.text.rindex('data-sort-key="frequency_hz"') > home.text.rindex('data-sort-key="mode"')
    assert "Frequency (Hz)" not in home.text
    assert 'list="callsign-history"' in home.text
    assert '<datalist id="callsign-history">' in home.text
    assert 'autocomplete="on"' in home.text
    assert '<details class="operator-options">' in home.text
    assert "<summary>Options</summary>" in home.text
    assert "Advanced query options" not in home.text
    assert "PSK Reporter XML parameters" not in home.text
    assert '<details id="xml-trace" class="trace-panel">' in home.text
    assert '<details id="xml-trace" class="trace-panel" open>' not in home.text
    assert '<details id="results-options-panel" class="results-options-panel">' in home.text
    assert "Filters &amp; Request Details" in home.text
    assert 'id="results-options-summary-context"' in home.text
    assert "function updateStationQuerySummary()" in javascript.text
    assert "function updateResultsOptionsSummary()" in javascript.text
    assert "stationQueryPanel.open = false;" in javascript.text
    assert "queryPanelHasAutoCollapsed = true;" in javascript.text
    assert "focusWasInsideQueryPanel" in javascript.text
    assert "ADIF log" in home.text
    assert 'id="reload-adif"' in home.text
    for control_id in (
        "upstream-mode",
        "frequency-range",
        "report-limit",
        "last-sequence-number",
        "modify",
        "rronly",
        "noactive",
        "nolocator",
        "statistics",
    ):
        assert f'id="{control_id}"' in home.text
    assert '<th scope="col">Age</th>' not in home.text
    assert stylesheet.status_code == 200


def test_browser_config_supplies_operator_default_callsign() -> None:
    client = TestClient(
        create_app(
            reports_service=object(),
            settings=Settings(default_callsign="N0CALL"),
        )
    )
    with client:
        response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json() == {
        "default_callsign": "N0CALL",
        "report_limit": 1000,
    }


def test_adif_status_loads_and_manually_reloads_configured_file(tmp_path) -> None:
    log_path = tmp_path / "operator.adi"
    log_path.write_text("<CALL:5>K1ABC<EOR>", encoding="utf-8")
    client = TestClient(
        create_app(
            reports_service=object(),
            settings=Settings(adif_file_path=str(log_path)),
        )
    )

    with client:
        initial = client.get("/api/adif")
        log_path.write_text(
            "<CALL:5>K1ABC<EOR>\n<CALL:5>W1XYZ<EOR>", encoding="utf-8"
        )
        reloaded = client.post("/api/adif/reload")

    assert initial.status_code == 200
    assert initial.json()["status"] == "loaded"
    assert initial.json()["qso_count"] == 1
    assert initial.json()["path"] == str(log_path)
    assert reloaded.status_code == 200
    assert reloaded.json()["status"] == "loaded"
    assert reloaded.json()["qso_count"] == 2


def test_adif_status_is_nonfatal_when_no_file_is_configured() -> None:
    client, _ = build_client(ParsedReports(()))
    with client:
        response = client.get("/api/adif")

    assert response.status_code == 200
    assert response.json()["status"] == "not_configured"
    assert response.json()["configured"] is False


def test_station_qso_history_returns_normalized_local_log_details(tmp_path) -> None:
    log_path = tmp_path / "operator.adi"
    log_path.write_text(
        "<CALL:5>K1ABC<QSO_DATE:8>20260804<TIME_ON:6>235959"
        "<BAND:3>10M<MODE:3>FT8<FREQ:6>28.074<EOR>"
        "<CALL:5>K1ABC<QSO_DATE:8>20260805<TIME_ON:4>1423"
        "<BAND:3>20M<MODE:3>FT8<FREQ:6>14.074<SNR:2>-8<EOR>",
        encoding="utf-8",
    )
    client, _ = build_client(
        ParsedReports(()), Settings(adif_file_path=str(log_path))
    )

    with client:
        response = client.get("/api/stations/k1abc/qsos?band=10M")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "loaded"
    assert payload["callsign"] == "K1ABC"
    assert payload["band"] == "10m"
    assert payload["qso_count_band"] == 1
    assert payload["qso_count_total"] == 2
    assert [qso["qso_date"] for qso in payload["qsos"]] == [
        "2026-08-05",
        "2026-08-04",
    ]
    assert payload["qsos"][0]["time_on_utc"] == "14:23:00Z"
    assert payload["qsos"][0]["snr_db"] == "-8"


def test_station_qso_history_validates_callsign() -> None:
    client, _ = build_client(ParsedReports(()))

    with client:
        response = client.get("/api/stations/NOT-A-CALL/qsos")

    assert response.status_code == 422
    assert response.json()["status"] == "invalid_query"


def test_station_qso_history_accepts_portable_callsigns(tmp_path) -> None:
    log_path = tmp_path / "operator.adi"
    log_path.write_text("<CALL:9>EA8/K1ABC<BAND:3>10M<EOR>", encoding="utf-8")
    client, _ = build_client(
        ParsedReports(()), Settings(adif_file_path=str(log_path))
    )

    with client:
        response = client.get("/api/stations/EA8%2FK1ABC/qsos?band=10m")

    assert response.status_code == 200
    assert response.json()["callsign"] == "EA8/K1ABC"
    assert response.json()["qso_count_total"] == 1


def test_lookback_options_match_supported_live_intervals() -> None:
    client, _ = build_client(ParsedReports(()))
    with client:
        home = client.get("/")

    parser = LookbackOptionParser()
    parser.feed(home.text)
    assert parser.options == [
        ("3600", "1 hour", False),
        ("1800", "30 minutes", False),
        ("900", "15 minutes", True),
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
    assert first.json()["reports"][0]["qso_call"] == "N0RX"
    assert first.json()["reports"][0]["qso_locator"] is None
    assert first.json()["reports"][0]["qso_latitude"] is None
    assert first.json()["reports"][0]["qso_longitude"] is None
    assert first.json()["reports"][0]["qso_count"] is None
    assert first.json()["reports"][0]["qso_count_band"] is None
    assert first.json()["reports"][0]["qso_count_total"] is None
    assert first.json()["reports"][1]["sender_region"] == "Colorado"
    assert first.json()["reports"][1]["sender_dxcc"] == "United States"
    assert first.json()["reports"][1]["snr_db"] == -12
    assert first.json()["reports"][1]["qso_locator"] == "FN42hn"
    assert first.json()["reports"][1]["qso_latitude"] == pytest.approx(42.5625)
    assert first.json()["reports"][1]["qso_longitude"] == pytest.approx(-71.375)
    assert first.json()["xml_trace"][0]["direction"] == "sent_by"
    assert first.json()["xml_trace"][0]["cache_hit"] is False
    assert first.json()["xml_trace"][0]["lookback_seconds"] == 3600

    assert second.status_code == 200
    assert second.json()["report_count"] == 1
    assert second.json()["cache_hit"] is True
    assert second.json()["reports"][0]["band"] == "20m"
    assert fake.calls == 1


def test_qso_count_follows_the_other_station_in_both_directions(tmp_path) -> None:
    parsed = parse_reception_reports(
        b"""<?xml version="1.0"?>
        <receptionReports>
          <receptionReport receiverCallsign="W1RX" senderCallsign="KF6UFO"
            receiverLocator="FN42hn" frequency="28074000"
            flowStartSeconds="1700000000" mode="FT8" />
          <receptionReport receiverCallsign="KF6UFO" senderCallsign="K1ABC"
            senderLocator="DM79lt" frequency="28074000"
            flowStartSeconds="1700000060" mode="FT8" />
        </receptionReports>"""
    )
    log_path = tmp_path / "operator.adi"
    log_path.write_text(
        "<CALL:4>W1RX<BAND:3>10M<EOR>"
        "<CALL:4>W1RX<BAND:3>20M<EOR>"
        "<CALL:5>K1ABC<BAND:3>10M<EOR>"
        "<CALL:5>K1ABC<BAND:3>10M<EOR>"
        "<CALL:5>K1ABC<BAND:2>6M<EOR>",
        encoding="utf-8",
    )
    client, _ = build_client(parsed, Settings(adif_file_path=str(log_path)))

    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=900"
            "&sent_by=true&recv_by=true"
        )

    assert response.status_code == 200
    reports = {
        (report["sender_call"], report["receiver_call"]): report
        for report in response.json()["reports"]
    }
    sent_report = reports[("KF6UFO", "W1RX")]
    received_report = reports[("K1ABC", "KF6UFO")]
    assert sent_report["qso_call"] == "W1RX"
    assert sent_report["qso_locator"] == "FN42hn"
    assert sent_report["qso_latitude"] == pytest.approx(42.5625)
    assert sent_report["qso_count_band"] == 1
    assert sent_report["qso_count_total"] == 2
    assert sent_report["qso_count"] == 2
    assert received_report["qso_call"] == "K1ABC"
    assert received_report["qso_locator"] == "DM79lt"
    assert received_report["qso_longitude"] == pytest.approx(-105.0416666667)
    assert received_report["qso_count_band"] == 2
    assert received_report["qso_count_total"] == 3
    assert received_report["qso_count"] == 3


def test_advanced_query_options_are_normalized_and_returned() -> None:
    client, fake = build_client(ParsedReports(()))
    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=900"
            "&upstream_mode=ft8&rptlimit=75&rronly=false&noactive=false"
            "&nolocator=false&frange=28000000-29700000&statistics=true"
            "&modify=grid&lastseqno=12345"
        )

    assert response.status_code == 200
    query = fake.queries[0]
    assert query.upstream_mode == "FT8"
    assert query.report_limit == 75
    assert query.reception_reports_only is False
    assert query.exclude_active_monitors is False
    assert query.include_reports_without_locator is False
    assert query.frequency_range == "28000000-29700000"
    assert query.include_statistics is True
    assert query.modify_grid is True
    assert query.last_sequence_number == 12345
    assert response.json()["query"] == {
        "callsign": "KF6UFO",
        "lookback_seconds": 900,
        "directions": ["sent_by"],
        "band": None,
        "mode": None,
        "upstream_mode": "FT8",
        "rptlimit": 75,
        "rronly": False,
        "noactive": False,
        "nolocator": False,
        "frange": "28000000-29700000",
        "statistics": True,
        "modify": "grid",
        "lastseqno": 12345,
    }


def test_invalid_advanced_frequency_range_has_stable_error_shape() -> None:
    client, _ = build_client(ParsedReports(()))
    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=900"
            "&frange=29700000-28000000"
        )

    assert response.status_code == 422
    assert response.json()["status"] == "invalid_query"
    assert "lowerHz-upperHz" in response.json()["message"]


def test_filled_upstream_limit_is_reported_as_truncated() -> None:
    parsed_fixture = parse_reception_reports((FIXTURES / "reports.xml").read_bytes())
    parsed = ParsedReports(
        reports=parsed_fixture.reports,
        warnings=parsed_fixture.warnings,
        xml_trace=XmlTrace(
            direction="sent_by",
            request_url="https://retrieve.pskreporter.info/query",
            http_status=200,
            elapsed_ms=25,
            response_bytes=500,
            raw_xml="<receptionReports />",
            requested_report_limit=2,
            report_limit_reached=True,
        ),
    )
    client, _ = build_client(parsed)

    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=3600"
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["truncated"] is True
    assert payload["oldest_report_utc"] == "2023-11-14T22:13:20Z"
    assert "2-report limit" in payload["warnings"][-1]
    assert payload["xml_trace"][0]["report_limit_reached"] is True


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


def test_unsupported_multi_hour_lookback_is_rejected() -> None:
    client, fake = build_client(ParsedReports(()))
    with client:
        response = client.get(
            "/api/reports?callsign=KF6UFO&lookback_seconds=7200"
        )

    assert response.status_code == 422
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
