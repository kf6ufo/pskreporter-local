import pytest

from pskreporter_local.maidenhead import maidenhead_center


@pytest.mark.parametrize(
    ("locator", "expected_latitude", "expected_longitude"),
    [
        ("FN", 45.0, -70.0),
        ("FN31", 41.5, -73.0),
        ("FN31pr", 41.7291666667, -72.7083333333),
        ("DM79lt", 39.8125, -105.0416666667),
        ("AA00AA00", -89.9979166667, -179.9958333333),
        ("RR99XX99", 89.9979166667, 179.9958333333),
    ],
)
def test_returns_center_for_supported_maidenhead_precision(
    locator: str,
    expected_latitude: float,
    expected_longitude: float,
) -> None:
    center = maidenhead_center(locator)

    assert center is not None
    assert center.latitude == pytest.approx(expected_latitude)
    assert center.longitude == pytest.approx(expected_longitude)


@pytest.mark.parametrize(
    "locator",
    [None, "", "F", "FN3", "FN31P", "FN31PR0", "SN31", "FN3A", "FN31ZZ"],
)
def test_rejects_missing_or_invalid_maidenhead_locators(locator: str | None) -> None:
    assert maidenhead_center(locator) is None
