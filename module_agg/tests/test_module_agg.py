from module_agg.run import run


def test_missing_chg_results_returns_degraded():
    result = run({"site_id": "A1037", "site_attributes": {}})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_full_input_aggregates_cleanly():
    result = run(
        {
            "site_id": "A1037",
            "pnu": "4146110500100780003",
            "chg_results": [{"anomaly_score": 0.72, "changed_area_ratio": 0.18, "sar_anomaly": 0.4}],
            "site_attributes": {
                "restoration_elapsed_days": 420,
                "last_inspection_days_ago": 63,
                "adjacent_to_water": True,
                "past_anomaly_count": 1,
                "recent_rainfall_mm": 20.0,
            },
        }
    )

    assert result["status"] == "ok"
    assert result["fallback_tier"] == 1
    assert result["data"]["features"] == {
        "anomaly_score_mean": 0.72,
        "changed_area_ratio": 0.18,
        "sar_anomaly_mean": 0.4,
        "adjacent_to_water": True,
        "restoration_elapsed_days": 420,
        "last_inspection_days_ago": 63,
        "past_anomaly_count": 1,
        "recent_rainfall_mm": 20.0,
    }


def test_multiple_chg_results_are_averaged():
    result = run(
        {
            "site_id": "A1037",
            "chg_results": [
                {"anomaly_score": 0.6, "changed_area_ratio": 0.1},
                {"anomaly_score": 0.8, "changed_area_ratio": 0.2},
            ],
            "site_attributes": {
                "adjacent_to_water": False,
                "restoration_elapsed_days": None,
                "last_inspection_days_ago": None,
                "past_anomaly_count": 0,
            },
        }
    )
    assert result["data"]["features"]["anomaly_score_mean"] == 0.7
    assert result["data"]["features"]["changed_area_ratio"] == round(0.15, 4)


def test_missing_site_attributes_flagged_but_not_fatal():
    result = run(
        {
            "site_id": "A1037",
            "chg_results": [{"anomaly_score": 0.5, "changed_area_ratio": 0.1}],
            "site_attributes": {},
        }
    )
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 2
    assert result["data"]["features"]["adjacent_to_water"] is None
    assert any("site_attributes 누락" in w for w in result["warnings"])
