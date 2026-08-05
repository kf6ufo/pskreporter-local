from pathlib import Path

import pytest

from pskreporter_local.adif import AdifLogService, InvalidAdif, parse_adi_records

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_adi_header_and_case_insensitive_qso_records() -> None:
    contents = (FIXTURES / "log.adi").read_text(encoding="utf-8")

    records = parse_adi_records(contents)

    assert len(records) == 2
    assert records[0]["CALL"] == "K1ABC"
    assert records[0]["BAND"] == "10M"
    assert records[1]["CALL"] == "W1XYZ"
    assert records[1]["BAND"] == "6M"


def test_rejects_unterminated_adi_record() -> None:
    with pytest.raises(InvalidAdif, match="does not end with <EOR>"):
        parse_adi_records("<CALL:5>K1ABC")


def test_adif_service_reports_loaded_missing_and_unconfigured_files(tmp_path) -> None:
    log_path = tmp_path / "operator.adi"
    log_path.write_text(
        "<CALL:5>K1ABC<BAND:3>10M<EOR>"
        "<CALL:5>k1abc<BAND:2>6M<EOR>",
        encoding="utf-8",
    )

    loaded = AdifLogService(str(log_path))
    loaded_status = loaded.reload()
    missing_status = AdifLogService(str(tmp_path / "missing.adi")).reload()
    unconfigured_status = AdifLogService(None).reload()

    assert loaded_status.status == "loaded"
    assert loaded_status.qso_count == 2
    assert loaded.records[0]["CALL"] == "K1ABC"
    assert loaded.qso_count_for("K1ABC") == 2
    assert loaded.qso_count_for("k1abc") == 2
    assert loaded.qso_count_for("W1XYZ") == 0
    assert loaded.qso_counts_for("K1ABC", "10m") == (1, 2)
    assert loaded.qso_counts_for("k1abc", "6M") == (1, 2)
    assert loaded.qso_counts_for("K1ABC", "20m") == (0, 2)
    assert loaded.qso_counts_for("K1ABC", None) == (None, 2)
    assert unconfigured_status.qso_count == 0
    assert AdifLogService(None).qso_count_for("K1ABC") is None
    assert AdifLogService(None).qso_counts_for("K1ABC", "10m") is None
    assert loaded_status.file_size_bytes == log_path.stat().st_size
    assert missing_status.status == "error"
    assert "No such file" in (missing_status.message or "")
    assert unconfigured_status.status == "not_configured"


def test_failed_reload_retains_the_last_good_records(tmp_path) -> None:
    log_path = tmp_path / "operator.adi"
    log_path.write_text("<CALL:5>K1ABC<EOR>", encoding="utf-8")
    service = AdifLogService(str(log_path))
    service.reload()
    log_path.write_text("<CALL:5>K1ABC", encoding="utf-8")

    failed_status = service.reload()

    assert failed_status.status == "error"
    assert failed_status.qso_count == 1
    assert service.records[0]["CALL"] == "K1ABC"
    assert "last successfully loaded records remain" in (failed_status.message or "")
