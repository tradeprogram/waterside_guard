import datetime as dt

from module_obs.seasonal import _season_window, summarize_seasonal_baseline


def test_season_window_maps_same_month_day_to_past_year():
    start, end = _season_window("2026-08-15", 2024)
    assert start == "2024-07-26"  # 8/15 - 20일
    assert end == "2024-09-04"  # 8/15 + 20일


def test_season_window_handles_leap_day_without_crashing():
    start, end = _season_window("2024-02-29", 2023)  # 2023엔 2/29가 없다
    assert dt.date.fromisoformat(start) < dt.date.fromisoformat(end)


def test_summarize_uses_median_and_mad_not_mean():
    """한 해가 이상치여도 기준선이 통째로 흔들리지 않아야 한다."""
    yearly = [
        {"year": 2023, "ndvi_median": 0.70, "scene_count": 4},
        {"year": 2024, "ndvi_median": 0.72, "scene_count": 3},
        {"year": 2025, "ndvi_median": 0.10, "scene_count": 2},  # 구름 등으로 튄 값
    ]
    result = summarize_seasonal_baseline(yearly)
    assert result["historical_median"] == 0.70  # 평균(0.51)이 아니라 중앙값
    assert result["years_used"] == 3


def test_summarize_skips_years_without_observation():
    yearly = [
        {"year": 2023, "ndvi_median": None, "scene_count": 0},
        {"year": 2024, "ndvi_median": 0.60, "scene_count": 3},
    ]
    result = summarize_seasonal_baseline(yearly)
    assert result["years_used"] == 1
    assert result["historical_median"] == 0.60


def test_summarize_empty_returns_none_baseline():
    result = summarize_seasonal_baseline([])
    assert result["historical_median"] is None
    assert result["years_used"] == 0
