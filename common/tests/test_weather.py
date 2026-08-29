from unittest.mock import Mock, patch

from common.weather import fetch_recent_rainfall_mm


@patch("common.weather.requests.get")
def test_sums_precipitation_over_window(mock_get):
    mock_get.return_value = Mock(
        raise_for_status=lambda: None,
        json=lambda: {"daily": {"precipitation_sum": [0.0, 5.2, None, 3.1]}},
    )

    result = fetch_recent_rainfall_mm(37.26, 127.20, as_of_date="2026-08-25")

    assert result == 8.3
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["start_date"] == "2026-08-11"  # as_of - 14일(기본 window)
    assert kwargs["params"]["end_date"] == "2026-08-25"


@patch("common.weather.requests.get")
def test_all_null_precipitation_returns_none(mock_get):
    mock_get.return_value = Mock(raise_for_status=lambda: None, json=lambda: {"daily": {"precipitation_sum": [None, None]}})

    assert fetch_recent_rainfall_mm(37.26, 127.20, as_of_date="2026-08-25") is None


@patch("common.weather.requests.get")
def test_network_failure_returns_none_not_exception(mock_get):
    mock_get.side_effect = ConnectionError("boom")

    assert fetch_recent_rainfall_mm(37.26, 127.20, as_of_date="2026-08-25") is None
