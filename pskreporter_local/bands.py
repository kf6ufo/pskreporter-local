from __future__ import annotations

# Inclusive ranges in hertz. These cover the bands most likely to appear in
# reception reports while keeping band derivation in one versioned location.
BAND_RANGES_HZ: tuple[tuple[str, int, int], ...] = (
    ("2190m", 135_700, 137_800),
    ("630m", 472_000, 479_000),
    ("160m", 1_800_000, 2_000_000),
    ("80m", 3_500_000, 4_000_000),
    ("60m", 5_060_000, 5_450_000),
    ("40m", 7_000_000, 7_300_000),
    ("30m", 10_100_000, 10_150_000),
    ("20m", 14_000_000, 14_350_000),
    ("17m", 18_068_000, 18_168_000),
    ("15m", 21_000_000, 21_450_000),
    ("12m", 24_890_000, 24_990_000),
    ("10m", 28_000_000, 29_700_000),
    ("8m", 40_000_000, 45_000_000),
    ("6m", 50_000_000, 54_000_000),
    ("4m", 70_000_000, 71_000_000),
    ("2m", 144_000_000, 148_000_000),
    ("1.25m", 222_000_000, 225_000_000),
    ("70cm", 420_000_000, 450_000_000),
    ("33cm", 902_000_000, 928_000_000),
    ("23cm", 1_240_000_000, 1_300_000_000),
)


def band_from_frequency(frequency_hz: int | None) -> str | None:
    if frequency_hz is None or frequency_hz <= 0:
        return None

    for band, low_hz, high_hz in BAND_RANGES_HZ:
        if low_hz <= frequency_hz <= high_hz:
            return band
    return None
