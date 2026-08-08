from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaidenheadCenter:
    latitude: float
    longitude: float


def maidenhead_center(locator: str | None) -> MaidenheadCenter | None:
    """Return the geographic center of a 2, 4, 6, or 8 character locator."""
    if locator is None:
        return None

    normalized = locator.strip().upper()
    if len(normalized) not in {2, 4, 6, 8}:
        return None
    if not (
        "A" <= normalized[0] <= "R"
        and "A" <= normalized[1] <= "R"
    ):
        return None

    longitude = -180.0 + (ord(normalized[0]) - ord("A")) * 20.0
    latitude = -90.0 + (ord(normalized[1]) - ord("A")) * 10.0
    longitude_width = 20.0
    latitude_height = 10.0

    if len(normalized) >= 4:
        if not (normalized[2].isdigit() and normalized[3].isdigit()):
            return None
        longitude += int(normalized[2]) * 2.0
        latitude += int(normalized[3])
        longitude_width = 2.0
        latitude_height = 1.0

    if len(normalized) >= 6:
        if not (
            "A" <= normalized[4] <= "X"
            and "A" <= normalized[5] <= "X"
        ):
            return None
        longitude += (ord(normalized[4]) - ord("A")) / 12.0
        latitude += (ord(normalized[5]) - ord("A")) / 24.0
        longitude_width = 1.0 / 12.0
        latitude_height = 1.0 / 24.0

    if len(normalized) >= 8:
        if not (normalized[6].isdigit() and normalized[7].isdigit()):
            return None
        longitude += int(normalized[6]) / 120.0
        latitude += int(normalized[7]) / 240.0
        longitude_width = 1.0 / 120.0
        latitude_height = 1.0 / 240.0

    return MaidenheadCenter(
        latitude=latitude + latitude_height / 2.0,
        longitude=longitude + longitude_width / 2.0,
    )
