import json

import pytest

from pskreporter_local.config import ConfigurationError, Settings


def test_missing_config_file_uses_safe_defaults(tmp_path) -> None:
    settings = Settings.from_file(tmp_path / "missing.json")

    assert settings == Settings()


def test_config_file_is_loaded_normalized_and_bounded(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "default_callsign": " kf6ufo ",
                "app_contact": " operator@example.test ",
                "cache_ttl_seconds": 60,
                "report_limit": 250,
                "http_timeout_seconds": 8.5,
                "max_xml_bytes": 200000,
            }
        ),
        encoding="utf-8",
    )

    settings = Settings.from_file(config_path)

    assert settings.default_callsign == "KF6UFO"
    assert settings.app_contact == "operator@example.test"
    assert settings.cache_ttl_seconds == 300
    assert settings.report_limit == 250
    assert settings.http_timeout_seconds == 8.5
    assert settings.max_xml_bytes == 200000


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("not JSON", "Cannot read valid JSON"),
        ('{"default_call": "N0CALL"}', "Unknown configuration setting"),
        ('{"default_callsign": "NOT-A-CALL"}', "not a valid callsign"),
        ('{"report_limit": "many"}', '"report_limit" must be an integer'),
    ],
)
def test_invalid_config_file_is_rejected(tmp_path, contents, message) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ConfigurationError, match=message):
        Settings.from_file(config_path)
