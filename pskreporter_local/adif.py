from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

MAX_ADIF_BYTES = 50_000_000
FIELD_PATTERN = re.compile(
    r"<\s*([A-Za-z][A-Za-z0-9_]*)(?::(\d+)(?::[^>]*?)?)?\s*>",
    re.IGNORECASE,
)


class InvalidAdif(ValueError):
    """An ADI file cannot be parsed safely enough for local indexing."""


def parse_adi_records(contents: str) -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    position = 0

    while match := FIELD_PATTERN.search(contents, position):
        field_name = match.group(1).upper()
        length_text = match.group(2)
        position = match.end()

        if field_name == "EOH":
            current.clear()
            continue
        if field_name == "EOR":
            if current:
                records.append(current)
                current = {}
            continue
        if length_text is None:
            continue

        field_length = int(length_text)
        value_end = position + field_length
        if value_end > len(contents):
            raise InvalidAdif(
                f"Field {field_name} declares {field_length} characters beyond the file."
            )
        current[field_name] = contents[position:value_end].strip()
        position = value_end

    if current:
        raise InvalidAdif("The final ADIF record does not end with <EOR>.")
    return tuple(records)


def _utc_text(timestamp: float) -> str:
    return (
        datetime.fromtimestamp(timestamp, UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class AdifStatus:
    status: str
    path: str | None
    qso_count: int
    loaded_at_utc: str | None = None
    file_modified_at_utc: str | None = None
    file_size_bytes: int | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "configured": self.path is not None,
            "path": self.path,
            "qso_count": self.qso_count,
            "loaded_at_utc": self.loaded_at_utc,
            "file_modified_at_utc": self.file_modified_at_utc,
            "file_size_bytes": self.file_size_bytes,
            "message": self.message,
        }


class AdifLogService:
    def __init__(self, path: str | None) -> None:
        self.path = Path(path) if path else None
        self.records: tuple[dict[str, str], ...] = ()
        self._call_counts: dict[str, int] = {}
        self._call_band_counts: dict[tuple[str, str], int] = {}
        self._has_loaded = False
        self.status = AdifStatus(
            status="not_configured",
            path=str(self.path) if self.path else None,
            qso_count=0,
            message="Set adif_file_path in config.json to load an ADI log.",
        )
        self._lock = Lock()

    def qso_count_for(self, callsign: str) -> int | None:
        if not self._has_loaded:
            return None
        return self._call_counts.get(callsign.strip().upper(), 0)

    def qso_counts_for(
        self, callsign: str, band: str | None
    ) -> tuple[int | None, int] | None:
        if not self._has_loaded:
            return None
        normalized_call = callsign.strip().upper()
        total_count = self._call_counts.get(normalized_call, 0)
        if band is None:
            return None, total_count
        band_count = self._call_band_counts.get(
            (normalized_call, band.strip().lower()), 0
        )
        return band_count, total_count

    def reload(self) -> AdifStatus:
        with self._lock:
            if self.path is None:
                return self.status

            try:
                file_stat = self.path.stat()
                if not self.path.is_file():
                    raise OSError("The configured path is not a regular file.")
                if file_stat.st_size > MAX_ADIF_BYTES:
                    raise InvalidAdif(
                        f"The ADI file exceeds the {MAX_ADIF_BYTES:,}-byte safety limit."
                    )
                raw_contents = self.path.read_bytes()
                try:
                    contents = raw_contents.decode("utf-8-sig")
                except UnicodeDecodeError:
                    contents = raw_contents.decode("latin-1")
                records = parse_adi_records(contents)
            except (InvalidAdif, OSError) as exc:
                self.status = AdifStatus(
                    status="error",
                    path=str(self.path),
                    qso_count=len(self.records),
                    message=(
                        "Reload failed; the last successfully loaded records remain "
                        f"in memory. {exc}"
                    ),
                )
                return self.status

            call_counts = Counter(
                call.strip().upper()
                for record in records
                if (call := record.get("CALL")) and call.strip()
            )
            call_band_counts = Counter(
                (call.strip().upper(), band.strip().lower())
                for record in records
                if (call := record.get("CALL"))
                and call.strip()
                and (band := record.get("BAND"))
                and band.strip()
            )
            self.records = records
            self._call_counts = dict(call_counts)
            self._call_band_counts = dict(call_band_counts)
            self._has_loaded = True
            self.status = AdifStatus(
                status="loaded",
                path=str(self.path),
                qso_count=len(records),
                loaded_at_utc=_utc_text(datetime.now(UTC).timestamp()),
                file_modified_at_utc=_utc_text(file_stat.st_mtime),
                file_size_bytes=file_stat.st_size,
                message="ADI log loaded into memory.",
            )
            return self.status
