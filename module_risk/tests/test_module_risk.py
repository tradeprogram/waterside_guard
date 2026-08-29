from module_risk.run import run


def test_missing_features_returns_degraded():
    result = run({"site_id": "A1037"})
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 3


def test_architecture_example_reproduces_score_51():
    # ARCHITECTURE.md §5 Module RISK 예시값 재현(2026-08-30, SAR·최근강우 요인 추가 후
    # 실제 코드 실행 결과로 문서를 맞춤 — 요인 추가 전에는 54점이었다)
    result = run(
        {
            "site_id": "A1037",
            "features": {
                "anomaly_score_mean": 0.72,
                "changed_area_ratio": 0.18,
                "sar_anomaly_mean": 0.4,
                "recent_rainfall_mm": 20.0,
                "adjacent_to_water": True,
                "restoration_elapsed_days": 420,
                "last_inspection_days_ago": 63,
                "past_anomaly_count": 1,
            },
        }
    )
    assert result["status"] == "ok"
    assert result["data"]["risk_score"] == 51
    assert result["data"]["risk_tier"] == "2순위"
    assert result["data"]["source"] == "rule_based"
    factors = {f["factor"] for f in result["data"]["contributing_factors"]}
    assert factors == {
        "anomaly_score_mean",
        "changed_area_ratio",
        "sar_anomaly_mean",
        "recent_rainfall_mm",
        "last_inspection_days_ago",
        "adjacent_to_water",
        "past_anomaly_count",
    }


def test_all_zero_features_yields_normal_tier():
    result = run(
        {
            "site_id": "A2000",
            "features": {
                "anomaly_score_mean": 0.0,
                "changed_area_ratio": 0.0,
                "adjacent_to_water": False,
                "restoration_elapsed_days": 100,
                "last_inspection_days_ago": 0,
                "past_anomaly_count": 0,
            },
        }
    )
    assert result["data"]["risk_score"] == 0
    assert result["data"]["risk_tier"] == "정상"


def test_missing_site_attribute_factors_degrade_but_still_score():
    result = run(
        {
            "site_id": "A3000",
            "features": {
                "anomaly_score_mean": 0.9,
                "changed_area_ratio": 0.5,
                "adjacent_to_water": None,
                "restoration_elapsed_days": None,
                "last_inspection_days_ago": None,
                "past_anomaly_count": None,
            },
        }
    )
    assert result["status"] == "degraded"
    assert result["fallback_tier"] == 2
    assert result["data"]["risk_score"] > 0  # anomaly/changed_area만으로도 부분 점수는 나온다
    factors = {f["factor"] for f in result["data"]["contributing_factors"]}
    assert factors == {"anomaly_score_mean", "changed_area_ratio"}
    assert any("0으로 처리됨" in w for w in result["warnings"])


def test_tier_boundaries():
    def score_for(anomaly):
        return run(
            {
                "site_id": "X",
                "features": {
                    "anomaly_score_mean": anomaly,
                    "changed_area_ratio": 0.0,
                    "adjacent_to_water": False,
                    "restoration_elapsed_days": 0,
                    "last_inspection_days_ago": 0,
                    "past_anomaly_count": 0,
                },
            }
        )["data"]

    assert score_for(1.0)["risk_tier"] == "3순위"  # 0.35*100 = 35
    assert score_for(0.0)["risk_tier"] == "정상"
