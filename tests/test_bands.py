from pskreporter_local.bands import band_from_frequency


def test_derives_common_bands_at_boundaries() -> None:
    assert band_from_frequency(14_000_000) == "20m"
    assert band_from_frequency(14_074_000) == "20m"
    assert band_from_frequency(14_350_000) == "20m"
    assert band_from_frequency(144_174_000) == "2m"


def test_unknown_and_invalid_frequencies_are_not_parser_failures() -> None:
    assert band_from_frequency(13_000_000) is None
    assert band_from_frequency(0) is None
    assert band_from_frequency(None) is None
