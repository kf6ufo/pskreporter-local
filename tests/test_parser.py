from pathlib import Path

import pytest

from pskreporter_local.parser import InvalidPskXml, parse_reception_reports

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_parses_reports_and_preserves_map_fields() -> None:
    parsed = parse_reception_reports(fixture("reports.xml"))

    assert len(parsed.reports) == 2
    assert len(parsed.warnings) == 1

    newest, oldest = parsed.reports
    assert newest.receiver_call == "N0RX"
    assert newest.receiver_locator is None
    assert newest.mode is None
    assert newest.band == "40m"

    assert oldest.spot_time_utc == "2023-11-14T22:13:20Z"
    assert oldest.sender_call == "KF6UFO"
    assert oldest.sender_locator == "DM79lt"
    assert oldest.receiver_locator == "FN42hn"
    assert oldest.receiver_latitude is None
    assert oldest.receiver_longitude is None
    assert oldest.frequency_hz == 14_074_000
    assert oldest.band == "20m"
    assert oldest.mode == "FT8"


def test_empty_response_is_valid() -> None:
    parsed = parse_reception_reports(fixture("empty.xml"))
    assert parsed.reports == ()
    assert parsed.warnings == ()


@pytest.mark.parametrize("name", ["malformed.xml", "unexpected.xml"])
def test_rejects_invalid_or_unexpected_xml(name: str) -> None:
    with pytest.raises(InvalidPskXml):
        parse_reception_reports(fixture(name))


def test_rejects_entity_expansion() -> None:
    unsafe = b"""<?xml version='1.0'?>
    <!DOCTYPE root [<!ENTITY example 'unsafe'>]>
    <receptionReports>&example;</receptionReports>"""
    with pytest.raises(InvalidPskXml):
        parse_reception_reports(unsafe)
