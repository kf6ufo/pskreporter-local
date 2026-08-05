from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

from .models import CALLSIGN_PATTERN

DEFAULT_CONFIG_PATH = Path("config.json")


class ConfigurationError(RuntimeError):
    """The local configuration file is present but cannot be used."""


def _optional_text(data: dict[str, object], name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f'Configuration setting "{name}" must be text or null.')
    return value.strip() or None


def _integer(data: dict[str, object], name: str, default: int) -> int:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f'Configuration setting "{name}" must be an integer.')
    return value


def _number(data: dict[str, object], name: str, default: float) -> float:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f'Configuration setting "{name}" must be a number.')
    return float(value)


@dataclass(frozen=True)
class Settings:
    query_url: str = "https://retrieve.pskreporter.info/query"
    cache_ttl_seconds: int = 300
    report_limit: int = 1000
    http_timeout_seconds: float = 10.0
    max_xml_bytes: int = 5_000_000
    default_callsign: str | None = None
    app_contact: str | None = None

    @classmethod
    def from_file(cls, path: str | Path = DEFAULT_CONFIG_PATH) -> "Settings":
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"Cannot read valid JSON configuration from {config_path}."
            ) from exc

        if not isinstance(data, dict):
            raise ConfigurationError("The configuration file must contain a JSON object.")

        known_settings = {field.name for field in fields(cls)}
        unknown_settings = sorted(set(data) - known_settings)
        if unknown_settings:
            names = ", ".join(unknown_settings)
            raise ConfigurationError(f"Unknown configuration setting(s): {names}.")

        query_url = data.get("query_url", cls.query_url)
        if not isinstance(query_url, str) or not query_url.strip():
            raise ConfigurationError('Configuration setting "query_url" must be text.')

        default_callsign = _optional_text(data, "default_callsign")
        if default_callsign:
            default_callsign = default_callsign.upper()
            if (
                not 3 <= len(default_callsign) <= 20
                or not CALLSIGN_PATTERN.fullmatch(default_callsign)
            ):
                raise ConfigurationError(
                    'Configuration setting "default_callsign" is not a valid callsign.'
                )

        return cls(
            query_url=query_url.strip(),
            cache_ttl_seconds=max(
                300, _integer(data, "cache_ttl_seconds", cls.cache_ttl_seconds)
            ),
            report_limit=max(1, _integer(data, "report_limit", cls.report_limit)),
            http_timeout_seconds=max(
                1.0,
                _number(data, "http_timeout_seconds", cls.http_timeout_seconds),
            ),
            max_xml_bytes=max(
                1024, _integer(data, "max_xml_bytes", cls.max_xml_bytes)
            ),
            default_callsign=default_callsign,
            app_contact=_optional_text(data, "app_contact"),
        )
